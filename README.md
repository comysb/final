# final
severity_app: 마비말장애 중증도 진단 앱 (Port 8000)

## 실행 방법
```bash
uvicorn app:app --reload --port 8000
```

## 의존성
```bash
pip install fastapi uvicorn xgboost joblib torch transformers librosa soundfile parselmouth
```
