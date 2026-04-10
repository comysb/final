import os
import shutil
import tempfile
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# 퍼터커 추론 엔진 로드
from pipeline.inference_engine import PutterkerInferenceEngine

app = FastAPI(
    title="말길 Putterker API",
    description="퍼터커 음성을 실시간 모델에 올려 진단 점수를 반환합니다.",
    version="1.0.0"
)

# CORS 설정 (React/Vite 프론트엔드 연동)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 엔진 (앱 실행 시 한 번만 로드)
# use_w2v = False 로 설정할 경우 매우 빠르게 응답이 가능합니다.
# v1 아키텍처에 맞게 Wav2Vec2를 활성화하려면 True로 변경하세요.
# (현재 w2v_encoder 랜덤 프로젝션 문제를 회피하기 위해 기본적으로 False 유지 권장)
engine = PutterkerInferenceEngine(use_w2v=False)

@app.get("/")
def read_root():
    return {"message": "Putterker Inference API is running."}

@app.post("/api/predict/putterker")
async def predict_putterker(audio: UploadFile = File(...)):
    """
    클라이언트에서 업로드한 퍼터커 오디오 파일을 받아 중증도 점수를 반환합니다.
    """
    if not audio.filename.endswith(('.wav', '.webm', '.ogg', '.m4a')):
        # 프론트 상황에 따라 다양한 오디오 포맷을 허용
        pass

    temp_path = ""
    try:
        ext = os.path.splitext(audio.filename)[1].lower()
        if not ext: ext = ".wav"
        
        # 원본 확장자로 임시 파일 생성
        fd, temp_path = tempfile.mkstemp(suffix=ext)
        os.close(fd)
        
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(audio.file, f)
            
        print(f"[{audio.filename}] 오디오 수신 및 분석 준비...")
        
        # wav가 아닌 경우 (ex: m4a, ogg, webm) wav로 변환
        if not temp_path.endswith('.wav'):
            print(f"[{audio.filename}] 포맷 변환 중 (-> wav)...")
            import librosa
            import soundfile as sf
            y, sr = librosa.load(temp_path, sr=16000)
            convert_path = temp_path + "_converted.wav"
            sf.write(convert_path, y, sr)
            os.remove(temp_path)  # 기존 원본 삭제
            temp_path = convert_path
        
        # 엔진 예측 실행 (점수 제외, 순수 중증도 분류)
        result = engine.predict(temp_path)
        
        return {
            "success": True,
            "filename": audio.filename,
            "result": result
        }
        
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # 분석이 끝난 임시 파일 삭제
        if os.path.exists(temp_path):
            os.remove(temp_path)

if __name__ == "__main__":
    import uvicorn
    # uvicorn app_backend:app --host 0.0.0.0 --port 8000
    uvicorn.run("app_backend:app", host="0.0.0.0", port=8000, reload=True)
