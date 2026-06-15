"""
ocr_engine.py — EasyOCR singleton wrapper (Türkçe + İngilizce, CPU).

EasyOCR modeli uygulama ömrü boyunca bir kez yüklenir.
Her istek için Reader yeniden oluşturulmaz → performans korunur.
"""
from __future__ import annotations
import logging
import re
import threading
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ─── OCR Karakter Düzeltme Tabloları ─────────────────────────────────────────

# EasyOCR'ın Türkçe isimler için sık yaptığı harf karışıklıkları
# Büyük/küçük harf duyarsız çalışır; uygulamadan önce metin büyük harfe çevrilir
_NAME_CHAR_FIXES: list[tuple[str, str]] = [
    # Rakam/özel karakter karışıklıkları
    (r"[#\$\*\^\+\|]", ""),                        # anlamsız özel karakterleri sil
    (r"(?<=[A-ZÇĞİÖŞÜ\s])0(?=[A-ZÇĞİÖŞÜ\s])", "O"),  # harf ortasında 0 → O
    (r"(?<=[A-ZÇĞİÖŞÜ\s])1(?=[A-ZÇĞİÖŞÜ\s])", "I"),  # harf ortasında 1 → I
    # Türkçe özgün harf düzeltmeleri
    (r"\bPUSTAFA\b", "MUSTAFA"),
    (r"\bRUSTAFA\b", "MUSTAFA"),
    (r"\bMUSTAPA\b", "MUSTAFA"),
    (r"\bHUSEY\b", "HÜSEY"),
    (r"\bHUSEYIN\b", "HÜSEYİN"),
    (r"\bUMIT\b", "ÜMIT"),
    (r"\bUMLT\b", "ÜMIT"),
    (r"\bUMLT\b", "ÜMIT"),
]

# Türkçe isme uygun izin verilen karakter seti (OCR allowlist)
_NAME_ALLOWLIST = (
    "ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ"
    "abcçdefgğhıijklmnoöprsştuüvyz"
    " '-."
)

_lock = threading.Lock()
_reader = None  # EasyOCR Reader singleton


def _get_reader():
    """Thread-safe singleton EasyOCR Reader."""
    global _reader
    if _reader is None:
        with _lock:
            if _reader is None:
                try:
                    import easyocr  # noqa: PLC0415
                    logger.info("EasyOCR Reader yükleniyor (tr + en, GPU=False)…")
                    _reader = easyocr.Reader(
                        ["tr", "en"],
                        gpu=False,
                        verbose=False,
                        download_enabled=True,
                    )
                    logger.info("EasyOCR Reader hazır.")
                except Exception as exc:
                    logger.error("EasyOCR yüklenemedi: %s", exc)
                    raise
    return _reader


def _preprocess_cell(
    cell_img: np.ndarray,
    is_name: bool = False,
    scale: int = 3,
) -> np.ndarray:
    """
    Hücre görüntüsünü OCR için ön işle.

    Parameters
    ----------
    cell_img : np.ndarray
        BGR veya gri ton hücre görüntüsü.
    is_name : bool
        True ise isim hücresi için daha agresif kontrastlama uygula.
    scale : int
        Büyütme katsayısı (varsayılan 3).
    """
    if cell_img is None or cell_img.size == 0:
        return cell_img

    try:
        # Gri tonlamaya çevir
        if len(cell_img.shape) == 3:
            gray = cv2.cvtColor(cell_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = cell_img.copy()

        # Gürültü giderme
        gray = cv2.medianBlur(gray, 3)

        pmin, pmax = int(gray.min()), int(gray.max())
        contrast = pmax - pmin

        if is_name:
            # İsim hücreleri için CLAHE kontrast artırma
            clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(4, 4))
            gray = clahe.apply(gray)
            # Adaptif threshold — değişken aydınlatmada daha iyi
            binarized = cv2.adaptiveThreshold(
                gray, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                blockSize=15,
                C=8,
            )
        elif contrast > 15:
            thresh_val = pmin + contrast * 0.35
            _, binarized = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY)
        else:
            # Düşük kontrast → Otsu
            _, binarized = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Küçük gürültü noktalarını temizle (morfolojik açma)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        binarized = cv2.morphologyEx(binarized, cv2.MORPH_OPEN, kernel)

        # Ölçeklendir
        h, w = binarized.shape
        # Çok küçük hücrelerde ölçeği artır
        if h < 20 or w < 20:
            scale = max(scale, int(max(20 / max(h, 1), 20 / max(w, 1))) + 1)
        resized = cv2.resize(
            binarized, (w * scale, h * scale),
            interpolation=cv2.INTER_CUBIC
        )
        return cv2.cvtColor(resized, cv2.COLOR_GRAY2BGR)

    except Exception as exc:
        logger.warning("OCR ön işleme hatası: %s", exc)
        return cell_img


