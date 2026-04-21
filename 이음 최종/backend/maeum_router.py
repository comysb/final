"""
마음이음 (service) API 라우터 — /maeum/* prefix
main.py에서 include_router로 등록됩니다.
"""
import base64
import asyncio
import json
import warnings
import os

import numpy as np
import pandas as pd
import joblib

from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

warnings.filterwarnings("ignore")

from dotenv import load_dotenv
load_dotenv(dotenv_path=r"D:\service\.env", override=False)

from openai import AsyncOpenAI
oc = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# ── 경로 설정
SVC_DIR  = Path(r"D:\service")
USER_DB  = SVC_DIR / "user_db.json"
HRV_PKL  = SVC_DIR / "xgboost_depression_model.pkl"
IDX_FILE = SVC_DIR / "manual_index.faiss"
META_FILE = SVC_DIR / "manual_metadata.json"

# ── HRV 모델
hrv_model = None
hrv_feats = []
try:
    if HRV_PKL.exists():
        hrv_model = joblib.load(HRV_PKL)
        print("[마음이음] HRV XGBoost 모델 로드 완료")
except Exception as e:
    print(f"[마음이음] HRV 모델 로드 오류: {e}")

# ── RAG 지식 베이스
k_index  = None
k_chunks = []
try:
    if IDX_FILE.exists() and META_FILE.exists():
        import faiss
        k_index = faiss.read_index(str(IDX_FILE))
        with open(META_FILE, 'r', encoding='utf-8') as f:
            k_chunks = json.load(f)
        print(f"[마음이음] RAG 로드 완료: {len(k_chunks)}청크")
except Exception as e:
    print(f"[마음이음] RAG 로드 오류: {e}")

# ── 라우터
router = APIRouter(prefix="/maeum", tags=["마음이음"])

# ── 스키마
class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    diagnostic_context: Optional[Dict] = None
    session: Optional[str] = None

class SentimentRequest(BaseModel):
    text: str

class UserData(BaseModel):
    data: Dict

class HRVRequest(BaseModel):
    samples: List[Dict[str, float]]

SESSION_ARC = """【전문 상담 6단계 구조】
아래 순서를 철저히 준수하여 대화를 이끌어가세요:
1. 상황(Situation): 사용자의 현재 상황과 주요 활동을 탐색합니다.
   - **아침 대화 (Morning Chat)**: 다정하게 아침 인사를 건네고 밤사이 안부를 물으세요.
   - **저녁 회고 (Evening Review)**: 오늘 하루 전체의 일과와 주요 활동을 되돌아보며 탐색합니다.
   - **중요: 활동 언급 시 반드시 정확한 '시간'을 확인해야 합니다. 하지만 첫 번째 인사(Opening) 단계에서는 무조건 '활동의 내용'부터 물어보고, 시간 정보는 두 번째 질문에서 확인하여 사용자가 한 번에 많은 정보를 입력하게 하지 마세요.**
2. 감정(Emotion): 상황과 시간이 모두 확인된 후에 현재 느껴지는 주관적인 감정을 확인하고, 반드시 "0점에서 10점 사이에서 지금 기분은 몇 점인가요?"라고 질문하여 구체적인 점수를 얻으세요.
3. 원인(Cause): 그 감정이 들게 된 배경이나 구체적인 사건, 맥락을 탐색합니다.
4. 패턴(Pattern): 해당 상황에서의 생각을 확인하고, '인지적 오류(생각의 함정)'가 있는지 함께 살펴봅니다.
5. 감각(Sensation): 그 기분이나 생각을 할 때 몸에서는 어떤 반응(가슴 답답함, 어깨 무거움 등)이 느껴지는지 확인합니다.
6. 대응(Response): 지금 바로 실천할 수 있는 활동(BA)을 추천하고, "내일 오전 10시에 산책을 예약해드릴까요?"와 같이 구체적인 시간과 함께 예약을 유도하세요.
※ 단계 번호를 직접 말하지 마세요.
※ 사용자가 예약을 수락(예: "응", "그래", "해줘", "좋아")하면, `automated_action`을 통해 기술적으로 예약 처리를 수행해야 합니다."""

