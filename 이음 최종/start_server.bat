@echo off
title 이음 서버 (포트 8080)
cd /d D:\이음최종\backend

echo.
echo ========================================
echo  이음 통합 서버 시작 중...
echo  http://localhost:8080
echo  http://localhost:8080/maeum/
echo ========================================
echo.

python -m uvicorn main:app --host 0.0.0.0 --port 8080

echo.
echo [서버 종료됨] 아무 키나 누르면 창이 닫힙니다.
pause
