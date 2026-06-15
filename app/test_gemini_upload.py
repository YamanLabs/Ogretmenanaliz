from __future__ import annotations

import os
import unittest
from unittest.mock import patch

import numpy as np
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.services import gemini_extractor
from app.services.gemini_extractor import GeminiStudent
from main import app


class TestGeminiUpload(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.Session = sessionmaker(bind=cls.engine)
        Base.metadata.create_all(bind=cls.engine)

        def override_get_db():
            db = cls.Session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=cls.engine)
        cls.engine.dispose()

    def test_gemini_maps_students_without_local_ocr(self):
        fake_rows = [
            GeminiStudent("542", "AHMET YILMAZ", 80.0, 90.0, 100.0, 90.0),
            GeminiStudent("871", "AYŞE DEMİR", 70.0, None, 80.0, 90.0),
        ]
        png_bytes = b"\x89PNG\r\n\x1a\nnot-decoded-by-opencv"

        with (
            patch.object(
                gemini_extractor,
                "extract_students_with_gemini",
                return_value=fake_rows,
            ) as gemini_mock,
            patch("app.routers.upload.extract_cells") as extract_cells_mock,
            patch("app.routers.upload.read_text") as read_text_mock,
            patch("app.routers.upload.read_name") as read_name_mock,
            patch("app.routers.upload._decode_image") as decode_mock,
        ):
            response = self.client.post(
                "/api/upload",
                data={"class_name": "GEMINI-10-A", "processor": "gemini"},
                files={"file": ("table.png", png_bytes, "image/png")},
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data["total_rows"], 2)
        self.assertEqual(data["students"][0]["calculated_average"], 90.0)
        self.assertEqual(data["students"][1]["exam2"], None)
        self.assertIsNone(data["students"][1]["calculated_average"])
        self.assertEqual(data["students"][1]["status"], "Belirsiz")
        self.assertIsNone(data["students"][0]["bbox_school_no"])
        gemini_mock.assert_called_once_with(png_bytes, "image/png")
        extract_cells_mock.assert_not_called()
        read_text_mock.assert_not_called()
        read_name_mock.assert_not_called()
        decode_mock.assert_not_called()

    def test_default_processor_stays_local(self):
        with (
            patch(
                "app.routers.upload._decode_image",
                return_value=np.zeros((10, 10, 3), dtype=np.uint8),
            ),
            patch("app.routers.upload.extract_cells", return_value=[]) as extract_cells_mock,
            patch.object(gemini_extractor, "extract_students_with_gemini") as gemini_mock,
        ):
            response = self.client.post(
                "/api/upload",
                data={"class_name": "LOCAL-DEFAULT"},
                files={"file": ("table.png", b"local-image", "image/png")},
            )

        self.assertEqual(response.status_code, 422)
        extract_cells_mock.assert_called_once()
        gemini_mock.assert_not_called()

    def test_gemini_error_is_returned_without_local_fallback(self):
        error = gemini_extractor.GeminiExtractionError(
            "Gemini API kotası aşıldı.",
            status_code=429,
        )
        with (
            patch.object(
                gemini_extractor,
                "extract_students_with_gemini",
                side_effect=error,
            ),
            patch("app.routers.upload.extract_cells") as extract_cells_mock,
        ):
            response = self.client.post(
                "/api/upload",
                data={"class_name": "GEMINI-ERROR", "processor": "gemini"},
                files={"file": ("table.png", b"\x89PNG\r\n\x1a\n", "image/png")},
            )

        self.assertEqual(response.status_code, 429)
        self.assertIn("kota", response.json()["detail"].lower())
        extract_cells_mock.assert_not_called()


class TestGeminiExtractor(unittest.TestCase):
    def test_invalid_grade_becomes_null(self):
        rows = gemini_extractor._parse_response_text(
            """
            {
              "students": [{
                "school_no": "125",
                "name": "MEHMET KAYA",
                "exam1": "101",
                "exam2": "-2",
                "perf1": "G",
                "perf2": "88"
              }]
            }
            """
        )
        self.assertIsNone(rows[0].exam1)
        self.assertIsNone(rows[0].exam2)
        self.assertIsNone(rows[0].perf1)
        self.assertEqual(rows[0].perf2, 88.0)

    def test_broken_or_extra_json_is_rejected(self):
        with self.assertRaises(gemini_extractor.GeminiExtractionError):
            gemini_extractor._parse_response_text("{broken")

        with self.assertRaises(gemini_extractor.GeminiExtractionError):
            gemini_extractor._parse_response_text(
                """
                {
                  "students": [{
                    "school_no": "125",
                    "name": "MEHMET KAYA",
                    "exam1": "45",
                    "exam2": "50",
                    "perf1": null,
                    "perf2": null,
                    "Puani": "95"
                  }]
                }
                """
            )

    def test_prompt_ignores_calculated_score_column(self):
        self.assertIn('"Puanı"', gemini_extractor.EXTRACTION_PROMPT)
        self.assertIn("performans notu olarak kullanma", gemini_extractor.EXTRACTION_PROMPT)

    def test_missing_key_and_api_errors_are_friendly(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(gemini_extractor.GeminiExtractionError) as missing:
                gemini_extractor.extract_students_with_gemini(b"img", "image/png")
        self.assertEqual(missing.exception.status_code, 503)
        self.assertIn("GEMINI_API_KEY", str(missing.exception))

        quota = type("QuotaError", (Exception,), {"status_code": 429})("quota")
        quota_error = gemini_extractor._friendly_api_error(quota)
        self.assertEqual(quota_error.status_code, 429)
        self.assertIn("kota", str(quota_error).lower())

        network_error = gemini_extractor._friendly_api_error(
            ConnectionError("network unavailable")
        )
        self.assertEqual(network_error.status_code, 503)
        self.assertIn("baglanilamadi", str(network_error))


if __name__ == "__main__":
    unittest.main()
