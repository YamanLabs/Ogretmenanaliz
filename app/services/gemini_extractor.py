"""Gemini ile e-Okul ekran goruntusunden ogrenci notlarini ayiklama."""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, ValidationError

logger = logging.getLogger(__name__)

DEFAULT_GEMINI_MODEL = "gemini-3.1-flash-lite"

EXTRACTION_PROMPT = """
Bu e-Okul not tablosu goruntusundeki ogrenci satirlarini ayikla.

Kurallar:
- Sutun basliklarini esas al. Yalnizca Okul No, Adi Soyadi, 1. Sinav,
  2. Sinav, 1. Performans ve 2. Performans alanlarini oku.
- "Puani", "Puanı", "Ortalama", "Basari", "Durum" gibi hesaplanmis
  sutunlari tamamen yok say. Bu sutunlari performans notu olarak kullanma.
- Her ogrenci icin yalnizca su alanlari dondur:
  school_no, name, exam1, exam2, perf1, perf2.
- Notlari goruntude yazdigi haliyle metin olarak dondur.
- Bos, girilmemis veya G olan notlari null dondur.
- Ortalama ya da gecme durumu hesaplama.
- Goruntude olmayan bir degeri tahmin etme.
""".strip()


class GeminiStudentRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    school_no: str
    name: str
    exam1: Optional[str] = None
    exam2: Optional[str] = None
    perf1: Optional[str] = None
    perf2: Optional[str] = None


class GeminiExtractionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    students: list[GeminiStudentRow]


@dataclass(frozen=True)
class GeminiStudent:
    school_no: str
    name: str
    exam1: Optional[float]
    exam2: Optional[float]
    perf1: Optional[float]
    perf2: Optional[float]


class GeminiExtractionError(Exception):
    """Kullaniciya guvenle gosterilebilen Gemini servis hatasi."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def _response_schema() -> dict[str, Any]:
    grade_schema = {"anyOf": [{"type": "string"}, {"type": "null"}]}
    return {
        "type": "object",
        "properties": {
            "students": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "school_no": {"type": "string"},
                        "name": {"type": "string"},
                        "exam1": grade_schema,
                        "exam2": grade_schema,
                        "perf1": grade_schema,
                        "perf2": grade_schema,
                    },
                    "required": [
                        "school_no",
                        "name",
                        "exam1",
                        "exam2",
                        "perf1",
                        "perf2",
                    ],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["students"],
        "additionalProperties": False,
    }


def _friendly_api_error(exc: Exception) -> GeminiExtractionError:
    status_code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    text = str(exc).lower()

    if status_code == 429 or "quota" in text or "resource_exhausted" in text:
        return GeminiExtractionError(
            "Gemini API kotasi asildi. Kota durumunu kontrol edip daha sonra tekrar deneyin.",
            status_code=429,
        )
    if status_code in (401, 403) or "api key" in text or "permission_denied" in text:
        return GeminiExtractionError(
            "Gemini API anahtari gecersiz veya bu model icin yetkili degil.",
            status_code=502,
        )
    if (
        isinstance(exc, (ConnectionError, TimeoutError))
        or "timeout" in text
        or "connection" in text
        or "network" in text
    ):
        return GeminiExtractionError(
            "Gemini API'ye baglanilamadi. Ag baglantisini kontrol edip tekrar deneyin.",
            status_code=503,
        )
    return GeminiExtractionError(
        "Gemini goruntuyu analiz ederken bir hata olustu. Lutfen tekrar deneyin.",
        status_code=502,
    )


def _parse_gemini_grade(raw: Optional[str]) -> Optional[float]:
    """Gemini notunu yalnızca açıkça 0-100 aralığındaysa kabul et."""
    if raw is None:
        return None
    cleaned = raw.strip().replace(",", ".")
    if not cleaned or cleaned.upper() == "G" or cleaned == "-":
        return None
    if not re.fullmatch(r"\d+(?:\.\d+)?", cleaned):
        return None
    value = float(cleaned)
    if not 0.0 <= value <= 100.0:
        return None
    return round(value, 2)


def _parse_response_text(response_text: str) -> list[GeminiStudent]:
    try:
        raw_payload = json.loads(response_text)
        payload = GeminiExtractionPayload.model_validate(raw_payload)
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        raise GeminiExtractionError(
            "Gemini gecersiz bir yanit dondurdu. Goruntuyu kontrol edip tekrar deneyin."
        ) from exc

    students: list[GeminiStudent] = []
    for row in payload.students:
        school_no = row.school_no.strip()
        name = row.name.strip()
        if not school_no or not name:
            raise GeminiExtractionError(
                "Gemini yanitinda okul numarasi veya ogrenci adi eksik."
            )

        students.append(
            GeminiStudent(
                school_no=school_no,
                name=name,
                exam1=_parse_gemini_grade(row.exam1),
                exam2=_parse_gemini_grade(row.exam2),
                perf1=_parse_gemini_grade(row.perf1),
                perf2=_parse_gemini_grade(row.perf2),
            )
        )

    if not students:
        raise GeminiExtractionError(
            "Gemini goruntude ogrenci satiri bulamadi. Tablo goruntusunu kontrol edin.",
            status_code=422,
        )
    return students


def extract_students_with_gemini(
    image_bytes: bytes,
    mime_type: str,
    api_key: Optional[str] = None,
) -> list[GeminiStudent]:
    """Goruntuyu Gemini'ye gonder ve dogrulanmis ogrenci satirlarini dondur."""
    if api_key:
        api_key = api_key.strip()
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY", "").strip()

    if not api_key:
        raise GeminiExtractionError(
            "Gemini kullanmak icin geçerli bir Gemini API anahtari (GEMINI_API_KEY) girilmelidir.",
            status_code=503,
        )

    model = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                EXTRACTION_PROMPT,
            ],
            config={
                "response_mime_type": "application/json",
                "response_json_schema": _response_schema(),
                "thinking_config": {"thinking_level": "minimal"},
            },
        )
    except GeminiExtractionError:
        raise
    except Exception as exc:
        logger.warning(
            "Gemini API istegi basarisiz oldu (model=%s, hata_turu=%s)",
            model,
            type(exc).__name__,
        )
        raise _friendly_api_error(exc) from exc

    response_text = getattr(response, "text", None)
    if not response_text:
        raise GeminiExtractionError(
            "Gemini bos bir yanit dondurdu. Goruntuyu kontrol edip tekrar deneyin."
        )
    return _parse_response_text(response_text)
