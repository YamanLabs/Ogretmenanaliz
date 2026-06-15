"""
test_pipeline.py — E-Okul OCR Backend uçtan uca boru hattı (pipeline) test suite'i.
"""
from __future__ import annotations
import os
import sys
import unittest
from fastapi.testclient import TestClient

# Workspace dizinini Python yoluna ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from app.test_mock_generator import generate_mock_screenshot
from app.database import engine, Base


class TestEOkulOCRPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 1. Testler başlamadan önce temiz bir SQLite DB kullanması için tabloları sıfırla
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        
        # 2. Mock ekran görüntüsünü oluştur
        cls.mock_image_path = "mock_screenshot.png"
        generate_mock_screenshot(cls.mock_image_path)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        # Üretilen geçici görselleri temizle
        if os.path.exists(cls.mock_image_path):
            os.remove(cls.mock_image_path)

    def test_01_upload_and_parse_grades(self):
        """POST /api/upload endpoint'ini mock görsel ile test eder."""
        print("\n--- [Test 1] Görsel Yükleme ve OCR Analizi ---")
        
        with open(self.mock_image_path, "rb") as img_file:
            files = {"file": (self.mock_image_path, img_file, "image/png")}
            data = {"class_name": "10-A"}
            response = self.client.post("/api/upload", files=files, data=data)

        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        
        # Alan kontrolü
        self.assertEqual(json_data["class_name"], "10-A")
        self.assertIsNotNone(json_data["class_id"])
        self.assertGreaterEqual(json_data["total_rows"], 3)
        
        students = json_data["students"]
        
        # 1. Öğrenci kontrolü (Okul No: 542, Ahmet Yılmaz)
        # Notlar: 80, 90, 100, 90 -> Ortalama: 90.0 (Tüm notlar tam)
        ahmet = next((s for s in students if s["school_no"] == "542"), None)
        self.assertIsNotNone(ahmet, "Okul no 542 (Ahmet) bulunamadi.")
        self.assertIn("AHMET", ahmet["name"].upper())
        self.assertEqual(ahmet["exam1"], 80.0)
        self.assertEqual(ahmet["exam2"], 90.0)
        self.assertEqual(ahmet["perf1"], 100.0)
        self.assertEqual(ahmet["perf2"], 90.0)
        self.assertEqual(ahmet["calculated_average"], 90.0)
        self.assertEqual(ahmet["status"], "Geçti")
        self.assertTrue(ahmet["is_new_student"])
        
        # 2. Öğrenci kontrolü (Okul No: 125, Mehmet Kaya)
        # Notlar: 45, 50, 55, 40 -> Ortalama: 47.5 (Tüm notlar tam, Kaldı)
        mehmet = next((s for s in students if s["school_no"] == "125"), None)
        self.assertIsNotNone(mehmet, "Okul no 125 (Mehmet) bulunamadi.")
        self.assertEqual(mehmet["calculated_average"], 47.5)
        self.assertEqual(mehmet["status"], "Kaldı")
        
        # 3. Öğrenci kontrolü (Okul No: 871, Ayşe Demir)
        # Notlar: 70, G (None), 80, 90 -> Ortalama: None (çünkü 2. sınav eksik/G)
        ayse = next((s for s in students if s["school_no"] == "871"), None)
        self.assertIsNotNone(ayse, "Okul no 871 (Ayşe) bulunamadi.")
        self.assertEqual(ayse["exam1"], 70.0)
        self.assertIsNone(ayse["exam2"])  # G -> None olmalı
        self.assertEqual(ayse["perf1"], 80.0)
        self.assertEqual(ayse["perf2"], 90.0)
        self.assertIsNone(ayse["calculated_average"], "Eksik not varken ortalama None olmali.")
        self.assertEqual(ayse["status"], "Belirsiz")
        
        # BBox (koordinat) alanlarının doğruluğu
        for key in ["bbox_school_no", "bbox_name", "bbox_exam1"]:
            self.assertIsNotNone(ahmet[key], f"{key} koordinatlari eksik.")
            self.assertIn("x", ahmet[key])
            self.assertIn("y", ahmet[key])

        # Bir sonraki test için sınıf ID'sini sakla
        self.__class__.class_id = json_data["class_id"]
        self.__class__.extracted_students = students

    def test_02_save_grades(self):
        """POST /api/save-grades endpoint'ini test eder (akademik + gelişim notları)."""
        print("\n--- [Test 2] Notların SQLite Veritabanına Kaydı (Akademik + Gelişim) ---")
        
        grades_to_save = []
        for s in self.extracted_students:
            grades_to_save.append({
                "school_no": s["school_no"],
                "name": s["name"],
                "class_name": "10-A",
                "exam1": s["exam1"],
                "exam2": s["exam2"],
                "perf1": s["perf1"],
                "perf2": s["perf2"],
                "growth_attendance": 95.0,
                "growth_activities": 80.0,
                "growth_product": 85.0,
                "growth_social_emotional": 90.0,
                "growth_progress": 92.5,
                "term": "2024-2025-1"
            })
            
        payload = {"grades": grades_to_save}
        response = self.client.post("/api/save-grades", json=payload)
        
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertEqual(json_data["saved"], 3)
        self.assertEqual(json_data["updated"], 0)
        self.assertEqual(len(json_data["errors"]), 0)

        # Tekrar gönderildiğinde upsert güncelleme (updated) durumunu test et
        print("Aynı notlar tekrar gönderiliyor (güncelleme kontrolü)...")
        response_re = self.client.post("/api/save-grades", json=payload)
        self.assertEqual(response_re.status_code, 200)
        json_re = response_re.json()
        self.assertEqual(json_re["saved"], 0)
        self.assertEqual(json_re["updated"], 3)  # Tüm 3 kayıt güncellendi

    def test_03_export_excel(self):
        """GET /api/export-excel/{class_id} endpoint'ini test eder."""
        print("\n--- [Test 3] Renkli Excel Çıktısı Alma ---")
        
        response = self.client.get(f"/api/export-excel/{self.class_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["content-type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        self.assertIn("attachment; filename=", response.headers["content-disposition"])
        
        # Excel bayt dizisi boş olmamalı
        self.assertGreater(len(response.content), 1000)
        print("Akademik Excel başarıyla oluşturuldu ve indirildi.")

    def test_04_get_grades(self):
        """GET /api/grades/{class_id} endpoint'ini test eder."""
        print("\n--- [Test 4] Kaydedilen Sınıf Notlarının DB'den Çekilmesi ---")
        
        response = self.client.get(f"/api/grades/{self.class_id}?term=2024-2025-1")
        self.assertEqual(response.status_code, 200)
        students = response.json()
        
        self.assertEqual(len(students), 3)
        for s in students:
            # Gelişim alanlarının DB'den başarıyla yüklendiğini doğrula
            self.assertEqual(s["growth_attendance"], 95.0)
            self.assertEqual(s["growth_activities"], 80.0)
            self.assertEqual(s["growth_product"], 85.0)
            self.assertEqual(s["growth_social_emotional"], 90.0)
            self.assertEqual(s["growth_progress"], 92.5)
            
        print("Tüm akademik ve gelişim notları veritabanından başarıyla sorgulandı.")

    def test_05_export_growth_excel(self):
        """GET /api/export-growth-excel/{class_id} endpoint'ini test eder."""
        print("\n--- [Test 5] Gelişim Raporu Excel Çıktısı Alma ---")
        
        response = self.client.get(f"/api/export-growth-excel/{self.class_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["content-type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        self.assertIn("attachment; filename=", response.headers["content-disposition"])
        
        # Excel bayt dizisi boş olmamalı
        self.assertGreater(len(response.content), 1000)
        print("Gelişim Excel raporu başarıyla oluşturuldu ve indirildi.")


if __name__ == "__main__":
    unittest.main()
