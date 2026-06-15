"""
upload.py — POST /api/upload

İş akışı
--------
1. İsteği al: görsel (multipart/form-data veya base64 JSON) + class_name
2. OpenCV ile hücreleri çıkar
3. Sütun eşleştirme: header satırında "Okul No", "Adı Soyadı", "1.Sınav" vb. ara
4. Her veri satırı için OCR çalıştır
5. student_matcher ile DB'ye kaydet / eşleştir
6. ExtractedStudent listesi + hücre koordinatları döndür
"""
from __future__ import annotations
import base64
import io
import logging
from typing import Annotated, Optional

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import BBox, ExtractedStudent, UploadResponse
from app.services.image_processor import Cell, extract_cells
from app.services.ocr_engine import read_text, read_name
from app.services.grade_parser import parse_grade, calculate_average, determine_status
from app.services.student_matcher import match_or_create_student
from app.services import gemini_extractor

router = APIRouter(prefix="/api", tags=["upload"])
logger = logging.getLogger(__name__)

# E-okul sütun sırası (0-indexed): varsayılan düzen
# Öğretmene göre değişebilir; header satırı okunarak dinamik hale getirilir
DEFAULT_COL_MAP = {
    "sira":       0,  # Sıra No
    "school_no":  1,  # Okul No
    "name":       2,  # Adı Soyadı
    "exam1":      3,  # 1. Sınav
    "exam2":      4,  # 2. Sınav
    "perf1":      5,  # 1. Performans
    "perf2":      6,  # 2. Performans
}

# Başlık eşleştirme anahtar kelimeleri (küçük harf)
# Gerçek e-okul sütun başlıkları dahil edilmiştir:
# Örn. "Okul No", "Adı Soyadı", "1.Sınav", "1.Perf.", "1.Uyg."
HEADER_KEYWORDS = {
    "school_no": [
        "okul no", "okulno", "no", "numara", "okul",
    ],
    "name": [
        "adı soyadı", "adi soyadi", "ad soyad", "öğrenci adı",
        "isim", "adi", "soyadi", "soyad", "soyodi", "soy",
    ],
    "exam1": [
        "1.sınav", "1. sınav", "1.sinav", "1. sinav", "sinav1", "sınav1",
        "1-sinov", "sinov1", "sin 1", "sın 1", "1.sın", "1.sin",
    ],
    "exam2": [
        "2.sınav", "2. sınav", "2.sinav", "2. sinav", "sinav2", "sınav2",
        "2-sinov", "sinov2", "sin 2", "sın 2", "2.sın", "2.sin",
    ],
    "exam3": [
        "3.sınav", "3. sınav", "3.sinav", "3. sinav", "sinav3", "sınav3",
        "3-sinov", "sinov3", "sin 3", "sın 3", "3.sın",
    ],
    "exam4": [
        "4.sınav", "4. sınav", "4.sinav", "sinav4", "sınav4",
    ],
    "exam5": [
        "5.sınav", "5. sınav", "5.sinav", "sinav5", "sınav5",
    ],
    "exam6": [
        "6.sınav", "6. sınav", "6.sinav", "sinav6", "sınav6",
    ],
    "perf1": [
        "1.perf", "1. perf", "perf1", "1.perf.", "performans1",
        "1.parf", "parf1", "1.per",
    ],
    "perf2": [
        "2.perf", "2. perf", "perf2", "2.perf.", "performans2",
        "2.parf", "parf2", "2.per",
    ],
    "perf3": [
        "3.perf", "3. perf", "perf3", "3.perf.", "performans3",
        "3.parf", "parf3", "3.per",
    ],
    "uyg1": [
        "1.uyg", "1. uyg", "uyg1", "1.uyg.", "uygulama1",
        "1.uyg", "uyg 1",
    ],
    "uyg2": [
        "2.uyg", "2. uyg", "uyg2", "2.uyg.", "uygulama2",
        "uyg 2",
    ],
    "uyg3": [
        "3.uyg", "3. uyg", "uyg3", "3.uyg.", "uygulama3",
        "uyg 3",
    ],
}


def _complete_core_grade_columns(col_map: dict[str, int]) -> dict[str, int]:
    """Kısmi başlık OCR sonucunda bitişik temel not sütunlarını tamamla."""
    name_col = col_map.get("name")
    if name_col is None:
        return col_map

    expected = {
        "exam1": name_col + 1,
        "exam2": name_col + 2,
        "perf1": name_col + 3,
        "perf2": name_col + 4,
    }
    known_core = {key: col_map[key] for key in expected if key in col_map}
    if known_core and any(value != expected[key] for key, value in known_core.items()):
        return col_map

    completed = dict(col_map)
    for key, col in expected.items():
        completed.setdefault(key, col)
    return completed


