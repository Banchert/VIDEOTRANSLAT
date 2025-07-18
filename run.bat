@echo off
echo ========================================
echo    Video Translator - แปลวิดีโอ
echo ========================================
echo.

REM ตรวจสอบว่า Python ติดตั้งหรือไม่
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python ไม่ได้ติดตั้ง กรุณาติดตั้ง Python 3.8+ ก่อน
    pause
    exit /b 1
)

echo [INFO] ตรวจสอบ Python... OK
echo.

REM ตรวจสอบ virtual environment
if not exist "venv_py312\Scripts\activate.bat" (
    echo [INFO] สร้าง virtual environment...
    python -m venv venv_py312
    if errorlevel 1 (
        echo [ERROR] ไม่สามารถสร้าง virtual environment ได้
        pause
        exit /b 1
    )
)

echo [INFO] เปิดใช้งาน virtual environment...
call venv_py312\Scripts\activate.bat

REM ตรวจสอบ requirements.txt
if exist "requirements.txt" (
    echo [INFO] ติดตั้ง dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] ไม่สามารถติดตั้ง dependencies ได้
        pause
        exit /b 1
    )
) else (
    echo [WARNING] ไม่พบไฟล์ requirements.txt
)

echo.
echo [INFO] เริ่มต้นโปรแกรม...
echo [INFO] เปิดเบราว์เซอร์ไปที่: http://localhost:5556
echo.
echo [INFO] กด Ctrl+C เพื่อหยุดโปรแกรม
echo.

REM รันโปรแกรม
python main.py

echo.
echo [INFO] โปรแกรมหยุดทำงานแล้ว
pause 