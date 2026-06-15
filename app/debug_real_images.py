"""
debug_real_images.py — v5 image_processor ile gerçek görüntü testi.
"""
import os
import logging
import cv2
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("debug_real")

IMAGE_PATHS = [
    r"C:\Users\YAMAN\Desktop\Screenshot 2026-06-10 115922.png",
    r"C:\Users\YAMAN\Desktop\IMG_2034.PNG",
]

OUT_DIR = r"C:\Users\YAMAN\Desktop\ANALIZ\debug_output3"
os.makedirs(OUT_DIR, exist_ok=True)


def test_image(img_path: str):
    from app.services.image_processor import (
        extract_cells, _detect_sidebar_width, _detect_table_header_y,
        _detect_row_boundaries, _detect_col_boundaries,
        _get_dark_navy_mask, _get_input_pixels_mask
    )

    img_name = os.path.splitext(os.path.basename(img_path))[0]
    logger.info("=" * 60)
    logger.info("Test ediliyor: %s", img_path)

    img_bgr = cv2.imread(img_path)
    if img_bgr is None:
        logger.error("HATA: Görüntü okunamadı")
        return

    h_img, w_img = img_bgr.shape[:2]
    logger.info("Boyut: %dx%d", w_img, h_img)

    # ── 1. Maskeler ───────────────────────────────────────────────────────────
    navy_mask = _get_dark_navy_mask(img_bgr)
    navy_vis = img_bgr.copy(); navy_vis[navy_mask > 0] = [0, 0, 255]
    cv2.imwrite(os.path.join(OUT_DIR, f"{img_name}_1_navy.png"), navy_vis)

    input_mask = _get_input_pixels_mask(img_bgr)
    input_vis = img_bgr.copy(); input_vis[input_mask > 0] = [0, 255, 0]
    cv2.imwrite(os.path.join(OUT_DIR, f"{img_name}_2_input.png"), input_vis)
    logger.info("Input piksel sayısı: %d", np.sum(input_mask > 0))

    # ── 2. Tablo bölgesi ─────────────────────────────────────────────────────
    sidebar_w = _detect_sidebar_width(img_bgr)
    table_y = _detect_table_header_y(img_bgr, x_start=sidebar_w)
    tx, ty = sidebar_w, table_y
    tw, th = w_img - tx, h_img - ty

    region_vis = img_bgr.copy()
    cv2.rectangle(region_vis, (tx, ty), (tx + tw, ty + th), (255, 0, 0), 3)
    cv2.imwrite(os.path.join(OUT_DIR, f"{img_name}_3_region.png"), region_vis)
    logger.info("Tablo bölgesi: x=%d y=%d w=%d h=%d", tx, ty, tw, th)

    table_img = img_bgr[ty:ty + th, tx:tx + tw]
    cv2.imwrite(os.path.join(OUT_DIR, f"{img_name}_4_table.png"), table_img)

    # ── 3. Grid tespiti ───────────────────────────────────────────────────────
    y_positions = _detect_row_boundaries(table_img)
    x_positions = _detect_col_boundaries(table_img)

    logger.info("Satır pozisyonları (%d): %s", len(y_positions), y_positions)
    logger.info("Sütun pozisyonları (%d): %s", len(x_positions), x_positions)

    # Grid görselleştirme
    grid_vis = table_img.copy()
    for y in y_positions:
        cv2.line(grid_vis, (0, y), (tw, y), (0, 255, 0), 1)
    for x in x_positions:
        cv2.line(grid_vis, (x, 0), (x, th), (255, 0, 0), 1)
    cv2.imwrite(os.path.join(OUT_DIR, f"{img_name}_5_grid.png"), grid_vis)

    # ── 4. Hücre çıkarma + OCR ────────────────────────────────────────────────
    cells = extract_cells(img_bgr)
    logger.info("Toplam hücre: %d", len(cells))

    # Hücre görüntülerini kaydet
    cell_dir = os.path.join(OUT_DIR, f"{img_name}_cells")
    os.makedirs(cell_dir, exist_ok=True)
    for cell in cells:
        if cell.row < 5 and cell.image is not None:
            cv2.imwrite(
                os.path.join(cell_dir, f"r{cell.row:02d}_c{cell.col:02d}.png"),
                cell.image
            )

    # OCR testi
    logger.info("--- OCR (ilk 5 satır, ilk 4 sütun) ---")
    try:
        from app.services.ocr_engine import read_text
        for cell in sorted(cells, key=lambda c: (c.row, c.col)):
            if cell.row < 5 and cell.col < 4 and cell.image is not None:
                text, conf = read_text(cell.image)
                if text:
                    logger.info("  [%d,%d]: '%s' (%.2f)", cell.row, cell.col, text, conf)
    except Exception as e:
        logger.warning("OCR atlandı: %s", e)

    logger.info("Debug: %s", OUT_DIR)


if __name__ == "__main__":
    for path in IMAGE_PATHS:
        try:
            test_image(path)
        except Exception as e:
            logger.exception("HATA: %s", path)
    logger.info("Tamamlandı.")