def _detect_header_row(cells: list[Cell]) -> tuple[int, dict[str, int]]:
    """
    Hücreler arasında başlık satırını tespit et.
    
    Yöntem:
    1. İlk 5 satırda OCR ile başlık anahtar kelimeleri ara
    2. Bulunamazsa: okul no ve ad soyad hazır sütun konumlarından tahmin et
    3. En son çare: DEFAULT_COL_MAP kullan
    """
    max_row = max(c.row for c in cells) if cells else 0
    cells_by_pos: dict[tuple[int, int], Cell] = {(c.row, c.col): c for c in cells}

    for row_idx in range(min(5, max_row + 1)):
        row_cells = sorted(
            [c for c in cells if c.row == row_idx],
            key=lambda c: c.col,
        )
        if not row_cells:
            continue
        
        texts = []
        for c in row_cells:
            t, _ = read_text(c.image)
            texts.append(t.lower().strip())
        
        col_map: dict[str, int] = {}
        mapped_cols: set[int] = set()

        for field_key, keywords in HEADER_KEYWORDS.items():
            for col_idx, text in enumerate(texts):
                if col_idx in mapped_cols:
                    continue
                if any(kw in text for kw in keywords):
                    col_map[field_key] = col_idx
                    mapped_cols.add(col_idx)
                    break

        # En az "name" ve "school_no" bulunursa bu başlık satırı
        if "name" in col_map and "school_no" in col_map:
            col_map = _complete_core_grade_columns(col_map)
            logger.info("Başlık satırı tespit edildi: row=%d, col_map=%s", row_idx, col_map)
            return row_idx, col_map

    # ── Fallback: Veri satırlarından sütun pozisyonunu çıkar ────────────────────
    # E-okul'da ilk veri satırında okul no genellikle ilk sütunda sayısal değer
    # Ad soyad ikinci sütunda uzun metin
    logger.warning("Başlık satırı bulunamadı — veri satırından sütun tahmini")

    import re as _re  # noqa: PLC0415

    for row_idx in range(min(5, max_row + 1)):
        row_cells = sorted([c for c in cells if c.row == row_idx], key=lambda c: c.col)
        if len(row_cells) < 3:
            continue

        # Satırdaki hücre metinlerini oku (ilk 8 hücre)
        texts_with_col = []
        for c in row_cells[:8]:
            t, conf = read_text(c.image)
            texts_with_col.append((c.col, t.strip(), conf))

        # Okul No: rakam içeren kısa metin (1-5 hane)
        # text.isdigit() yerine: sadece rakamlar çıkarılınca 1-5 haneli olmalı
        school_no_col = None
        for col_idx, text, conf in texts_with_col:
            digits_only = _re.sub(r"\D", "", text)
            if 1 <= len(digits_only) <= 5 and len(digits_only) >= len(text) * 0.6:
                school_no_col = col_idx
                break

        # Ad Soyad: en uzun alfasayısal metin okul no'dan sonra
        name_col = None
        if school_no_col is not None:
            # Önce uzun (>=4 karakter) bir metin bul
            best_len = 0
            for col_idx, text, conf in texts_with_col:
                if col_idx > school_no_col and len(text) >= 3:
                    if len(text) > best_len:
                        best_len = len(text)
                        name_col = col_idx
                    break  # ilk uzun metin = isim sütunu

        if school_no_col is not None and name_col is not None:
            remaining_cols = [c.col for c in row_cells if c.col > name_col]
            col_map = {
                "school_no": school_no_col,
                "name": name_col,
            }
            grade_fields = [
                "exam1", "exam2", "exam3", "exam4", "exam5", "exam6",
                "perf1", "perf2", "perf3", "uyg1", "uyg2", "uyg3",
            ]
            for i, field in enumerate(grade_fields):
                if i < len(remaining_cols):
                    col_map[field] = remaining_cols[i]

            logger.info("Veri satırı tahmini col_map: row=%d, %s", row_idx, col_map)
            return -1, col_map

    logger.warning("Hiçbir yöntem başarılı olmadı — varsayılan sütun haritası")
    return -1, DEFAULT_COL_MAP


def _cell_at(cells_by_pos: dict[tuple[int, int], Cell],
             row: int, col: int) -> Optional[Cell]:
    return cells_by_pos.get((row, col))


