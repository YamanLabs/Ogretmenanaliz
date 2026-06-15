"""
grades.py — POST /api/save-grades

Frontend'den gelen manuel düzeltilmiş not listesini SQLite'a kaydeder.
Var olan kayıtları günceller, olmayanları oluşturur (upsert).
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Class, Student, Grade
from app.schemas import SaveGradesRequest, SaveGradesResponse, GradeItem, ExtractedStudent
from app.services.grade_parser import calculate_average

router = APIRouter(prefix="/api", tags=["grades"])
logger = logging.getLogger(__name__)


def _upsert_grade(db: Session, student: Student, item: GradeItem) -> tuple[bool, bool]:
    """
    Öğrencinin not kaydını upsert et.
    Döner: (is_new, is_updated)
    """
    avg = calculate_average(item.exam1, item.exam2, item.perf1, item.perf2)

    existing = (
        db.query(Grade)
        .filter(Grade.student_id == student.id, Grade.term == item.term)
        .first()
    )

    if existing is None:
        grade = Grade(
            student_id=student.id,
            exam1=item.exam1,
            exam2=item.exam2,
            perf1=item.perf1,
            perf2=item.perf2,
            calculated_average=avg,
            growth_attendance=item.growth_attendance,
            growth_activities=item.growth_activities,
            growth_product=item.growth_product,
            growth_social_emotional=item.growth_social_emotional,
            growth_progress=item.growth_progress,
            term=item.term,
            updated_at=datetime.now(timezone.utc),
        )
        db.add(grade)
        return True, False
    else:
        existing.exam1 = item.exam1
        existing.exam2 = item.exam2
        existing.perf1 = item.perf1
        existing.perf2 = item.perf2
        existing.calculated_average = avg
        existing.growth_attendance = item.growth_attendance
        existing.growth_activities = item.growth_activities
        existing.growth_product = item.growth_product
        existing.growth_social_emotional = item.growth_social_emotional
        existing.growth_progress = item.growth_progress
        existing.updated_at = datetime.now(timezone.utc)
        return False, True


@router.post("/save-grades", response_model=SaveGradesResponse)
def save_grades(
    payload: SaveGradesRequest,
    db: Session = Depends(get_db),
):
    """
    Manuel düzeltilmiş notları veritabanına kaydet / güncelle.

    Her item için:
    - Sınıfı bul / oluştur
    - Öğrenciyi bul (school_no + class) / oluştur
    - Not kaydını upsert et
    """
    saved = 0
    updated = 0
    errors: list[str] = []

    for item in payload.grades:
        try:
            # Sınıf
            cls = db.query(Class).filter(Class.name == item.class_name).first()
            if cls is None:
                cls = Class(name=item.class_name)
                db.add(cls)
                db.flush()

            # Öğrenci
            student = (
                db.query(Student)
                .filter(
                    Student.school_no == item.school_no,
                    Student.class_id == cls.id,
                )
                .first()
            )
            if student is None:
                student = Student(
                    school_no=item.school_no,
                    name=item.name,
                    class_id=cls.id,
                )
                db.add(student)
                db.flush()

            is_new, is_updated = _upsert_grade(db, student, item)
            db.commit()

            if is_new:
                saved += 1
            elif is_updated:
                updated += 1

        except Exception as exc:
            db.rollback()
            msg = f"Hata [{item.school_no} / {item.name}]: {exc}"
            logger.error(msg)
            errors.append(msg)

    return SaveGradesResponse(saved=saved, updated=updated, errors=errors)


@router.get("/grades/{class_id}", response_model=list[ExtractedStudent])
def get_class_grades(class_id: int, term: str = "2024-2025-1", db: Session = Depends(get_db)):
    """Seçilen sınıfın tüm öğrencilerini ve notlarını getir."""
    from app.services.grade_parser import determine_status
    
    cls = db.query(Class).filter(Class.id == class_id).first()
    if cls is None:
        raise HTTPException(status_code=404, detail=f"Sınıf bulunamadı: id={class_id}")
        
    students_out = []
    for idx, student in enumerate(cls.students, start=1):
        grade = (
            db.query(Grade)
            .filter(Grade.student_id == student.id, Grade.term == term)
            .first()
        )
        
        exam1 = grade.exam1 if grade else None
        exam2 = grade.exam2 if grade else None
        perf1 = grade.perf1 if grade else None
        perf2 = grade.perf2 if grade else None
        avg = grade.calculated_average if grade else None
        
        status = determine_status(avg)
        
        students_out.append(
            ExtractedStudent(
                row_index=idx,
                school_no=student.school_no,
                name=student.name,
                exam1=exam1,
                exam2=exam2,
                perf1=perf1,
                perf2=perf2,
                calculated_average=avg,
                status=status,
                is_new_student=False,
                growth_attendance=grade.growth_attendance if grade else None,
                growth_activities=grade.growth_activities if grade else None,
                growth_product=grade.growth_product if grade else None,
                growth_social_emotional=grade.growth_social_emotional if grade else None,
                growth_progress=grade.growth_progress if grade else None,
            )
        )
    return students_out


@router.delete("/grades/class/{class_name}")
def clear_class_data(class_name: str, db: Session = Depends(get_db)):
    """Sınıf adıyla eşleşen sınıfı ve tüm ilişkili verilerini (öğrenci, notlar) siler."""
    cls = db.query(Class).filter(Class.name == class_name).first()
    if cls is None:
        raise HTTPException(status_code=404, detail=f"Sınıf bulunamadı: '{class_name}'")
    
    db.delete(cls)
    db.commit()
    return {"message": f"'{class_name}' sınıfı ve tüm ilişkili verileri başarıyla silindi."}