# ── 유틸
async def score_mood(txt: str) -> Optional[int]:
    try:
        r = await oc.chat.completions.create(
            model="gpt-4o",
            messages=[{"role":"user","content":f"0~10 정수 하나만:\n{txt[:200]}"}],
            max_tokens=3, temperature=0
        )
        return max(0, min(10, int(r.choices[0].message.content.strip())))
    except Exception:
        return None

# ── 엔드포인트 ─────────────────────────────────────────

@router.get("/")
@router.get("/index.html")
def serve_index():
    return FileResponse(SVC_DIR / "index.html")

@router.post("/chat")
async def chat(p: ChatRequest):
    try:
        msgs = p.messages
        ui = msgs[-1].get("content","").strip() if msgs and msgs[-1].get("role")=="user" else ""

        diag = p.diagnostic_context or {}
        diag_info = ""
        if diag:
            hrv = diag.get("hrv", {})
            phq = diag.get("phq9", {})
            if hrv or phq:
                diag_info = "【최근 검사 결과】\n"
                if hrv:
                    diag_info += f"- HRV 스트레스 지수: {hrv.get('stress','알 수 없음')}%, 위험도: {hrv.get('risk','정보 없음')}\n"
                if phq:
                    diag_info += f"- PHQ-9 우울 점수: {phq.get('score','알 수 없음')}점 ({phq.get('label','정보 없음')})\n"
                diag_info += "상담 시작 시 이 결과를 먼저 언급하며 충분히 공감해 주세요.\n\n"

        session_type = p.session or "알 수 없음"
        session_context = f"【현재 세션】: {'아침 대화 (Morning Chat)' if session_type=='morning' else '저녁 회고 (Evening Review)' if session_type=='evening' else '일반 상담'}\n\n"

        from datetime import datetime
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        weekday_str = ["월요일","화요일","수요일","목요일","금요일","토요일","일요일"][now.weekday()]
        time_str = now.strftime("%H:%M")

        # RAG 검색 (쿼리 확장 포함)
        ctx = ""
        if ui and k_index and k_chunks:
            try:
                recent_turns = [m["content"] for m in msgs[-4:] if m.get("role") in ("user","assistant")]
                search_query = " ".join(recent_turns[-3:]) if recent_turns else ui

                expansion_map = {
                    "끔찍": "distress cognitive distortion catastrophizing",
                    "최악": "negative thinking depression pessimism",
                    "죽고 싶": "suicidal ideation crisis intervention",
                    "힘들어": "depression difficulty coping behavioral activation",
                    "무기력": "anhedonia loss of motivation behavioral withdrawal",
                    "화": "anger frustration emotion regulation CBT",
                    "불안": "anxiety cognitive behavioral therapy worry",
                    "외로": "social withdrawal isolation behavioral activation",
                    "우울": "depression behavioral activation CBT treatment",
                    "귀찮": "avoidance behavior activation motivation",
                }
                for k, v in expansion_map.items():
                    if k in ui:
                        search_query += f" {v}"

                er = await oc.embeddings.create(input=search_query, model="text-embedding-3-small")
                qv = np.array([er.data[0].embedding]).astype('float32')
                import faiss
                _, I = k_index.search(qv, 6)
                docs = [k_chunks[i] for i in I[0] if i < len(k_chunks)]
                ctx  = "\n\n".join([f"[근거 {j+1}]: {d}" for j, d in enumerate(docs)])
            except Exception:
                pass

        no_context_msg = "(지식 베이스 연결 실패 — 일반 CBT/BA 원칙에 따라 진행하세요.)"
        sys_c = (
            f"당신은 행동활성화(BA)와 인지행동치료(CBT) 전문 '마음이음' 상담사입니다. "
            f"사용자를 다정하게 대하며, 친구처럼 편안하면서도 전문적인 통찰을 제공하세요.\n\n"
            f"【현재 시각 정보】\n"
            f"오늘은 {date_str} {weekday_str}이며, 현재 시각은 {time_str}입니다. "
            f"사용자가 '오늘', '내일', '이따가' 등의 상대적 시간을 언급하면 이 정보를 바탕으로 정확한 YYYY-MM-DD 날짜를 계산하세요.\n\n"
            f"{SESSION_ARC}\n\n"
            f"{session_context}"
            f"{diag_info}"
            "【핵심 상담 규칙】\n"
            "1. **심층적 공감 및 지지**: 사용자의 말에 단순히 동의하는 것을 넘어, 사용자가 느꼈을 감정과 상황을 구체적으로 반영(Mirroring)하여 공감해 주세요.\n"
            "2. **이모지 사용 금지**: 대화 메시지(`reply`) 내에서는 화려한 이모지나 아이콘을 절대 사용하지 마세요.\n"
            "3. **패턴 중심**: 사용자가 상황을 공유하면, 인지적 함정이나 행동 패턴을 명확히 요약해주고 공감을 받으세요.\n"
            "4. **연속성 유지**: 메시지 기록에 언급된 과거 활동이 있다면, 이를 기억하고 자연스럽게 관련 질문을 던져 실제 대화하는 느낌을 주세요.\n"
            "5. **적절한 분량과 깊이**: 한 번의 답변은 3~5문장 정도로 따뜻하게 작성하세요.\n"
            "6. **세션별 오프닝 차별화**: 아침 대화라면 상쾌한 아침 인사, 저녁 회고라면 수고한 하루에 대한 위로로 시작하세요.\n"
            "7. **대화 주도성 및 단계적 질문 (핵심)**: 한 번에 하나의 주제만 다루세요. 대화 시작 시에는 '무엇을 했는지(활동명)'를 먼저 물어보고, '언제 했는지(시간)'는 다음 차례에 물어보세요.\n"
            "8. **단계별 준수**: 6단계 구조를 건너뛰거나 합치지 마세요.\n"
            "9. **진단 결과 연동**: 최근 검사 결과가 있다면 반드시 오프닝에서 먼저 언급하세요.\n\n"
            f"【치료 근거 (BA·CBT 매뉴얼)】\n"
            f"{ctx if ctx else no_context_msg}\n\n"
            "【응답 형식】\n"
            "반드시 아래의 JSON 형식으로만 답변하세요. 모든 텍스트는 반드시 한국어로 작성하세요:\n"
            "{\n"
            "  \"reply\": \"(사용자에게 보낼 메시지)\",\n"
            "  \"choices\": [ {\"label\": \"...\", \"text\": \"...\"} ],\n"
            "  \"automated_action\": \"BOOK_ACTIVITY\" 또는 null,\n"
            "  \"action_metadata\": { \"activity\": \"활동명\", \"time\": \"HH:mm\", \"date\": \"YYYY-MM-DD\" } 또는 null\n"
            "}\n"
            "- **`choices`는 반드시 3개에서 5개 사이로 생성하세요.**\n"
            "- **중요: `choices`에서 이모지(`emoji`) 필드를 완전히 제거하고, 오직 `label`과 `text`만 포함하세요.**\n"
            "- **중요: `choices`의 `label`과 `text`는 반드시 한국어로, 사용자(내담자)의 관점에서 작성된 '완전한 답변 형식'이어야 합니다. 절대 상담사에게 되묻는 질문 형식을 사용하지 마세요.**\n"
            "- **중요: 모든 `choices`는 사용자가 자신의 생각이나 감정을 고백하거나 선언하는 1인칭 평서문 형태(예: ~인 것 같아요, ~했어요)여야 합니다.**\n"
            "- **중요: 활동 시간을 물어볼 때(`choices`), '시간 알려주기'와 같은 추상적인 표현 대신 '7시쯤 했어요', '8시쯤 했어요'와 같이 구체적인 시간(숫자)이 포함된 답변 형식을 제공하세요.**\n"
            "- **중요: `automated_action`은 오직 사용자가 명시적으로 동의하거나 구체적인 시간을 말하며 예약을 요청했을 때만 포함시키세요.**"
        )

        if msgs and msgs[0].get("role") == "system":
            msgs[0]["content"] = sys_c
        else:
            msgs.insert(0, {"role":"system","content":sys_c})

        r = await oc.chat.completions.create(
            model="gpt-4o", messages=msgs,
            temperature=0.9, max_tokens=1200,
            response_format={"type":"json_object"}
        )
        rd    = json.loads(r.choices[0].message.content)
        reply = rd.get("reply", "")

        async def get_tts(text):
            try:
                ar = await oc.audio.speech.create(model="tts-1", voice="nova", input=text)
                return base64.b64encode(ar.content).decode()
            except Exception:
                return None

        if ui:
            ms, ab = await asyncio.gather(score_mood(ui), get_tts(reply))
        else:
            ms, ab = None, await get_tts(reply)

        return {
            "reply": reply,
            "audio_base64": ab,
            "evidence": ctx,
            "mood_score": ms,
            "session_step": None,
            "suggested_choices": rd.get("choices", []),
            "automated_action": rd.get("automated_action"),
            "action_metadata": rd.get("action_metadata"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze_sentiment")
async def analyze_sentiment(p: SentimentRequest):
    try:
        r = await oc.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role":"system","content":'JSON: {"moodScore":0-10,"activity":"3-5자 명사","moodLabel":"3-5자","activityHour":0-23또는null}'},
                {"role":"user","content":p.text}
            ],
            response_format={"type":"json_object"}
        )
        d = json.loads(r.choices[0].message.content)
        return {
            "moodScore": int(d.get("moodScore", 5)),
            "activity": d.get("activity", "대화 세션"),
            "moodLabel": d.get("moodLabel", "보통"),
            "activityHour": d.get("activityHour"),
        }
    except Exception:
        return {"moodScore": 5, "activity": "대화 세션", "moodLabel": "보통"}