def _cell_to_bbox(cell: Optional[Cell]) -> Optional[BBox]:
    if cell is None:
        return None
    return BBox(x=cell.x, y=cell.y, w=cell.w, h=cell.h)


def _decode_image(image_bytes: bytes) -> np.ndarray:
    """Bayt dizisini OpenCV BGR görüntüsüne dönüştür."""
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Görüntü çözümlenemedi. Geçerli bir PNG/JPG gönderin.")
    return img


def _detect_mime_type(raw_bytes: bytes, declared_type: Optional[str]) -> str:
    """OpenCV kullanmadan Gemini için güvenli bir görsel MIME türü belirle."""
    if declared_type and declared_type.startswith("image/"):
        return declared_type
    if raw_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if raw_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if raw_bytes.startswith(b"RIFF") and raw_bytes[8:12] == b"WEBP":
        return "image/webp"
    raise HTTPException(
        status_code=422,
        detail="Gemini için geçerli bir PNG, JPG veya WEBP görseli yükleyin.",
    )


def _build_gemini_response(
    rows: list[gemini_extractor.GeminiStudent],
    class_name: str,
    db: Session,
) -> UploadResponse:
    """Gemini satırlarını mevcut eşleştirme ve hesaplama akışına bağla."""
    students: list[ExtractedStudent] = []
    warnings: list[str] = []
    class_id: Optional[int] = None

    for row_index, row in enumerate(rows, start=1):
        avg = calculate_average(row.exam1, row.exam2, row.perf1, row.perf2)
        status = determine_status(avg)

        try:
            student, is_new, corrected_name = match_or_create_student(
                db=db,
                class_name=class_name,
                school_no=row.school_no,
                ocr_name=row.name,
            )
            db.commit()
            class_id = student.class_id
        except Exception as exc:
            db.rollback()
            warn_msg = f"Row {row_index} DB hatası: {exc}"
            logger.error(warn_msg)
            warnings.append(warn_msg)
            corrected_name = row.name
            is_new = False

        students.append(
            ExtractedStudent(
                row_index=row_index,
                school_no=row.school_no,
                name=corrected_name,
                exam1=row.exam1,
                exam2=row.exam2,
                perf1=row.perf1,
                perf2=row.perf2,
                calculated_average=avg,
                status=status,
                is_new_student=is_new,
                bbox_school_no=None,
                bbox_name=None,
                bbox_exam1=None,
                bbox_exam2=None,
                bbox_perf1=None,
                bbox_perf2=None,
            )
        )

    return UploadResponse(
        class_name=class_name,
        class_id=class_id,
        total_rows=len(students),
        students=students,
        warnings=warnings,
    )


