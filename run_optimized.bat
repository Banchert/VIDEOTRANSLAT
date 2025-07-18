@echo off
chcp 65001 >nul
title Video Translator - Optimized Version

echo.
echo ========================================
echo    Video Translator - Optimized Version
echo ========================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python ไม่ได้ติดตั้งหรือไม่พบใน PATH
    echo กรุณาติดตั้ง Python 3.8+ และลองใหม่
    pause
    exit /b 1
)

:: Check if virtual environment exists
if not exist "venv_py312\Scripts\activate.bat" (
    echo ⚠️  Virtual environment ไม่พบ
    echo กำลังสร้าง virtual environment...
    python -m venv venv_py312
    if errorlevel 1 (
        echo ❌ ไม่สามารถสร้าง virtual environment ได้
        pause
        exit /b 1
    )
)

:: Activate virtual environment
echo 🔧 กำลังเปิดใช้งาน virtual environment...
call venv_py312\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ ไม่สามารถเปิดใช้งาน virtual environment ได้
    pause
    exit /b 1
)

:: Check if requirements are installed
echo 📦 ตรวจสอบ dependencies...
python -c "import flask, torch, transformers" >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Dependencies ไม่ครบ กำลังติดตั้ง...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ❌ ไม่สามารถติดตั้ง dependencies ได้
        pause
        exit /b 1
    )
)

:: Create necessary directories
echo 📁 สร้างโฟลเดอร์ที่จำเป็น...
if not exist "uploads" mkdir uploads
if not exist "outputs" mkdir outputs
if not exist "temp" mkdir temp
if not exist "logs" mkdir logs
if not exist "texts" mkdir texts
if not exist "previews" mkdir previews
if not exist "audios" mkdir audios
if not exist "models" mkdir models

:: Set environment variables for optimization
set FLASK_ENV=production
set PYTHONOPTIMIZE=1
set PYTHONDONTWRITEBYTECODE=1

:: Memory optimization settings
set PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128

echo.
echo 🚀 เริ่มต้นแอปพลิเคชัน Video Translator (Optimized)
echo 📊 Memory optimization: เปิดใช้งาน
echo 🔒 Thread safety: เปิดใช้งาน
echo 🧹 Auto cleanup: เปิดใช้งาน
echo.

REM ตรวจสอบว่า venv_py312 มีอยู่หรือไม่
if not exist "venv_py312\Scripts\activate.bat" (
    echo ❌ ไม่พบ venv_py312 กรุณาสร้าง virtual environment ก่อน
    echo.
    echo 📋 คำสั่งสร้าง venv:
    echo py -3.12 -m venv venv_py312
    echo venv_py312\Scripts\activate
    echo pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo กำลังรัน main_optimized.py...
echo.

REM เปิดใช้งาน venv และรันแอปพลิเคชัน
call venv_py312\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ ไม่สามารถเปิดใช้งาน venv ได้
    pause
    exit /b 1
)

echo ✅ เปิดใช้งาน venv สำเร็จ
echo 🐍 Python version: 
python --version
echo.

REM ตรวจสอบ GPU support
echo 🔍 ตรวจสอบ GPU support...
python -c "import torch; print('PyTorch CUDA:', torch.cuda.is_available())"
python -c "import onnxruntime as ort; print('ONNX Runtime:', ort.get_device())"
echo.

REM รันแอปพลิเคชัน
echo 🚀 Starting Video Translator Application (Optimized)
echo 🧹 Memory optimization enabled
echo 📊 Memory monitoring enabled
echo 🔒 Thread safety enabled
echo 🧹 Memory cleanup completed
echo.

python main_optimized.py

REM ถ้าแอปพลิเคชันหยุดทำงาน
echo.
echo ⚠️ แอปพลิเคชันหยุดทำงาน
echo 📋 กดปุ่มใดก็ได้เพื่อปิดหน้าต่าง...
pause 