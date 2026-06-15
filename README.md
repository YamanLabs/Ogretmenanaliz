# E-Okul OCR Backend — README

## Proje Hakkında

Fizik öğretmeninin **e-okul toplu sınıf not girişi** ekran görüntülerinden veri ayıklayan, tamamen yerelde (local) ve CPU üzerinde çalışan **FastAPI** backend'i.

### Özellikler
- 🔍 **OpenCV** ile tablo hücresi tespiti (morfik filtreler + çizgi analizi)
- 🤖 **EasyOCR** ile Türkçe karakter desteğli OCR (GPU gerektirmez)
- ✨ **Gemini 3.1 Flash-Lite** ile isteğe bağlı doğrudan görsel analizi
- 🧠 **Akıllı Öğrenci Eşleştirme** — okul numarasıyla DB sorgusu + fuzzy isim düzeltme
- 📊 **SQLite** veritabanı (`local_eokul.db`) ile kalıcı hafıza
- 📈 **Renkli Excel Çıktısı** — Geçti/Kaldı durumuna göre renklendirme
- ⚡ Tek seferlik OCR model yüklemesi (singleton pattern)

---

## Kurulum

### Gereksinimler
- Python 3.10+
- Windows / Linux / macOS

### Adımlar

```bash
# 1. Sanal ortam oluştur
python -m venv venv

# 2. Etkinleştir (Windows)
venv\Scripts\activate

# 3. Bağımlılıkları yükle
pip install -r requirements.txt

# 4. Gemini kullanılacaksa .env dosyasını hazırla
copy .env.example .env

# 5. Uygulamayı başlat
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Gemini seçeneği için `.env` içindeki `GEMINI_API_KEY` alanını doldurun. Model
kimliği varsayılan olarak `gemini-3.1-flash-lite` değeridir ve gerekirse
`GEMINI_MODEL` ile değiştirilebilir. API anahtarı arayüzden alınmaz.

> **Windows kullanıcıları için:** `setup_and_run.bat` dosyasını çift tıklayarak da başlatabilirsiniz.

---

## API Kullanımı

### Swagger UI
http://127.0.0.1:8000/docs

### Uç Noktalar

| Method | Yol | Açıklama |
|--------|-----|----------|
| `GET` | `/health` | Servis durumu |
| `POST` | `/api/upload` | Görsel → öğrenci/not verisi |
| `POST` | `/api/save-grades` | Notları DB'ye kaydet |
| `GET` | `/api/export-excel/{class_id}` | Renkli Excel indir |

---

### `POST /api/upload` — Örnek İstek

```bash
curl -X POST http://localhost:8000/api/upload \
  -F "class_name=10-A" \
  -F "processor=local" \
  -F "file=@ekran_goruntüsü.png"
```

`processor` alanı isteğe bağlıdır. Varsayılan `local` değeridir; Gemini için
`processor=gemini` gönderilir. Gemini başarısız olursa yerel OCR otomatik
olarak çalıştırılmaz.

**Örnek Yanıt:**
```json
{
  "class_name": "10-A",
  "class_id": 1,
  "total_rows": 25,
  "students": [
    {
      "row_index": 2,
      "school_no": "12345",
      "name": "AHMET YILMAZ",
      "exam1": 75.0,
      "exam2": 80.0,
      "perf1": null,
      "perf2": 65.0,
      "calculated_average": 73.33,
      "status": "Geçti",
      "is_new_student": false,
      "bbox_school_no": {"x": 10, "y": 120, "w": 80, "h": 30},
      ...
    }
  ],
  "warnings": []
}
```

### `POST /api/save-grades` — Örnek İstek

```json
{
  "grades": [
    {
      "school_no": "12345",
      "name": "AHMET YILMAZ",
      "class_name": "10-A",
      "exam1": 75.0,
      "exam2": 80.0,
      "perf1": null,
      "perf2": 65.0,
      "term": "2024-2025-1"
    }
  ]
}
```

### `GET /api/export-excel/1`

Sınıf ID=1 için `10-A_notlar.xlsx` dosyasını indirir.

---

## Proje Yapısı

```
ANALIZ/
├── main.py                     # FastAPI giriş noktası
├── requirements.txt            # Bağımlılıklar
├── setup_and_run.bat           # Windows kurulum scripti
├── local_eokul.db              # SQLite (otomatik oluşur)
├── eokul_ocr.log               # Uygulama logları
│
└── app/
    ├── database.py             # SQLAlchemy engine & session
    ├── models.py               # ORM modelleri
    ├── schemas.py              # Pydantic şemaları
    │
    ├── routers/
    │   ├── upload.py           # POST /api/upload
    │   ├── grades.py           # POST /api/save-grades
    │   └── export.py           # GET /api/export-excel/{id}
    │
    └── services/
        ├── image_processor.py  # OpenCV hücre tespiti
        ├── ocr_engine.py       # EasyOCR singleton
        ├── grade_parser.py     # Not ayrıştırma
        ├── student_matcher.py  # DB eşleştirme + fuzzy
        └── excel_exporter.py   # Renkli Excel çıktısı
```

---

## Not Hesaplama Formülü

```
Ortalama = (Sınav1 + Sınav2 + Perf1 + Perf2) / 4
```

- Boş hücre veya "G" → `null`; dört nottan biri eksikse ortalama hesaplanmaz
- Ortalama ≥ 50 → **Geçti** 🟢
- Ortalama < 50 → **Kaldı** 🔴
- Tüm notlar eksik → **Belirsiz** 🟡

---

## Lisans

Yalnızca okul içi kullanım amaçlıdır.