@router.post("/upload", response_model=UploadResponse)
async def upload_image(
    class_name: Annotated[str, Form()],
    file: Annotated[Optional[UploadFile], File()] = None,
    image_base64: Annotated[Optional[str], Form()] = None,
    processor: Annotated[str, Form()] = "local",
    gemini_api_key: Annotated[Optional[str], Form()] = None,
    db: Session = Depends(get_db),
):
    """
    Görsel yükle ve e-okul notlarını ayıkla.

    Kabul edilen formatlar:
    - `file`: multipart/form-data dosya yüklemesi
    - `image_base64`: base64 kodlu görsel (data:image/… ön eki ile veya saf base64)
    """
    # ── Görüntü al ──────────────────────────────────────────────────────────
    declared_mime_type: Optional[str] = None
    if file is not None:
        raw_bytes = await file.read()
        declared_mime_type = file.content_type
    elif image_base64:
        # "data:image/png;base64,..." ön ekini temizle
        if "," in image_base64:
            prefix, image_base64 = image_base64.split(",", 1)
            if prefix.startswith("data:"):
                declared_mime_type = prefix[5:].split(";", 1)[0]
        try:
            raw_bytes = base64.b64decode(image_base64, validate=True)
        except (ValueError, base64.binascii.Error) as exc:
            raise HTTPException(status_code=422, detail="Geçersiz base64 görsel verisi.") from exc
    else:
        raise HTTPException(status_code=422, detail="'file' veya 'image_base64' zorunludur.")

    if len(raw_bytes) == 0:
        raise HTTPException(status_code=422, detail="Boş görüntü.")

    if processor not in {"local", "gemini"}:
        raise HTTPException(
            status_code=422,
            detail="'processor' alanı 'local' veya 'gemini' olmalıdır.",
        )

    if processor == "gemini":
        mime_type = _detect_mime_type(raw_bytes, declared_mime_type)
        try:
            rows = gemini_extractor.extract_students_with_gemini(raw_bytes, mime_type, api_key=gemini_api_key)
        except gemini_extractor.GeminiExtractionError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
        return _build_gemini_response(rows, class_name, db)

    try:
        img_bgr = _decode_image(raw_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # ── Hücre tespiti ────────────────────────────────────────────────────────
    logger.info("Görüntü boyutu: %dx%d — hücreler ayıklanıyor…", img_bgr.shape[1], img_bgr.shape[0])
    cells = extract_cells(img_bgr)

    if not cells:
        raise HTTPException(status_code=422,
                            detail="Görüntüde tablo hücresi tespit edilemedi.")

    # (row, col) → Cell hızlı erişim
    cells_by_pos: dict[tuple[int, int], Cell] = {(c.row, c.col): c for c in cells}
    max_row = max(c.row for c in cells)

    # ── Başlık satırı tespiti ────────────────────────────────────────────────
    header_row, col_map = _detect_header_row(cells)
    data_start_row = header_row + 1  # veri satırları bu indexten başlar

    # ── Veri satırlarını işle ────────────────────────────────────────────────
    students: list[ExtractedStudent] = []
    warnings: list[str] = []
    class_id: Optional[int] = None

    for row_idx in range(data_start_row, max_row + 1):
        row_cells_count = sum(1 for c in cells if c.row == row_idx)
        if row_cells_count == 0:
            continue

        # Okul No hücresi
        school_no_cell = _cell_at(cells_by_pos, row_idx, col_map.get("school_no", 1))
        school_no_text, sno_conf = read_text(
            school_no_cell.image if school_no_cell else None,
            allowlist="0123456789",
        )
        school_no_clean = school_no_text.strip()

        # Boş veya çok kısa okul numarası → satırı atla
        if len(school_no_clean) < 3:
            logger.debug("Row %d atlandı — okul no yetersiz: '%s'", row_idx, school_no_clean)
            continue

        # İsim hücresi — özel read_name ile daha iyi OCR
        name_cell = _cell_at(cells_by_pos, row_idx, col_map.get("name", 2))
        name_text, _ = read_name(name_cell.image if name_cell else None)

        # Not hücreleri
        def read_grade_cell(field_key: str, default_col: int) -> tuple[Optional[float], Optional[Cell]]:
            col = col_map.get(field_key, default_col)
            cell = _cell_at(cells_by_pos, row_idx, col)
            raw, _ = read_text(cell.image if cell else None, is_numeric=True)
            return parse_grade(raw), cell

        exam1, exam1_cell = read_grade_cell("exam1", 3)
        exam2, exam2_cell = read_grade_cell("exam2", 4)
        perf1, perf1_cell = read_grade_cell("perf1", 5)
        perf2, perf2_cell = read_grade_cell("perf2", 6)

        avg    = calculate_average(exam1, exam2, perf1, perf2)
        status = determine_status(avg)

        # ── DB eşleştirme ────────────────────────────────────────────────────
        try:
            student, is_new, corrected_name = match_or_create_student(
                db=db,
                class_name=class_name,
                school_no=school_no_clean,
                ocr_name=name_text,
            )
            db.commit()
            class_id = student.class_id
        except Exception as exc:
            db.rollback()
            warn_msg = f"Row {row_idx} DB hatası: {exc}"
            logger.error(warn_msg)
            warnings.append(warn_msg)
            corrected_name = name_text
            is_new = False
            student = None  # type: ignore[assignment]

        students.append(
            ExtractedStudent(
                row_index=row_idx,
                school_no=school_no_clean,
                name=corrected_name,
                exam1=exam1,
                exam2=exam2,
                perf1=perf1,
                perf2=perf2,
                calculated_average=avg,
                status=status,
                is_new_student=is_new,
                bbox_school_no=_cell_to_bbox(school_no_cell),
                bbox_name=_cell_to_bbox(name_cell),
                bbox_exam1=_cell_to_bbox(exam1_cell),
                bbox_exam2=_cell_to_bbox(exam2_cell),
                bbox_perf1=_cell_to_bbox(perf1_cell),
                bbox_perf2=_cell_to_bbox(perf2_cell),
            )
        )

    if not students:
        raise HTTPException(
            status_code=422,
            detail="Görüntüden hiçbir öğrenci satırı ayıklanamadı. "
                   "Tablo yapısını kontrol edin.",
        )

    return UploadResponse(
        class_name=class_name,
        class_id=class_id,
        total_rows=len(students),
        students=students,
        warnings=warnings,
    )
