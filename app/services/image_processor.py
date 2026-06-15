"""
image_processor.py — OpenCV ile e-okul tablo tespiti ve hücre ayırma.

Desteklenen görüntü türleri:
  A) Masaüstü web ekran görüntüsü (gri oval input kutular, ince tablo çizgileri)
  B) iPad/tablet ekran görüntüsü (sol sidebar, lacivert başlık barı)

Ana Strateji:
  1. Lacivert başlık barı ve sidebar tespiti → tablo bölgesini belirle
  2. Tablonun her satırının piksel parlaklık ortalamasıyla satır sınırlarını bul
  3. Gri/beyaz input kutularının x konturlarından sütun sınırlarını bul
  4. Her hücrenin (row, col) → BBox ve görüntü listesini döndür
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Cell:
    row: int
    col: int
    x: int
    y: int
    w: int
    h: int
    image: Optional[np.ndarray] = field(default=None, repr=False)


# ─── Renk Maskeleri ──────────────────────────────────────────────────────────

def _get_dark_navy_mask(img_bgr: np.ndarray) -> np.ndarray:
    """Lacivert (#2b3e50 benzeri) pikselleri maskele."""
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    return cv2.inRange(hsv, (90, 25, 20), (145, 255, 140))


def _get_input_pixels_mask(img_bgr: np.ndarray) -> np.ndarray:
    """
    E-okul input alanlarını maskele.
    Hem gri (kilitli sınav) hem beyaz (aktif perf) input kutular dahil.
    Lacivert (#2b3e50) ve siyah metin piksellerini hariç tut.
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

    # 1) Gri input kutuları (kilitli sınav notları): açık gri, düşük doygunluk
    gray_input = cv2.inRange(gray, 165, 235)

    # 2) Beyaz/açık input kutuları (aktif perf notları)
    white_input = cv2.inRange(gray, 236, 252)

    # Neredeyse saf beyaz arka planı (>252) çıkar
    pure_white = cv2.inRange(gray, 252, 255)
    # Çok koyu pikselleri çıkar (metin, çizgiler)
    dark = cv2.inRange(gray, 0, 100)
    # Lacivert pikselleri çıkar
    navy = _get_dark_navy_mask(img_bgr)

    combined = cv2.bitwise_or(gray_input, white_input)
    exclude = cv2.bitwise_or(cv2.bitwise_or(pure_white, dark), navy)
    mask = cv2.bitwise_and(combined, cv2.bitwise_not(exclude))

    return mask


# ─── Sidebar Tespiti ─────────────────────────────────────────────────────────

def _detect_sidebar_width(img_bgr: np.ndarray) -> int:
    """
    Sol navigasyon sidebar'ının genişliğini tespit et.
    Sidebar: sol %45'te, yüksekliğin %55'inden fazlasını kaplayan lacivert dikey bant.
    """
    h_img, w_img = img_bgr.shape[:2]
    navy_mask = _get_dark_navy_mask(img_bgr)

    search_width = int(w_img * 0.45)
    left_region = navy_mask[:, :search_width]
    v_proj = np.sum(left_region > 0, axis=0).astype(float)

    sidebar_threshold = h_img * 0.55
    sidebar_cols = np.where(v_proj >= sidebar_threshold)[0]

    if len(sidebar_cols) == 0:
        return 0

    sidebar_right = int(sidebar_cols[-1])

    if sidebar_right < 80 or sidebar_right > search_width - 50:
        return 0

    # Sağda açık alan olmalı
    right_check = img_bgr[:, sidebar_right:sidebar_right + 60]
    right_gray = cv2.cvtColor(right_check, cv2.COLOR_BGR2GRAY)
    if np.mean(right_gray) < 150:
        return 0

    logger.info("Sidebar tespit edildi: genişlik=%d px", sidebar_right + 1)
    return sidebar_right + 5


# ─── Başlık Barı Tespiti ─────────────────────────────────────────────────────

def _detect_table_header_y(img_bgr: np.ndarray, x_start: int = 0) -> int:
    """
    'Sınıf Listesi...' lacivert başlık barının altını bul (tablo y başlangıcı).
    """
    h_img, w_img = img_bgr.shape[:2]
    roi = img_bgr[:, x_start:]
    roi_w = roi.shape[1]

    navy_mask = _get_dark_navy_mask(roi)
    h_proj = np.sum(navy_mask > 0, axis=1).astype(float)

    header_threshold = roi_w * 0.50
    header_rows = np.where(h_proj >= header_threshold)[0]

    if len(header_rows) == 0:
        logger.warning("Lacivert başlık barı bulunamadı")
        return 0

    groups = _group_consecutive(header_rows.tolist(), gap=5)

    for group in reversed(groups):
        if len(group) >= 8:
            table_y = group[-1] + 2
            logger.info("Başlık barı bulundu: y=%d-%d, tablo y=%d",
                        group[0], group[-1], table_y)
            return table_y

    return groups[-1][-1] + 2


# ─── Satır Tespiti ───────────────────────────────────────────────────────────

def _detect_row_boundaries(table_img: np.ndarray) -> list[int]:
    """
    Tablo satır sınırlarını tespit et.
    
    Yöntem 1: Morfik yatay çizgi tespiti (görünür border'lar)
    Yöntem 2: Satır piksel parlaklığı → koyu çizgiler = ayırıcı
    Yöntem 3: İnce border çizgileri için özel filtre
    """
    h, w = table_img.shape[:2]
    gray = cv2.cvtColor(table_img, cv2.COLOR_BGR2GRAY)

    # ── Yöntem 1: Morfik yatay çizgi ──────────────────────────────────────────
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    best_y, best_count = [], 0
    for scale in [8, 10, 12, 15, 20, 25, 30, 40]:
        kl = max(1, w // scale)
        kern = cv2.getStructuringElement(cv2.MORPH_RECT, (kl, 1))
        lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kern, iterations=2)
        proj = np.sum(lines, axis=1)
        thresh = proj.max() * 0.10 if proj.max() > 0 else 1
        pos = _get_line_positions_from_proj(proj, thresh)
        if len(pos) > best_count:
            best_count = len(pos)
            best_y = pos

    if best_count >= 5:
        logger.debug("Morfik yatay çizgi: %d satır", best_count)
        positions = sorted(set([0] + best_y + [h]))
        # Çok yakın pozisyonları birleştir (min 10px)
        return _merge_close_positions(positions, min_gap=10)

    # ── Yöntem 2: İnce border çizgileri (RGB değişimi) ────────────────────────
    logger.info("Morfik çizgi yetersiz (%d), border piksel yöntemi", best_count)
    
    # Tablo border çizgileri genellikle açık gri (#dddddd benzeri)
    # veya beyaz arka plandan biraz daha koyu
    # Her satırın ortalama parlaklığını hesapla
    row_means = np.mean(gray, axis=1)
    
    # Eşik: açık arka plan satırları yüksek (>210), border çizgileri düşük (<210)
    # Ama aynı zamanda koyu header da düşük
    threshold_brightness = 210
    
    # Border satırları: düşük parlaklık ama çok koyu değil (50-210 arası)
    border_mask = (row_means < threshold_brightness) & (row_means > 50)
    
    # Border maskesi projeksiyon ile gruplama
    border_idx = np.where(border_mask)[0].tolist()
    groups = _group_consecutive(border_idx, gap=3)
    
    if len(groups) >= 5:
        positions = [0] + [int(np.mean(g)) for g in groups] + [h]
        positions = sorted(set(positions))
        merged = _merge_close_positions(positions, min_gap=15)
        if len(merged) >= 5:
            logger.debug("Border piksel yöntemi: %d satır", len(merged) - 1)
            return merged

    # ── Yöntem 3: Input kutusu y-koordinatları ────────────────────────────────
    logger.info("Border piksel yöntemi yetersiz, input kutusu y-tespiti")
    return _detect_rows_from_inputs(table_img, h, w)


def _detect_rows_from_inputs(table_img: np.ndarray, h: int, w: int) -> list[int]:
    """Input kutularının y koordinatlarından satır sınırlarını tespit et."""
    input_mask = _get_input_pixels_mask(table_img)

    # Morfolojik birleştirme
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (10, 3))
    cleaned = cv2.morphologyEx(input_mask, cv2.MORPH_CLOSE, k)

    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        logger.warning("Input kontur bulunamadı — eşit bölümleme (12 satır)")
        return [int(i * h / 13) for i in range(14)]

    # Makul boyuttaki kutular
    box_ys = []
    for cnt in contours:
        xc, yc, wc, hc = cv2.boundingRect(cnt)
        if wc >= 12 and hc >= 8 and wc * hc >= 150:
            box_ys.append(yc)
            box_ys.append(yc + hc)

    if not box_ys:
        logger.warning("Makul boyutlu input bulunamadı — eşit bölümleme")
        return [int(i * h / 13) for i in range(14)]

    # Y değerlerini kümele — her küme bir satır sınırı
    box_ys_sorted = sorted(set(box_ys))
    gap = max(8, h // 25)
    clusters = _cluster_positions(box_ys_sorted, tolerance=gap)

    positions = sorted(set([0] + clusters + [h]))
    merged = _merge_close_positions(positions, min_gap=12)

    logger.info("Input y-tespiti: %d satır sınırı", len(merged))
    return merged


# ─── Sütun Tespiti ───────────────────────────────────────────────────────────

def _detect_col_boundaries(table_img: np.ndarray) -> list[int]:
    """
    Tablo sütun sınırlarını tespit et.
    
    Yöntem 1: Morfik dikey çizgi tespiti
    Yöntem 2: Canny kenar tespiti ile ince dikey çizgiler
    Yöntem 3: Input widget sütunlarını tespit + e-okul şablon yapısı
    """
    h, w = table_img.shape[:2]
    gray = cv2.cvtColor(table_img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # ── Yöntem 1: Morfik dikey çizgi ──────────────────────────────────────────
    best_x, best_count = [], 0
    for scale in [5, 6, 8, 10, 12, 15, 20]:
        kl = max(1, h // scale)
        kern = cv2.getStructuringElement(cv2.MORPH_RECT, (1, kl))
        lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kern, iterations=2)
        proj = np.sum(lines, axis=0)
        thresh = proj.max() * 0.10 if proj.max() > 0 else 1
        pos = _get_line_positions_from_proj(proj, thresh)
        if len(pos) > best_count:
            best_count = len(pos)
            best_x = pos

    if best_count >= 5:
        logger.debug("Morfik dikey çizgi: %d sütun", best_count)
        positions = sorted(set([0] + best_x + [w]))
        return _merge_close_positions(positions, min_gap=8)

    # ── Yöntem 2: Canny kenar + dikey projeksiyon ─────────────────────────────
    logger.info("Morfik dikey çizgi yetersiz (%d), Canny tespiti", best_count)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    edges = cv2.Canny(enhanced, 20, 80)
    # Dikey kenarları seç
    v_kern = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(3, h // 12)))
    v_edges = cv2.morphologyEx(edges, cv2.MORPH_OPEN, v_kern)
    v_proj = np.sum(v_edges, axis=0).astype(float)
    if v_proj.max() > 0:
        canny_thresh = v_proj.max() * 0.12
        canny_pos = _get_line_positions_from_proj(v_proj, canny_thresh)
        if len(canny_pos) >= 5:
            positions = sorted(set([0] + canny_pos + [w]))
            positions = _merge_close_positions(positions, min_gap=8)
            logger.debug("Canny sütun tespiti: %d kenar", len(positions))
            return positions

    # ── Yöntem 3: Input widget sütunlarından e-okul şablonu ───────────────────
    logger.info("Canny yetersiz, input widget şablon tespiti")
    return _detect_cols_eokul_layout(table_img, h, w)


def _detect_cols_eokul_layout(table_img: np.ndarray, h: int, w: int) -> list[int]:
    """
    E-okul input kutucuklarının x konumlarından sütun yapısını çöz.
    
    Yöntem:
    1. Her input konturünün x kenarlarını topla
    2. Kenarları kümele → sütun sınırları
    3. Sol sabit sütunlar (Sıra, Okul No, Ad Soyad) ile birleştir
    """
    input_mask = _get_input_pixels_mask(table_img)
    
    # Küçük gürültüyü temizle
    k_open = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    k_close = cv2.getStructuringElement(cv2.MORPH_RECT, (6, 4))
    cleaned = cv2.morphologyEx(input_mask, cv2.MORPH_OPEN, k_open)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, k_close)
    
    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    x_lefts = []
    x_rights = []
    
    for cnt in contours:
        xc, yc, wc, hc = cv2.boundingRect(cnt)
        # Input kutu boyutu: min 15x8, max 400x100
        if wc >= 15 and hc >= 8 and wc <= 400 and hc <= 100 and wc * hc >= 180:
            x_lefts.append(xc)
            x_rights.append(xc + wc)
    
    if not x_lefts:
        logger.warning("Input kontur yok — 18 eşit sütun")
        return [int(i * w / 18) for i in range(19)]
    
    # Tüm x kenarlarını kümele
    all_x = sorted(set(x_lefts + x_rights))
    tolerance = max(8, w // 80)
    clustered = _cluster_positions(all_x, tolerance=tolerance)
    
    # Sınır listesi oluştur
    boundaries = sorted(set([0] + clustered + [w]))
    boundaries = _merge_close_positions(boundaries, min_gap=8)
    
    logger.info("Input layout sütun tespiti: %d kenar", len(boundaries))
    return boundaries


# ─── Yardımcılar ─────────────────────────────────────────────────────────────

def _merge_close_positions(positions: list[int], min_gap: int = 10) -> list[int]:
    """Birbirine çok yakın pozisyonları birleştir."""
    if not positions:
        return []
    merged = [positions[0]]
    for p in positions[1:]:
        if p - merged[-1] >= min_gap:
            merged.append(p)
    return merged


def _group_consecutive(indices: list[int], gap: int = 5) -> list[list[int]]:
    if not indices:
        return []
    groups = [[indices[0]]]
    for idx in indices[1:]:
        if idx - groups[-1][-1] <= gap:
            groups[-1].append(idx)
        else:
            groups.append([idx])
    return groups


def _cluster_positions(positions: list[int], tolerance: int = 10) -> list[int]:
    if not positions:
        return []
    sorted_pos = sorted(positions)
    clusters = [[sorted_pos[0]]]
    for p in sorted_pos[1:]:
        if p - clusters[-1][-1] <= tolerance:
            clusters[-1].append(p)
        else:
            clusters.append([p])
    return [int(np.mean(cluster)) for cluster in clusters]


def _get_line_positions_from_proj(
    projection: np.ndarray, threshold: float, group_gap: int = 5
) -> list[int]:
    candidate_idx = np.where(projection > threshold)[0]
    if len(candidate_idx) == 0:
        return []

    positions: list[int] = []
    group_start = int(candidate_idx[0])
    prev = int(candidate_idx[0])

    for idx in candidate_idx[1:]:
        idx = int(idx)
        if idx - prev > group_gap:
            positions.append((group_start + prev) // 2)
            group_start = idx
        prev = idx
    positions.append((group_start + prev) // 2)
    return positions


# ─── Ana Fonksiyon ───────────────────────────────────────────────────────────

def extract_cells(img_bgr: np.ndarray) -> list[Cell]:
    """
    Ana fonksiyon: e-okul ekran görüntüsünden hücre listesi çıkar.
    """
    h_img, w_img = img_bgr.shape[:2]
    logger.info("Görüntü boyutu: %dx%d", w_img, h_img)

    # ── 1. Tablo bölgesini belirle ─────────────────────────────────────────────
    sidebar_w = _detect_sidebar_width(img_bgr)
    y_start = _detect_table_header_y(img_bgr, x_start=sidebar_w)

    tx = sidebar_w
    ty = y_start
    tw = w_img - tx
    th = h_img - ty

    if tw < w_img * 0.30 or th < h_img * 0.15:
        logger.warning("Tablo bölgesi çok küçük, tüm görüntü kullanılıyor")
        tx, ty, tw, th = 0, 0, w_img, h_img

    table_img = img_bgr[ty:ty + th, tx:tx + tw]
    logger.info("Tablo kırpıldı: x=%d y=%d w=%d h=%d", tx, ty, tw, th)

    # ── 2. Satır ve sütun pozisyonlarını bul ─────────────────────────────────
    y_positions = _detect_row_boundaries(table_img)
    x_positions = _detect_col_boundaries(table_img)

    logger.info("Satır pozisyonları (%d): %s", len(y_positions), y_positions[:15])
    logger.info("Sütun pozisyonları (%d): %s", len(x_positions), x_positions[:25])

    if len(y_positions) < 2:
        y_positions = [int(i * th / 14) for i in range(15)]
    if len(x_positions) < 2:
        x_positions = [int(i * tw / 18) for i in range(19)]

    # ── 3. Hücreleri oluştur ──────────────────────────────────────────────────
    cells: list[Cell] = []
    pad = 2

    for r_idx, (y0, y1) in enumerate(zip(y_positions, y_positions[1:])):
        if y1 - y0 < 5:
            continue
        for c_idx, (x0, x1) in enumerate(zip(x_positions, x_positions[1:])):
            if x1 - x0 < 5:
                continue

            cy0 = max(0, y0 + pad)
            cy1 = min(th, y1 - pad)
            cx0 = max(0, x0 + pad)
            cx1 = min(tw, x1 - pad)

            crop = table_img[cy0:cy1, cx0:cx1] if cy1 > cy0 and cx1 > cx0 else None

            cells.append(Cell(
                row=r_idx,
                col=c_idx,
                x=x0 + tx,
                y=y0 + ty,
                w=x1 - x0,
                h=y1 - y0,
                image=crop if (crop is not None and crop.size > 0) else None
            ))

    logger.info("Toplam hücre: %d (%d satır × %d sütun)",
                len(cells), len(y_positions) - 1, len(x_positions) - 1)
    return cells
