"""
test_syntax.py — Hızlı import testi.
Tüm modüllerin sözdizimi hatası olmadan import edildiğini doğrular.
Kullanım: python test_syntax.py
"""
import sys

modules_to_test = [
    "app.database",
    "app.models",
    "app.schemas",
    "app.services.grade_parser",
    "app.services.student_matcher",
    "app.services.image_processor",
    "app.services.excel_exporter",
    "app.routers.upload",
    "app.routers.grades",
    "app.routers.export",
    "main",
]

errors = []
for module in modules_to_test:
    try:
        __import__(module)
        print(f"  ✅ {module}")
    except Exception as e:
        print(f"  ❌ {module}: {e}")
        errors.append((module, e))

print()
if errors:
    print(f"BAŞARISIZ: {len(errors)} modülde hata var.")
    sys.exit(1)
else:
    print(f"BAŞARILI: {len(modules_to_test)} modülün tümü doğru import edildi.")
