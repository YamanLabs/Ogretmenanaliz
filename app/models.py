"""
models.py — SQLAlchemy ORM modelleri.
Tablolar: classes, students, grades
"""
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.database import Base


class Class(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)  # Örn: "10-A"

    students = relationship("Student", back_populates="class_", cascade="all, delete-orphan")


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    school_no = Column(String(20), nullable=False)
    name = Column(String(150), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)

    class_ = relationship("Class", back_populates="students")
    grades = relationship("Grade", back_populates="student", cascade="all, delete-orphan")


class Grade(Base):
    __tablename__ = "grades"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    exam1 = Column(Float, nullable=True)
    exam2 = Column(Float, nullable=True)
    perf1 = Column(Float, nullable=True)
    perf2 = Column(Float, nullable=True)
    calculated_average = Column(Float, nullable=True)
    
    # Gelişim Değerlendirme Alanları
    growth_attendance = Column(Float, nullable=True)       # Sınıf İçi Ders Katılım
    growth_activities = Column(Float, nullable=True)       # Sınıf Dışı Faaliyetler
    growth_product = Column(Float, nullable=True)          # Ürün Değerlendirme
    growth_social_emotional = Column(Float, nullable=True) # Sosyal Duygusal Akademik Gelişim
    growth_progress = Column(Float, nullable=True)         # Öğrenci Gelişimi
    
    term = Column(String(20), nullable=False, default="2024-2025-1")
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    student = relationship("Student", back_populates="grades")
