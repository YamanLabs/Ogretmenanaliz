@echo off
REM E-Okul OCR Backend - Kurulum ve Başlatma Scripti
REM Kullanım: setup_and_run.bat

echo ============================================
echo  E-Okul OCR Backend Kurulum Scripti
echo ============================================
echo.

REM Python varlık kontrolü
python --version >nul 2>&1
if errorlevel 1 (
    echo [HATA] Python bulunamadi! Python 3.10+ yukleyin.
    pause
    exit /b 1
)

REM Sanal ortam oluştur (yoksa)
if not exist "venv\" (
    echo [1/4] Sanal ortam olusturuluyor...
    python -m venv venv
    echo      Tamamlandi.
) else (
    echo [1/4] Sanal ortam zaten mevcut. Atlanıyor.
)

REM Sanal ortamı etkinleştir
echo [2/4] Sanal ortam etkinlestiriliyor...
call venv\Scripts\activate.bat

REM Bağımlılıkları yükle
echo [3/4] Bagimliliklar yukleniyor (ilk kurulumda 3-5 dakika surebilir)...
pip install --upgrade pip --quiet
pip install -r requirements.txt

echo [4/4] Uygulama baslatiliyor...
echo.
echo  Swagger UI : http://127.0.0.1:8000/docs
echo  Saglik     : http://127.0.0.1:8000/health
echo.
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

pause