def _post_process_name(text: str) -> str:
    """
    OCR sonrası isim metnini temizle ve hataları düzelt.

    - Anlamsız özel karakterleri sil
    - Bilinen karakter karışıklıklarını düzelt (V↔Y vb.)
    - Fazla boşlukları normalize et
    - Tamamı büyük harfe çevir (Türk okul formatı)
    """
    if not text:
        return text

    # Büyük harfe çevir
    text = text.upper()

    # Bilinen regex düzeltmelerini uygula
    for pattern, replacement in _NAME_CHAR_FIXES:
        text = re.sub(pattern, replacement, text)

    # Sadece harf, boşluk ve tire bırak
    text = re.sub(r"[^A-ZÇĞİIÖŞÜ\s\-\']", "", text)

    # Birden fazla boşluğu tek boşluğa indir
    text = re.sub(r"\s+", " ", text).strip()

    return text


def read_text(
    cell_img: np.ndarray,
    is_numeric: bool = False,
    allowlist: Optional[str] = None,
) -> tuple[str, float]:
    """
    Tek hücre görüntüsünden metin oku.

    Parameters
    ----------
    cell_img : np.ndarray
        BGR veya gri ton hücre görüntüsü (OpenCV formatı).
    is_numeric : bool
        True ise yalnızca rakam/virgül/nokta/G/g/harf tanıma modunda çalış.
    allowlist : Optional[str]
        OCR okuması için izin verilen karakter listesi.

    Returns
    -------
    (metin, güven_skoru)
    """
    if cell_img is None or cell_img.size == 0:
        return "", 0.0

    original_img = cell_img

    # Orijinal ön işleme: basit threshold + 3x ölçek (küçük hücrelerde güvenilir)
    try:
        gray = cv2.cvtColor(cell_img, cv2.COLOR_BGR2GRAY)
        pmin, pmax = int(gray.min()), int(gray.max())

        if pmax - pmin > 15:
            thresh_val = pmin + (pmax - pmin) * 0.35
            _, binarized = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY)
            h, w = binarized.shape
            resized = cv2.resize(binarized, (w * 3, h * 3), interpolation=cv2.INTER_CUBIC)
            cell_img = cv2.cvtColor(resized, cv2.COLOR_GRAY2BGR)
        else:
            h, w = cell_img.shape[:2]
            if h < 20 or w < 20:
                scale = max(20 / max(h, 1), 20 / max(w, 1), 1.0)
                cell_img = _resize(cell_img, scale)
    except Exception as exc:
        logger.warning("OCR ön işleme hatası: %s", exc)

    reader = _get_reader()
    try:
        kwargs: dict = dict(detail=1, paragraph=False)
        if allowlist is not None:
            kwargs["allowlist"] = allowlist
        elif is_numeric:
            kwargs["allowlist"] = "0123456789,.-Gg "

        candidates = [_read_ocr_candidate(reader, original_img, kwargs)]
        if cell_img is not original_img:
            candidates.append(_read_ocr_candidate(reader, cell_img, kwargs))

        return max(candidates, key=lambda item: item[1])

    except Exception as exc:
        logger.warning("OCR hatası: %s", exc)
        return "", 0.0


def read_name(
    cell_img: np.ndarray,
) -> tuple[str, float]:
    """
    İsim hücresi için özel OCR okuyucu.

    Standart ``read_text``'e göre farklar:
    - Ham hücre ile 2x büyütülmüş hücreyi ayrı ayrı okur
    - Güven skoru daha yüksek olan sonucu kullanır
    - Post-processing: karakter karışıklıklarını düzelt, normalize et

    Returns
    -------
    (temizlenmiş_isim, güven_skoru)
    """
    if cell_img is None or cell_img.size == 0:
        return "", 0.0

    reader = _get_reader()
    try:
        h, w = cell_img.shape[:2]
        enlarged_img = cv2.resize(
            cell_img,
            (w * 2, h * 2),
            interpolation=cv2.INTER_CUBIC,
        )

        kwargs = dict(detail=1, paragraph=False)
        candidates = [
            _read_ocr_candidate(reader, cell_img, kwargs),
            _read_ocr_candidate(reader, enlarged_img, kwargs),
        ]
        raw_text, avg_confidence = max(candidates, key=lambda item: item[1])

        cleaned = _post_process_name(raw_text)
        if cleaned != raw_text.upper():
            logger.debug("İsim düzeltildi OCR sonrası: '%s' → '%s'", raw_text, cleaned)

        return cleaned, avg_confidence

    except Exception as exc:
        logger.warning("OCR isim okuma hatası: %s", exc)
        return "", 0.0


def _read_ocr_candidate(
    reader,
    image: np.ndarray,
    kwargs: dict,
) -> tuple[str, float]:
    """Tek görüntü varyantından birleşik metin ve ortalama güven skoru üret."""
    results = reader.readtext(image, **kwargs)
    if not results:
        return "", 0.0

    texts = [r[1] for r in results]
    confidences = [r[2] for r in results]
    return " ".join(texts).strip(), float(np.mean(confidences))


def _resize(img: np.ndarray, scale: float) -> np.ndarray:
    """Görüntüyü belirtilen ölçeğe göre büyüt."""
    import cv2  # noqa: PLC0415
    new_w = max(1, int(img.shape[1] * scale))
    new_h = max(1, int(img.shape[0] * scale))
    return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
