"""
schemas.py — Pydantic request/response şemaları.
"""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


# ─── Sınıf ───────────────────────────────────────────────────────────────────

class ClassOut(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


# ─── Öğrenci ─────────────────────────────────────────────────────────────────

class StudentOut(BaseModel):
    id: int
    school_no: str
    name: str
    class_id: int

    model_config = {"from_attributes": True}


# ─── Koordinat / BBox ─────────────────────────────────────────────────────────

class BBox(BaseModel):
    """Hücre koordinatları (piksel, sol-üst köşe referanslı)."""
    x: int
    y: int
    w: int
    h: int


# ─── Ayıklanan Öğrenci Satırı ─────────────────────────────────────────────────

class ExtractedStudent(BaseModel):
    row_index: int
    school_no: str
    name: str
    exam1: Optional[float] = None
    exam2: Optional[float] = None
    perf1: Optional[float] = None
    perf2: Optional[float] = None
    calculated_average: Optional[float] = None
    status: str = Field(description="'Geçti' veya 'Kaldı' ya da 'Belirsiz'")
    is_new_student: bool = Field(description="DB'de ilk kez görülen öğrenci mi?")
    
    # Gelişim Değerlendirme Puanları
    growth_attendance: Optional[float] = None
    growth_activities: Optional[float] = None
    growth_product: Optional[float] = None
    growth_social_emotional: Optional[float] = None
    growth_progress: Optional[float] = None
    # Hücre koordinatları (opsiyonel, frontend için)
    bbox_school_no: Optional[BBox] = None
    bbox_name: Optional[BBox] = None
    bbox_exam1: Optional[BBox] = None
    bbox_exam2: Optional[BBox] = None
    bbox_perf1: Optional[BBox] = None
    bbox_perf2: Optional[BBox] = None


# ─── Upload ──────────────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    class_name: str
    class_id: Optional[int] = None
    total_rows: int
    students: list[ExtractedStudent]
    warnings: list[str] = Field(default_factory=list)


# ─── Not Kayıt İsteği ─────────────────────────────────────────────────────────

class GradeItem(BaseModel):
    school_no: str
    name: str
    class_name: str
    exam1: Optional[float] = None
    exam2: Optional[float] = None
    perf1: Optional[float] = None
    perf2: Optional[float] = None
    
    # Gelişim Değerlendirme Puanları
    growth_attendance: Optional[float] = None
    growth_activities: Optional[float] = None
    growth_product: Optional[float] = None
    growth_social_emotional: Optional[float] = None
    growth_progress: Optional[float] = None
    
    term: str = "2024-2025-1"


class SaveGradesRequest(BaseModel):
    grades: list[GradeItem]


class SaveGradesResponse(BaseModel):
    saved: int
    updated: int
    errors: list[str] = []
