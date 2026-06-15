"""
grade_parser.py — OCR metninden not değerlerine dönüşüm.

Kurallar
--------
- Boş metin, "G", "g", "-" → None (gelmedi/girilmedi)
- Türkçe ondalık ayraç virgül (,) → noktaya (.) çevir
- Geçerli float → float
- Ortalama formülü: (toplam) / (null_olmayan_not_sayısı)
- Geçti barajı: ortalama ≥ 50
"""
from __future__ import annotations
import re
from typing import Optional


# "Gelmedi" / "boş" kabul edilen değerler
_ABSENT_PATTERNS = re.compile(r"^\s*[Gg]\s*$|^\s*-\s*$|^\s*$")


def parse_grade(raw: str) -> Optional[float]:
    """
    OCR ham metnini float nota dönüştür.
    Dönüştürülemez veya "G" ise None döner.
    """
    if not raw or _ABSENT_PATTERNS.match(raw):
        return None

    # Türkçe virgülü noktaya çevir, boşlukları temizle
    cleaned = raw.strip().replace(",", ".").replace(" ", "")

    # Yalnızca sayı ve nokta kalsın
    numeric_only = re.sub(r"[^\d.]", "", cleaned)
    if not numeric_only:
        return None

    try:
        value = float(numeric_only)
        # Makul not aralığı: 0 – 100
        if 0.0 <= value <= 100.0:
            return round(value, 2)
        return None
    except ValueError:
        return None


def calculate_average(
    exam1: Optional[float],
    exam2: Optional[float],
    perf1: Optional[float],
    perf2: Optional[float],
) -> Optional[float]:
    """
    Mevcut notlardan ortalama hesapla.
    Tüm notlar girilmiş olmalıdır (None veya eksik olmamalıdır).
    Eğer herhangi biri eksik (None) ise None döner.
    """
    grades = (exam1, exam2, perf1, perf2)
    if any(grade is None for grade in grades):
        return None
    return round(sum(grade for grade in grades if grade is not None) / 4, 2)


def determine_status(average: Optional[float]) -> str:
    """
    50 barajına göre geçme/kalma durumu.
    Ortalama yoksa 'Belirsiz'.
    """
    if average is None:
        return "Belirsiz"
    return "Geçti" if average >= 50.0 else "Kaldı"