@router.get("/api/get_data")
def get_data():
    if USER_DB.exists():
        with open(USER_DB, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

@router.post("/api/save_data")
def save_data(p: UserData):
    try:
        with open(USER_DB, "w", encoding="utf-8") as f:
            json.dump(p.data, f, ensure_ascii=False, indent=2)
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/api/analyze_hrv_real")
def analyze_hrv(p: HRVRequest):
    if not p.samples or len(p.samples) < 100:
        raise HTTPException(status_code=400, detail="데이터 부족")
    try:
        from scipy.signal import butter, filtfilt
        from scipy.interpolate import CubicSpline
        import neurokit2 as nk

        t = np.array([s['t'] for s in p.samples])
        v = np.array([s['v'] for s in p.samples])
        dur = (t[-1] - t[0]) / 1000.0
        fs  = 70.0
        nt  = np.linspace(0, dur, int(dur * fs))
        rs  = CubicSpline((t - t[0]) / 1000.0, v)(nt)
        nyq = 0.5 * fs
        b, a = butter(4, [0.75/nyq, 2.5/nyq], btype='band')
        fl  = filtfilt(b, a, rs)
        pc  = nk.ppg_clean(fl, sampling_rate=fs)
        pks = nk.ppg_findpeaks(pc, sampling_rate=fs)['PPG_Peaks']
        hr_res = nk.hrv(pks, sampling_rate=fs)
        sdnn  = float(hr_res['HRV_SDNN'].values[0])
        rmssd = float(hr_res['HRV_RMSSD'].values[0])
        hr    = float(60.0 / (np.mean(np.diff(pks)) / fs)) if len(pks) > 1 else 70.0
        lfhf  = float(hr_res['HRV_LFHF'].values[0]) if 'HRV_LFHF' in hr_res else 1.2
        st    = (min(1.0, sdnn/50.0) + min(1.0, rmssd/40.0) + max(0.0, 1.0-abs(lfhf-1.2)/2.0)) / 3.0
        stress = float(np.clip((1.0 - st) * 100, 0, 100))
        lbl = "Normal"
        if hrv_model is not None:
            df = pd.DataFrame([{c: hr_res[c].values[0] for c in hr_res.columns}])
            for c in hrv_feats:
                if c not in df.columns:
                    df[c] = 0
            if hrv_feats:
                df = df[hrv_feats]
            lbl = ["Normal","Moderate","Severe"][int(hrv_model.predict(df)[0])]
        return {
            "sdnn": round(sdnn, 1), "rmssd": round(rmssd, 1),
            "hr": round(hr), "lfhf": round(lfhf, 2),
            "stress": round(stress), "risk": lbl,
        }
    except Exception as e:
        return {"sdnn":42.0,"rmssd":32.0,"hr":72,"lfhf":1.1,"stress":40,"risk":"Normal","error_msg":str(e)}
