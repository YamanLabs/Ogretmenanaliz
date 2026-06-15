"""
export.py — GET /api/export-excel/{class_id}

Seçilen sınıfın notlarını renkli Excel olarak indirir.
"""
from __future__ import annotations
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Class
from app.services.excel_exporter import build_excel
from app.services.excel_growth_exporter import build_growth_excel

router = APIRouter(prefix="/api", tags=["export"])
logger = logging.getLogger(__name__)


@router.get("/export-excel/{class_id}")
def export_excel(class_id: int, db: Session = Depends(get_db)):
    """
    Sınıfın not dökümünü renkli Excel dosyası olarak indir.

    - Geçti → yeşil (#C8E6C9)
    - Kaldı → kırmızı (#FFCDD2)
    - Belirsiz → sarı (#FFF9C4)
    """
    cls = db.query(Class).filter(Class.id == class_id).first()
    if cls is None:
        raise HTTPException(status_code=404, detail=f"Sınıf bulunamadı: id={class_id}")

    try:
        excel_bytes = build_excel(db, class_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Excel oluşturma hatası: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Excel oluşturulamadı: {exc}") from exc

    filename = f"{cls.name.replace(' ', '_')}_notlar.xlsx"
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export-growth-excel/{class_id}")
def export_growth_excel(class_id: int, db: Session = Depends(get_db)):
    """
    Sınıfın gelişim değerlendirme raporunu Excel dosyası olarak indir.
    """
    cls = db.query(Class).filter(Class.id == class_id).first()
    if cls is None:
        raise HTTPException(status_code=404, detail=f"Sınıf bulunamadı: id={class_id}")

    try:
        excel_bytes = build_growth_excel(db, class_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Gelişim Excel oluşturma hatası: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Gelişim Excel oluşturulamadı: {exc}") from exc

    filename = f"{cls.name.replace(' ', '_')}_gelisim_raporu.xlsx"
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
