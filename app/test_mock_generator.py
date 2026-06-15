"""
test_mock_generator.py — Programlı olarak test amaçlı e-okul ekran görüntüsü üreten modül.
"""
from __future__ import annotations
import cv2
import numpy as np


def generate_mock_screenshot(output_path: str = "mock_screenshot.png") -> None:
    # 1. Büyük bir tarayıcı penceresi oluştur (gri arka plan)
    h_win, w_win = 800, 1200
    img = np.ones((h_win, w_win, 3), dtype=np.uint8) * 240  # #F0F0F0 açık gri

    # 2. Üst tarayıcı barı / başlık alanı çiz
    cv2.rectangle(img, (0, 0), (w_win, 60), (33, 150, 243), -1)  # #2196F3 mavi
    cv2.putText(img, "e-Okul Veli Bilgilendirme Sistemi - Sinif Not Girisi", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)

    # 3. Sol menü barı çiz
    cv2.rectangle(img, (0, 60), (120, h_win), (55, 71, 79), -1)  # Koyu gri
    # Sol menü yazıları
    menus = ["Ana Sayfa", "Not Islemleri", "Sinif Tanimi", "Raporlar"]
    for i, menu in enumerate(menus):
        cv2.putText(img, menu, (10, 100 + i * 40), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1, cv2.LINE_AA)

    # 4. Tablo koordinatları (sidebar ve header dışında kalacak şekilde)
    # Tablo boyutu: 7 sütun x 5 satır (1 başlık + 1 sütun başlığı + 3 veri satırı)
    tx, ty = 180, 120
    row_height = 40
    col_widths = [60, 100, 220, 90, 90, 90, 90]  # Toplam genişlik = 740
    table_w = sum(col_widths)
    table_h = row_height * 5

    # Tablo alanını beyaz doldur (en dış çerçeve sınırlarını belirlemek için)
    cv2.rectangle(img, (tx, ty), (tx + table_w, ty + table_h), (255, 255, 255), -1)

    # Tablo içeriği:
    # Başlık satırı (Satır 0): Sınıf adı
    # Sütun başlıkları (Satır 1): Sıra, Okul No, Adi Soyadi, 1.Sinav, 2.Sinav, 1.Perf, 2.Perf
    # Veriler (Satır 2-4)
    data = [
        # Sınıf Başlığı (satır 0'da birleştirilmiş olacak ama çizimlerimizi hücre bazında yapacağız)
        ["10-A SINIFI NOT DOKUMU", "", "", "", "", "", ""],
        # Sütun Başlıkları
        ["Sira", "Okul No", "Adi Soyadi", "1.Sinav", "2.Sinav", "1.Perf", "2.Perf"],
        # Öğrenciler
        ["1", "542", "AHMET YILMAZ", "80", "90", "100", "90"],
        ["2", "125", "MEHMET KAYA", "45", "50", "55", "40"],
        ["3", "871", "AYSE DEMIR", "70", "G", "80", "90"],
    ]

    # Hücreleri çiz ve yazıları yaz
    for r_idx, row_data in enumerate(data):
        curr_y = ty + r_idx * row_height
        
        # Satır çizgisi
        cv2.line(img, (tx, curr_y), (tx + table_w, curr_y), (0, 0, 0), 2)
        
        curr_x = tx
        for c_idx, val in enumerate(row_data):
            w = col_widths[c_idx]
            
            # Başlık satırı birleştirme simülasyonu
            if r_idx == 0:
                if c_idx == 0:
                    # Birinci hücreye tüm başlığı yazalım
                    (text_w, text_h), _ = cv2.getTextSize(val, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
                    text_x = tx + (table_w - text_w) // 2
                    text_y = curr_y + (row_height + text_h) // 2
                    cv2.putText(img, val, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1, cv2.LINE_AA)
                curr_x += w
                continue

            # Diğer hücre yazıları
            if val:
                (text_w, text_h), _ = cv2.getTextSize(val, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
                text_x = curr_x + (w - text_w) // 2
                text_y = curr_y + (row_height + text_h) // 2
                cv2.putText(img, val, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1, cv2.LINE_AA)
            
            curr_x += w

    # En alt çizgi
    cv2.line(img, (tx, ty + table_h), (tx + table_w, ty + table_h), (0, 0, 0), 2)

    # Dikey sütun çizgilerini çiz
    curr_x = tx
    for w in col_widths:
        # Başlık satırı (Satır 0) hariç dikey çizgiler çekilsin
        cv2.line(img, (curr_x, ty + row_height), (curr_x, ty + table_h), (0, 0, 0), 2)
        curr_x += w
    # En sağ dikey çizgi
    cv2.line(img, (tx + table_w, ty), (tx + table_w, ty + table_h), (0, 0, 0), 2)
    # En sol dikey çizgi
    cv2.line(img, (tx, ty), (tx, ty + table_h), (0, 0, 0), 2)

    # Görseli kaydet
    cv2.imwrite(output_path, img)
    print(f"Mock görsel basariyla uretildi: {output_path}")


if __name__ == "__main__":
    generate_mock_screenshot()
