"""
student_matcher.py — OCR ile okunan öğrenci bilgilerini DB ile eşleştir.

Akış
----
1. school_no ile DB'de sorgula.
2. Bulunamazsa → yeni öğrenci kaydı oluştur (is_new=True).
3. Bulunursa → OCR ismini DB ismiyle difflib ile kıyasla;
   benzerlik > 0.7 ise DB ismini kullan (OCR hatasını düzelt).

Not: SQLAlchemy Session thread-safe değil; her istek kendi session'ını kullanır.
"""
from __future__ import annotations
import difflib
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Class, Student

logger = logging.getLogger(__name__)

# İsim düzeltme için minimum benzerlik eşiği
NAME_SIMILARITY_THRESHOLD = 0.75


def _get_or_create_class(db: Session, class_name: str) -> Class:
    """Sınıfı bul ya da oluştur."""
    cls = db.query(Class).filter(Class.name == class_name).first()
    if cls is None:
        cls = Class(name=class_name)
        db.add(cls)
        db.flush()  # ID'yi al
        logger.info("Yeni sınıf oluşturuldu: %s (id=%d)", class_name, cls.id)
    return cls


def match_or_create_student(
    db: Session,
    class_name: str,
    school_no: str,
    ocr_name: str,
) -> tuple[Student, bool, str]:
    """
    Öğrenciyi DB ile eşleştir veya yeni kayıt oluştur.

    Returns
    -------
    (student, is_new, corrected_name)
    - student: ORM nesnesi
    - is_new: True ise yeni kayıt
    - corrected_name: Kullanılacak doğru isim (DB'den veya OCR'dan)
    """
    school_no = school_no.strip()
    ocr_name = ocr_name.strip()

    cls = _get_or_create_class(db, class_name)

    student: Optional[Student] = (
        db.query(Student)
        .filter(Student.class_id == cls.id, Student.school_no == school_no)
        .first()
    )

    if student is None:
        # Yeni öğrenci
        student = Student(school_no=school_no, name=ocr_name, class_id=cls.id)
        db.add(student)
        db.flush()
        logger.info("Yeni öğrenci kaydedildi: %s %s", school_no, ocr_name)
        return student, True, ocr_name

    # Mevcut öğrenci — isim düzeltme
    corrected_name = _correct_name(db_name=student.name, ocr_name=ocr_name)
    if corrected_name != ocr_name:
        logger.debug(
            "İsim düzeltildi [%s]: '%s' → '%s'",
            school_no, ocr_name, corrected_name,
        )

    # Eğer DB ismi çok kısa/boşsa ve OCR ismi daha uzunsa DB'yi güncelle
    if (
        len(corrected_name.strip()) > len(student.name.strip())
        and corrected_name == ocr_name  # DB'den düzeltilmediş, OCR sonucu kullanılıyor
    ):
        logger.info(
            "DB ismi güncellendi [%s]: '%s' → '%s'",
            school_no, student.name, corrected_name,
        )
        student.name = corrected_name
        db.flush()

    return student, False, corrected_name


def _correct_name(db_name: str, ocr_name: str) -> str:
    """
    difflib SequenceMatcher ile OCR isim hatasını düzelt.
    Benzerlik yeterince yüksekse DB ismini döndür; aksi hâlde OCR ismini koru.
    """
    ratio = difflib.SequenceMatcher(None, db_name.upper(), ocr_name.upper()).ratio()
    logger.debug("İsim benzerliği: db='%s' ocr='%s' ratio=%.2f", db_name, ocr_name, ratio)

    if ratio >= NAME_SIMILARITY_THRESHOLD:
        return db_name
    return ocr_name
