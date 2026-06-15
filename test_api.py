"""
test_api.py — FastAPI upload endpoint'ini gerçek görüntülerle test et.
"""
import sys
import requests
import json

BASE_URL = "http://127.0.0.1:8001/api/v1"
TEST_IMAGES = [
    (r"C:\Users\YAMAN\Desktop\Screenshot 2026-06-10 115922.png", "10-A"),
    (r"C:\Users\YAMAN\Desktop\IMG_2034.PNG", "10-B"),
]


def test_upload(img_path: str, class_name: str):
    print(f"\n{'='*60}")
    print(f"Test: {img_path}")
    print(f"Sınıf: {class_name}")
    
    try:
        with open(img_path, "rb") as f:
            r = requests.post(
                f"{BASE_URL}/upload",
                data={"class_name": class_name},
                files={"file": ("img.png", f, "image/png")},
                timeout=300
            )
        
        if r.status_code != 200:
            print(f"HATA {r.status_code}: {r.text[:500]}")
            return
        
        data = r.json()
        print(f"Öğrenci sayısı: {len(data['students'])}")
        print(f"Uyarılar: {data.get('warnings', [])}")
        print()
        
        # İlk 5 öğrenciyi göster
        for s in data["students"][:5]:
            print(f"  Okul No: {s['school_no']:>5} | Ad: {s['name']:<25} | "
                  f"Sınav1: {s.get('exam1', '-'):>4} | Perf1: {s.get('perf1', '-'):>4} | "
                  f"Ort: {s.get('calculated_average', '-'):>5}")
    
    except Exception as e:
        print(f"HATA: {e}")


if __name__ == "__main__":
    for img_path, class_name in TEST_IMAGES:
        test_upload(img_path, class_name)
    print("\nTamam.")
