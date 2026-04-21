
/* ══════════════════════════════════════════════════════════
   DATA
══════════════════════════════════════════════════════════ */
const EX = {
  1:  {n:"자세교정",    e:"자세",g:"gb",gn:"숨쉬기 연습",d:"올바른 발성 자세 만들기",       detail:"발뒤꿈치 바닥, 등 곧게, 어깨 편안히, 턱 살짝 당기기",  dur:"1~2분",t:"self",m:null},
  2:  {n:"구강운동",    e:"구강",g:"ga",gn:"발음 연습",       d:"입술·혀·턱 협응 훈련",         detail:"입술 오므리기 5회 → 혀 내밀기 5회 → 큰입 벌리기 5회", dur:"2~3분",t:"self",m:null},
  3:  {n:"지속발성",    e:"발성",g:"gb",gn:"숨쉬기 연습",  d:'"아~~~" 지속적으로 길게',       detail:'"아" 소리를 최대한 오래, 안정적으로 유지하세요',         dur:"3분",  t:"auto",m:"MPT · HNR · 음도안정성"},
  4:  {n:"음도올리기",  e:"높임",g:"gb",gn:"호흡/발성 연습",  d:"낮은 음 → 높은 음 올리기",     detail:"편안한 음도에서 천천히 위로 올려가기",                   dur:"2~3분",t:"auto",m:"F0 변화범위 (Hz)"},
  5:  {n:"음도내리기",  e:"낮춤",g:"gb",gn:"호흡/발성 연습",  d:"높은 음 → 낮은 음 내리기",     detail:"높은 음에서 천천히 아래로 내려가기",                      dur:"2~3분",t:"auto",m:"F0 변화범위 (Hz)"},
  6:  {n:"피치조절",    e:"음도",g:"gb",gn:"호흡/발성 연습",  d:"목표 음도 정확히 맞추기",      detail:"화면의 목표 음도에 맞춰 발성하세요",                      dur:"3분",  t:"auto",m:"목표 F0 오차 (Hz)"},
  7:  {n:"볼륨업",      e:"음량",g:"gb",gn:"숨쉬기 연습",  d:"최대한 크게 발성하기",         detail:'"아!" 소리를 힘차고 크게 — LSVT LOUD 방식',             dur:"2~3분",t:"auto",m:"음량 (dB)"},
  8:  {n:"성문폐쇄",    e:"성문",g:"gb",gn:"숨쉬기 연습",  d:"성대 닫힘 강화 훈련",         detail:'"이!" 시작 때 성대를 확실히 닫는 느낌으로',              dur:"2분",  t:"auto",m:"Voice Onset Time · HNR"},
  9:  {n:"하품-한숨",   e:"호흡",g:"gb",gn:"숨쉬기 연습",d:"크게 하품 후 한숨 내쉬기",    detail:"하품 → 깊이 들이쉬고 → '하~' 한숨 3회",                 dur:"2~3분",t:"auto",m:"호기 지속시간 (초)"},
  10: {n:"대조훈련",    e:"대조",g:"ga",gn:"발음 연습",       d:"최소대립쌍 구별해 말하기",     detail:'"발/팔", "달/탈" — 비슷한 단어 정확히 구별',             dur:"3~4분",t:"auto",m:"STT 명료도 정확도"},
  11: {n:"대립강세",    e:"강세",g:"gp",gn:"말하기 연습",       d:"강세 위치를 바꾸어 말하기",    detail:'"나는 사과를 먹었다" — 3가지 강세 패턴',                 dur:"3분",  t:"auto",m:"강세 패턴 정확도"},
  12: {n:"호흡운동",    e:"숨",g:"gb",gn:"숨쉬기 연습",  d:"발성을 위한 호흡 조절",       detail:"코 3초 들이쉬기 → 입으로 5초 내쉬기 × 5회",             dur:"2~3분",t:"auto",m:"호기 지속시간 (초)"},
  13: {n:"탭핑",        e:"탭핑",g:"gp",gn:"말하기 연습",       d:"리듬에 맞춰 손 두드리며 말하기",detail:"테이블 두드리며 음절 박자에 맞춰 발화",                  dur:"3분",  t:"auto",m:"발화 타이밍 정확도"},
  14: {n:"천천히읽기",  e:"읽기",g:"gp",gn:"말하기 연습",       d:"의도적으로 속도 줄여 읽기",    detail:"평소보다 2배 천천히, 또렷하게 문장 읽기",                dur:"3~5분",t:"auto",m:"말속도 (단어/분)"},
  15: {n:"크게읽기",    e:"크게",g:"gp",gn:"말하기 연습",       d:"최대 음량으로 문장 읽기",      detail:'"LOUD!" 느낌으로 문장 읽기 (LSVT LOUD)',                dur:"3~5분",t:"auto",m:"dB · STT 명료도"},
  16: {n:"DDK 직접훈련",e:"DDK",g:"ga",gn:"발음 연습",       d:"/퍼터커/ 빠르게 반복",        detail:'"/퍼터커/" 최대한 빠르고 정확하게 5회 반복',             dur:"3분",  t:"auto",m:"음절 속도 (Hz) · STT"},
};

/* ══════════════════════════════════════════════════════════
   LEVEL SYSTEM — 난이도 위계
   80% 규칙: 3회 연속 목표 달성 → 자동 레벨업
══════════════════════════════════════════════════════════ */
const LEVELS = {
  // #2 구강운동 (self-check)
  2: [
    {lv:1, goal:'각 동작 3회',         desc:'천천히 정확하게'},
    {lv:2, goal:'각 동작 5회',         desc:'횟수 증가'},
    {lv:3, goal:'각 동작 5회 + 빠르게', desc:'속도까지 도전'},
  ],
  // #3 지속발성
  3: [
    {lv:1, goal:'3초 이상',  goalTxt:'목표: 3초 이상',  max:3,   desc:'기초 발성 유지'},
    {lv:2, goal:'5초 이상',  goalTxt:'목표: 5초 이상',  max:5,   desc:'안정적 발성'},
    {lv:3, goal:'8초 이상',  goalTxt:'목표: 8초 이상',  max:8,   desc:'호흡 연계 강화'},
    {lv:4, goal:'12초 이상', goalTxt:'목표: 12초 이상', max:12,  desc:'장시간 유지'},
    {lv:5, goal:'15초 이상', goalTxt:'목표: 15초 이상', max:15,  desc:'정상 범위 도달'},
  ],
  // #4 글라이딩↑
  4: [
    {lv:1, goal:'40Hz 이상', goalTxt:'목표: 40Hz 이상', max:40,  desc:'작은 변화폭'},
    {lv:2, goal:'60Hz 이상', goalTxt:'목표: 60Hz 이상', max:60,  desc:'중간 변화폭'},
    {lv:3, goal:'80Hz 이상', goalTxt:'목표: 80Hz 이상', max:80,  desc:'큰 변화폭'},
    {lv:4, goal:'100Hz+',    goalTxt:'목표: 100Hz 이상',max:100, desc:'1옥타브 도달'},
  ],
  // #5 글라이딩↓
  5: [
    {lv:1, goal:'40Hz 이상', goalTxt:'목표: 40Hz 이상', max:40,  desc:'작은 변화폭'},
    {lv:2, goal:'60Hz 이상', goalTxt:'목표: 60Hz 이상', max:60,  desc:'중간 변화폭'},
    {lv:3, goal:'80Hz 이상', goalTxt:'목표: 80Hz 이상', max:80,  desc:'큰 변화폭'},
    {lv:4, goal:'100Hz+',    goalTxt:'목표: 100Hz 이상',max:100, desc:'1옥타브 도달'},
  ],
  // #6 피치조절 (오차 — 낮을수록 좋음)
  6: [
    {lv:1, goal:'오차 ±30Hz', goalTxt:'목표: 오차 ±30Hz 이내', max:30, desc:'넓은 허용 범위'},
    {lv:2, goal:'오차 ±20Hz', goalTxt:'목표: 오차 ±20Hz 이내', max:20, desc:'중간 정밀도'},
    {lv:3, goal:'오차 ±15Hz', goalTxt:'목표: 오차 ±15Hz 이내', max:15, desc:'높은 정밀도'},
    {lv:4, goal:'오차 ±10Hz', goalTxt:'목표: 오차 ±10Hz 이내', max:10, desc:'정밀 조절'},
  ],
  // #7 볼륨업
  7: [
    {lv:1, goal:'60dB 이상', goalTxt:'목표: 60dB 이상', max:60, desc:'기본 음량'},
    {lv:2, goal:'65dB 이상', goalTxt:'목표: 65dB 이상', max:65, desc:'약간 크게'},
    {lv:3, goal:'70dB 이상', goalTxt:'목표: 70dB 이상', max:70, desc:'충분히 크게'},
    {lv:4, goal:'75dB 이상', goalTxt:'목표: 75dB 이상', max:75, desc:'문장에서도 크게'},
  ],
  // #8 성문폐쇄
  8: [
    {lv:1, goal:'선명도 60점', goalTxt:'목표: 60점 이상', max:60, desc:'"이!" 1회 강하게'},
    {lv:2, goal:'선명도 70점', goalTxt:'목표: 70점 이상', max:70, desc:'"이!" 5회 연속'},
    {lv:3, goal:'선명도 80점', goalTxt:'목표: 80점 이상', max:80, desc:'단어에서도 유지'},
    {lv:4, goal:'선명도 85점', goalTxt:'목표: 85점 이상', max:85, desc:'문장 첫소리 강화'},
  ],
  // #9 하품-한숨
  9: [
    {lv:1, goal:'호기 3초',       goalTxt:'목표: 3초 이상', max:3,  desc:'이완 시작'},
    {lv:2, goal:'호기 5초',       goalTxt:'목표: 5초 이상', max:5,  desc:'후두 이완 유지'},
    {lv:3, goal:'호기 5초 + 발성', goalTxt:'목표: 5초 + 발성', max:8, desc:'"하~" 자연스럽게'},
  ],
  // #10 대조훈련
  10: [
    {lv:1, goal:'STT 60% · 2쌍',   goalTxt:'목표: 정확도 60% 이상', max:60, desc:'초성 대립 2쌍'},
    {lv:2, goal:'STT 70% · 4쌍',   goalTxt:'목표: 정확도 70% 이상', max:70, desc:'초성 대립 4쌍'},
    {lv:3, goal:'STT 75% + 종성',  goalTxt:'목표: 정확도 75% 이상', max:75, desc:'종성 대립 포함'},
    {lv:4, goal:'STT 80% · 문장',  goalTxt:'목표: 정확도 80% 이상', max:80, desc:'문장 속 대립어'},
  ],
  // #11 대립강세
  11: [
    {lv:1, goal:'정확도 60% · 3어절', goalTxt:'목표: 정확도 60% 이상', max:60, desc:'짧은 문장 2패턴'},
    {lv:2, goal:'정확도 70% · 5어절', goalTxt:'목표: 정확도 70% 이상', max:70, desc:'보통 문장 3패턴'},
    {lv:3, goal:'정확도 75% · 7어절', goalTxt:'목표: 정확도 75% 이상', max:75, desc:'긴 문장 3패턴'},
    {lv:4, goal:'정확도 80% · 자유',  goalTxt:'목표: 정확도 80% 이상', max:80, desc:'자유 문장'},
  ],
  // #12 호흡운동
  12: [
    {lv:1, goal:'호기 3초',        goalTxt:'목표: 호기 3초 이상', max:3,  desc:'코2초 → 입3초'},
    {lv:2, goal:'호기 5초',        goalTxt:'목표: 호기 5초 이상', max:5,  desc:'코3초 → 입5초'},
    {lv:3, goal:'호기 8초',        goalTxt:'목표: 호기 8초 이상', max:8,  desc:'코3초 → 입8초'},
    {lv:4, goal:'호기 10초 + /s/', goalTxt:'목표: 호기 10초 이상',max:10, desc:'/s/ 발성하며 호기'},
  ],
  // #13 탭핑
  13: [
    {lv:1, goal:'타이밍 60% · 2음절', goalTxt:'목표: 타이밍 60% 이상', max:60, desc:'2음절 단어'},
    {lv:2, goal:'타이밍 70% · 3음절', goalTxt:'목표: 타이밍 70% 이상', max:70, desc:'3음절 단어'},
    {lv:3, goal:'타이밍 75% · 문장',  goalTxt:'목표: 타이밍 75% 이상', max:75, desc:'짧은 문장'},
    {lv:4, goal:'타이밍 80% · 긴문장', goalTxt:'목표: 타이밍 80% 이상', max:80, desc:'긴 문장'},
  ],
  // #14 천천히읽기 (말속도 — 낮을수록 좋음)
  14: [
    {lv:1, goal:'120어/분 이하', goalTxt:'목표: 120어/분 이하', max:120, desc:'짧은 문장 5어절'},
    {lv:2, goal:'110어/분 이하', goalTxt:'목표: 110어/분 이하', max:110, desc:'긴 문장 8어절'},
    {lv:3, goal:'100어/분 이하', goalTxt:'목표: 100어/분 이하', max:100, desc:'문단 3문장'},
    {lv:4, goal:'90어/분 이하',  goalTxt:'목표: 90어/분 이하',  max:90,  desc:'문단 5문장'},
  ],
  // #15 크게읽기
  15: [
    {lv:1, goal:'65dB · 짧은 문장',   goalTxt:'목표: 65dB 이상', max:65, desc:'짧은 문장'},
    {lv:2, goal:'68dB · 긴 문장',     goalTxt:'목표: 68dB 이상', max:68, desc:'긴 문장'},
    {lv:3, goal:'70dB + STT 70%',     goalTxt:'목표: 70dB + 명료도 70%', max:70, desc:'문단'},
    {lv:4, goal:'70dB + STT 80%',     goalTxt:'목표: 70dB + 명료도 80%', max:70, desc:'문단 + 명료도'},
  ],
  // #16 DDK
  16: [
    {lv:1, goal:'/퍼/ 3.0Hz',    goalTxt:'목표: 3.0Hz 이상', max:3.0, desc:'/퍼/ 단음절'},
    {lv:2, goal:'/퍼터/ 3.0Hz',  goalTxt:'목표: 3.0Hz 이상', max:3.0, desc:'/퍼터/ 이음절'},
    {lv:3, goal:'/퍼터커/ 3.5Hz', goalTxt:'목표: 3.5Hz 이상', max:3.5, desc:'/퍼터커/ 삼음절'},
    {lv:4, goal:'/퍼터커/ 4.5Hz+',goalTxt:'목표: 4.5Hz 이상', max:4.5, desc:'빠르고 정확하게'},
  ],
};

// 환자별 현재 레벨 (프로토타입: 기본값 1)
const playerLvl = {};
Object.keys(LEVELS).forEach(k => playerLvl[k] = 1);

function getLvl(id) {
  if (!LEVELS[id]) return null;
  const lv = playerLvl[id] || 1;
  return LEVELS[id].find(l => l.lv === lv) || LEVELS[id][0];
}
function getLvlMax(id) {
  return LEVELS[id] ? LEVELS[id].length : 0;
}

/* ── 레벨 자동 승급/강등 시스템 ───────────────── */
const lvStreak = {};          // {id: +N=연속성공, -N=연속실패}
Object.keys(LEVELS).forEach(k => lvStreak[k] = 0);
let sessionLvChanges = [];    // [{id, exName, from, to, dir}]

function checkLevelChange(id) {
  if (!LEVELS[id]) return;
  // 프로토타입: 70% 확률로 성공 시뮬레이션
  const success = Math.random() < 0.7;

  if (success) {
    lvStreak[id] = lvStreak[id] >= 0 ? lvStreak[id] + 1 : 1; // 실패 연속이었으면 리셋
  } else {
    lvStreak[id] = lvStreak[id] <= 0 ? lvStreak[id] - 1 : -1;
  }

  const curLv = playerLvl[id];
  const maxLv = LEVELS[id].length;

  // 3회 연속 성공 → 레벨업
  if (lvStreak[id] >= 3 && curLv < maxLv) {
    playerLvl[id] = curLv + 1;
    lvStreak[id] = 0;
    sessionLvChanges.push({ id, exName: EX[id].n, from: curLv, to: curLv + 1, dir: 'up' });
    showLvToast(id, 'up');
  }
  // 3회 연속 실패 → 레벨다운
  if (lvStreak[id] <= -3 && curLv > 1) {
    playerLvl[id] = curLv - 1;
    lvStreak[id] = 0;
    sessionLvChanges.push({ id, exName: EX[id].n, from: curLv, to: curLv - 1, dir: 'down' });
    showLvToast(id, 'down');
  }
}

function showLvToast(id, dir) {
  const ex = EX[id];
  const newLv = playerLvl[id];
  const newGoal = getLvl(id).goal;
  const toast = document.createElement('div');
  toast.className = 'lv-up-toast';
  if (dir === 'up') {
    toast.textContent = ex.n + ' Lv.' + newLv + ' 레벨업!';
    toast.style.background = 'linear-gradient(135deg, #F59E0B, #F97316)';
  } else {
    toast.textContent = ex.n + ' Lv.' + newLv + ' — 천천히 다시';
    toast.style.background = 'linear-gradient(135deg, #6366F1, #8B5CF6)';
  }
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 2500);
}
function lvStars(cur, max) {
  let s = '';
  for (let i = 0; i < max; i++) s += i < cur ? '★' : '☆';
  return s;
}

const RPPG = {
  high: { hrv:18, bpm:88, stress:"높음", lvl:"오늘은 좀 힘든 날이네요", cls:"rr-high",
    desc:"가볍게 해봐요" },
  mid:  { hrv:38, bpm:74, stress:"보통", lvl:"오늘은 괜찮은 편이에요", cls:"rr-mid",
    desc:"적당히 해봐요" },
  low:  { hrv:58, bpm:65, stress:"낮음",  lvl:"오늘 컨디션 좋아요!", cls:"rr-low",
    desc:"힘내서 해봐요" },
};

const COMBOS = {
  "high-severe":   {depC:"#DC2626",stratBg:"#FEF2F2",stratText:"#DC2626",
    tag:"rPPG 높음 + 중도", strat:"최소 과제 + 기초 자극 유지",
    msg:"오늘은 이것만으로도 충분해요", dur:"5~7분", ids:[1,12,2],
    results:[{e:"자세",n:"자세교정",met:"자세 확인 완료"},
             {e:"숨",n:"호흡운동",met:"복식호흡 3회 완료"},
             {e:"구강",n:"구강운동",met:"구강운동 3세트 완료"}],
    resMsg:"오늘 최소 과제를 완료했어요.<br><strong>오늘도 했다는 사실</strong>이 치료예요."},

  "high-moderate": {depC:"#DC2626",stratBg:"#FEF2F2",stratText:"#DC2626",
    tag:"rPPG 높음 + 중등도", strat:"기초 발성 + 성공 경험 중심",
    msg:"천천히, 한 번만 해볼까요?", dur:"7~10분", ids:[1,2,3,12],
    results:[{e:"자세",n:"자세교정",met:"자가확인 ✓",   ch:"완료",   up:false},
             {e:"구강",n:"구강운동",met:"자가확인 ✓",   ch:"완료",   up:false},
             {e:"발성",n:"지속발성",met:"MPT 3.2초",    ch:"↑+0.5초",up:true},
             {e:"숨",n:"호흡운동",met:"복식호흡 3회 완료"}],
    resMsg:"지속발성이 0.5초 더 길어졌어요!<br><strong>정말 잘 하고 있어요</strong>"},

  "high-mild":     {depC:"#DC2626",stratBg:"#FEF2F2",stratText:"#DC2626",
    tag:"rPPG 높음 + 경도", strat:"가벼운 발성 + 성공 보장",
    msg:"가볍게 시작해봐요, 충분해요", dur:"8~10분", ids:[2,3,9,7],
    results:[{e:"구강",n:"구강운동",met:"자가확인 ✓",  ch:"완료",   up:false},
             {e:"발성",n:"지속발성",met:"MPT 4.1초",   ch:"↑+0.8초",up:true},
             {e:"호흡",n:"하품-한숨",met:"호기 3.8초", ch:"↑+0.3초",up:true},
             {e:"음량",n:"볼륨업",  met:"68dB",        ch:"↑+3dB",  up:true}],
    resMsg:"발성이 많이 좋아졌어요!<br><strong>지속발성 +0.8초</strong> 달성"},

  "mid-severe":    {depC:"#D97706",stratBg:"#FFFBEB",stratText:"#D97706",
    tag:"rPPG 보통 + 중도", strat:"기초 + 발성 훈련",
    msg:"기초부터 차근차근 쌓아가요", dur:"10~13분", ids:[1,12,2,3,8],
    results:[{e:"자세",n:"자세교정",met:"자가확인 ✓",  ch:"완료",   up:false},

             {e:"숨",n:"호흡운동",met:"복식호흡 3회 완료"},
             {e:"구강",n:"구강운동",met:"자가확인 ✓",  ch:"완료",   up:false},
             {e:"발성",n:"지속발성",met:"MPT 3.8초",   ch:"↑+0.4초",up:true},
             {e:"성문",n:"성문폐쇄",met:"VoiceOnset 양호",ch:"유지", up:false}],
    resMsg:"오늘 5가지 운동을 완료했어요!<br><strong>호흡 + 발성</strong> 모두 좋아지고 있어요"},

  "mid-moderate":  {depC:"#D97706",stratBg:"#FFFBEB",stratText:"#D97706",
    tag:"rPPG 보통 + 중등도", strat:"균형형 훈련 — 발성 + 조음",
    msg:"오늘은 균형 있게 훈련해요!", dur:"12~15분", ids:[3,4,5,2,16],
    results:[{e:"발성",n:"지속발성",  met:"MPT 4.2초",     ch:"↑+0.4초",up:true},
             {e:"높임",n:"음도올리기",met:"F0 범위 82Hz",  ch:"↑+8Hz",  up:true},
             {e:"낮춤",n:"음도내리기",met:"F0 범위 75Hz",  ch:"유지",   up:false},
             {e:"구강",n:"구강운동",  met:"자가확인 ✓",    ch:"완료",   up:false},
             {e:"DDK",n:"DDK 직접훈련",met:"4.1Hz·78%",   ch:"↑+6%",   up:true}],
    resMsg:"DDK 정확도가 6% 올랐어요!<br><strong>조음이 점점 또렷해지고 있어요</strong>"},

  "mid-mild":      {depC:"#D97706",stratBg:"#FFFBEB",stratText:"#D97706",
    tag:"rPPG 보통 + 경도", strat:"발성 + 조음 + 운율 골고루",
    msg:"조금 더 도전해봐요, 잘 하고 있어요!", dur:"13~15분", ids:[3,6,7,10,14,11],
    results:[{e:"발성",n:"지속발성", met:"MPT 5.0초",       ch:"↑+0.6초",up:true},
             {e:"음도",n:"피치조절", met:"오차 ±12Hz",      ch:"↑개선",  up:true},
             {e:"음량",n:"볼륨업",   met:"72dB",            ch:"↑+4dB",  up:true},
             {e:"대조",n:"대조훈련", met:"STT 82%",         ch:"↑+5%",   up:true},
             {e:"읽기",n:"천천히읽기",met:"92단어/분",       ch:"↓-8✓",   up:true},
             {e:"강세",n:"대립강세", met:"강세 75%",        ch:"↑+8%",   up:true}],
    resMsg:"6가지 모두 완료! 발성·조음·운율을<br><strong>골고루 훈련한 완벽한 세션</strong>이에요"},

  "low-severe":    {depC:"#16A34A",stratBg:"#F0FDF4",stratText:"#16A34A",
    tag:"rPPG 낮음 + 중도", strat:"강도 있는 기초 훈련",
    msg:"오늘 컨디션 최고! 열심히 해봐요", dur:"15~18분", ids:[1,12,2,3,16,8],
    results:[{e:"자세",n:"자세교정",  met:"자가확인 ✓",    ch:"완료",   up:false},
             {e:"숨",n:"호흡운동",  met:"복식호흡 5회 완료"},
             {e:"구강",n:"구강운동",  met:"자가확인 ✓",    ch:"완료",   up:false},
             {e:"발성",n:"지속발성",  met:"MPT 4.5초",     ch:"↑+0.5초",up:true},
             {e:"DDK",n:"DDK 직접훈련",met:"3.8Hz·72%",   ch:"↑+8%",   up:true},
             {e:"성문",n:"성문폐쇄",  met:"VoiceOnset 양호",ch:"↑개선",  up:true}],
    resMsg:"6가지 완료! 컨디션이 좋은 날<br><strong>최대한 활용한 훌륭한 세션</strong>이에요"},

  "low-moderate":  {depC:"#16A34A",stratBg:"#F0FDF4",stratText:"#16A34A",
    tag:"rPPG 낮음 + 중등도", strat:"전 영역 도전 훈련",
    msg:"오늘 최고예요! 전부 도전해봐요", dur:"18~20분", ids:[3,4,5,7,16,10,11],
    results:[{e:"발성",n:"지속발성",  met:"MPT 5.5초",      ch:"↑+0.9초",up:true},
             {e:"높임",n:"음도올리기",met:"F0 범위 95Hz",   ch:"↑+12Hz", up:true},
             {e:"낮춤",n:"음도내리기",met:"F0 범위 88Hz",   ch:"↑+10Hz", up:true},
             {e:"음량",n:"볼륨업",    met:"76dB",           ch:"↑+6dB",  up:true},
             {e:"DDK",n:"DDK 직접훈련",met:"4.8Hz·85%",    ch:"↑+10%",  up:true},
             {e:"대조",n:"대조훈련",  met:"STT 88%",        ch:"↑+7%",   up:true},
             {e:"강세",n:"대립강세",  met:"강세 82%",       ch:"↑+12%",  up:true}],
    resMsg:"7가지 운동 전부 완료!<br><strong>이번 세션 최고 기록</strong>이에요"},

  "low-mild":      {depC:"#16A34A",stratBg:"#F0FDF4",stratText:"#16A34A",
    tag:"rPPG 낮음 + 경도", strat:"최대 강도 재활",
    msg:"오늘은 최대 강도로! 당신 최고예요", dur:"20~25분", ids:[3,4,5,6,7,16,10,14],
    results:[{e:"발성",n:"지속발성",  met:"MPT 6.2초",      ch:"↑+1.1초",up:true},
             {e:"높임",n:"음도올리기",met:"F0 범위 108Hz",  ch:"↑+15Hz", up:true},
             {e:"낮춤",n:"음도내리기",met:"F0 범위 100Hz",  ch:"↑+12Hz", up:true},
             {e:"음도",n:"피치조절",  met:"오차 ±8Hz",      ch:"↑최고",  up:true},
             {e:"음량",n:"볼륨업",    met:"80dB",           ch:"↑+8dB",  up:true},
             {e:"DDK",n:"DDK 직접훈련",met:"5.5Hz·91%",    ch:"↑+12%",  up:true},
             {e:"대조",n:"대조훈련",  met:"STT 92%",        ch:"↑+9%",   up:true},
             {e:"읽기",n:"천천히읽기",met:"85단어/분",       ch:"↓-14✓",  up:true}],
    resMsg:"8가지 모두 완료!<br><strong>모든 지표 개인 최고 기록</strong>이에요"},
};

const FOCUS_COMBOS = {
  /* ── 중도: 전체 16가지 완전 프로토콜 (순서대로) ─────────── */
  "normal-severe": {
    stratBg:"#F0FDF4", stratText:"#15803D",
    tag:"집중 재활 · 중도 — 완전 프로토콜",
    strat:"16가지 전체 순서 수행 — 완전 재활",
    msg:"오늘 컨디션 최고! 전 과정 도전해요", dur:"40~50분",
    ids:[1, 12, 9, 2, 3, 8, 7, 4, 5, 6, 16, 10, 13, 11, 14, 15],
    results:[
      {e:"자세",n:"자세교정",    met:"자가확인 ✓",       ch:"완료",    up:false},
      {e:"숨",n:"호흡운동",    met:"복식호흡 5회 완료"},
      {e:"호흡",n:"하품-한숨",  met:"호기 5.1초",       ch:"↑+0.5초", up:true},
      {e:"구강",n:"구강운동",    met:"자가확인 ✓",       ch:"완료",    up:false},
      {e:"발성",n:"지속발성",    met:"MPT 5.2초",        ch:"↑+0.8초", up:true},
      {e:"성문",n:"성문폐쇄",    met:"VoiceOnset 양호",  ch:"↑+개선",  up:true},
      {e:"음량",n:"볼륨업",      met:"72dB",             ch:"↑+5dB",   up:true},
      {e:"높임",n:"음도올리기",  met:"F0 범위 88Hz",     ch:"↑+10Hz",  up:true},
      {e:"낮춤",n:"음도내리기",  met:"F0 범위 82Hz",     ch:"↑+8Hz",   up:true},
      {e:"음도",n:"피치조절",    met:"오차 ±14Hz",       ch:"↑개선",   up:true},
      {e:"DDK",n:"DDK 직접훈련",met:"3.8Hz · 74%",      ch:"↑+10%",   up:true},
      {e:"대조",n:"대조훈련",    met:"STT 76%",          ch:"↑+8%",    up:true},
      {e:"탭핑",n:"탭핑",        met:"타이밍 71%",       ch:"↑+7%",    up:true},
      {e:"강세",n:"대립강세",    met:"강세 68%",         ch:"↑+9%",    up:true},
      {e:"읽기",n:"천천히읽기",  met:"102단어/분",        ch:"↓-12✓",   up:true},
      {e:"크게",n:"크게읽기",    met:"71dB · STT 74%",   ch:"↑+8%",    up:true}
    ],
    resMsg:"16가지 전체 프로토콜 완료!<br><strong>이보다 더 완전한 세션은 없어요</strong>"
  },

  /* ── 중등도: 발성+조음+운율 균형 (12가지) ───────────────── */
  "normal-moderate": {
    stratBg:"#F0FDF4", stratText:"#15803D",
    tag:"집중 재활 · 중등도",
    strat:"발성 · 조음 · 운율 전 영역 균형",
    msg:"균형 있게 전부 도전해요!", dur:"30~35분",
    ids:[1, 12, 2, 3, 7, 8, 4, 5, 16, 10, 14, 15],
    results:[
      {e:"자세",n:"자세교정",    met:"자가확인 ✓",       ch:"완료",    up:false},
      {e:"숨",n:"호흡운동",    met:"복식호흡 5회 완료"},
      {e:"구강",n:"구강운동",    met:"자가확인 ✓",       ch:"완료",    up:false},
      {e:"발성",n:"지속발성",    met:"MPT 6.4초",        ch:"↑+1.0초", up:true},
      {e:"음량",n:"볼륨업",      met:"76dB",             ch:"↑+6dB",   up:true},
      {e:"성문",n:"성문폐쇄",    met:"VoiceOnset 양호",  ch:"↑개선",   up:true},
      {e:"높임",n:"음도올리기",  met:"F0 범위 98Hz",     ch:"↑+12Hz",  up:true},
      {e:"낮춤",n:"음도내리기",  met:"F0 범위 92Hz",     ch:"↑+9Hz",   up:true},
      {e:"DDK",n:"DDK 직접훈련",met:"4.6Hz · 84%",      ch:"↑+12%",   up:true},
      {e:"대조",n:"대조훈련",    met:"STT 86%",          ch:"↑+10%",   up:true},
      {e:"읽기",n:"천천히읽기",  met:"90단어/분",         ch:"↓-14✓",   up:true},
      {e:"크게",n:"크게읽기",    met:"76dB · STT 82%",   ch:"↑+11%",   up:true}
    ],
    resMsg:"12가지 전 영역 완료!<br><strong>발성·조음·운율 모두 좋아지고 있어요</strong>"
  },

  /* ── 경도: 심화·유지 중심 (9가지) ──────────────────────── */
  "normal-mild": {
    stratBg:"#F0FDF4", stratText:"#15803D",
    tag:"집중 재활 · 경도 — 심화 유지",
    strat:"고급 조음 · 운율 · 속도 심화 훈련",
    msg:"이미 잘 하고 있어요, 더 정교하게!", dur:"25~30분",
    ids:[3, 6, 7, 16, 10, 11, 13, 14, 15],
    results:[
      {e:"발성",n:"지속발성",    met:"MPT 8.2초",        ch:"↑+1.4초", up:true},
      {e:"음도",n:"피치조절",    met:"오차 ±6Hz",        ch:"↑최고",   up:true},
      {e:"음량",n:"볼륨업",      met:"84dB",             ch:"↑+10dB",  up:true},
      {e:"DDK",n:"DDK 직접훈련",met:"5.9Hz · 94%",      ch:"↑+15%",   up:true},
      {e:"대조",n:"대조훈련",    met:"STT 95%",          ch:"↑+12%",   up:true},
      {e:"강세",n:"대립강세",    met:"강세 91%",         ch:"↑+16%",   up:true},
      {e:"탭핑",n:"탭핑",        met:"타이밍 88%",       ch:"↑+13%",   up:true},
      {e:"읽기",n:"천천히읽기",  met:"80단어/분",         ch:"↓-18✓",   up:true},
      {e:"크게",n:"크게읽기",    met:"83dB · STT 94%",   ch:"↑+13%",   up:true}
    ],
    resMsg:"9가지 심화 훈련 완료!<br><strong>정확도·운율 모두 개인 최고 기록</strong>"
  }
};

/* ══════════════════════════════════════════════════════════
   STATE
══════════════════════════════════════════════════════════ */
let dep = 'high', sev = 'severe';
let mode = 'integ';
let rppgIv = null, rppgSec = 0;
let bpmIv  = null;

function key() {
  if (mode === 'focus') return 'normal-' + sev;
  return dep + '-' + sev;
}
function combo() {
  if (mode === 'focus') return FOCUS_COMBOS[key()];
  return COMBOS[key()];
}

/* ══════════════════════════════════════════════════════════
   NAVIGATION
══════════════════════════════════════════════════════════ */
function goto(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.add('off'));
  document.getElementById('screen-' + id).classList.remove('off');
  stopRecTimer();
  if (id === 'tasks')     renderTasks();
  if (id === 'all-ex')   renderAllEx();
  if (id === 'result')   renderResult();
  if (id === 'rppg')     resetRppg();
  if (id === 'severity') resetSeverity();
}

/* ══════════════════════════════════════════════════════════
   중증도 진단 시스템
══════════════════════════════════════════════════════════ */
const SEV_VOWELS = [
  {word:'아', instruction:'"아~" 소리를 길게 내어 주세요'},
  {word:'이', instruction:'"이~" 소리를 길게 내어 주세요'},
  {word:'우', instruction:'"우~" 소리를 길게 내어 주세요'}
];
const SEV_DDK = [
  {word:'퍼터커', instruction:'"퍼·터·커"를 빠르게 반복해서 말해 주세요'}
];
const SEV_WORDS_RAW = [
  '나무','목도리','꽃','김밥','바지','사탕','풍선','국자',
  '토끼','코끼리','해바라기','연필','호랑이','라면','냉장고',
  '단추','곰','가방','똥','책상','자동차','빨간색','짹짹',
  '그네','기차','접시','로봇','싸움','짜장면','포크'
];
const SEV_WORDS = SEV_WORDS_RAW.map(w => ({word:w, instruction:'"'+w+'" 단어를 소리 내어 읽어 주세요'}));

const SEV_TASKS = [
  {name:'모음 발성', list: SEV_VOWELS, badge:['#FFF0D6','#E07B00']},
  {name:'퍼터커 발음', list: SEV_DDK, badge:['#EEF2FF','var(--primary)']},
  {name:'단어 읽기', list: SEV_WORDS, badge:['#E8F5E9','#2E7D32']}
];

let sevState = {taskIdx:0, step:0, recording:false, timer:null, waveTimer:null, sec:0, done:[false,false,false]};

// --- [START] MediaRecorder 연동 State ---
let mediaRecorder = null;
let chunkArrays = [];
let audioBlobs = {
  vowels: [],
  putterker: null,
  words: [],
  currentStep: 0
};
// --- [END] ---

function resetSeverity() {
  sevState = {taskIdx:0, step:0, recording:false, timer:null, waveTimer:null, sec:0, done:[false,false,false]};
  sevCalibrated = false;
  audioBlobs = { vowels: [], putterker: null, words: [], currentStep: 0 };
  document.getElementById('sev-list-view').style.display = '';
  document.getElementById('sev-rec-view').style.display = 'none';
  document.getElementById('sev-complete-view').style.display = 'none';
  renderSevList();
}

function renderSevList() {
  const doneCount = sevState.done.filter(Boolean).length;
  const nextIdx = sevState.done.indexOf(false);
  const pct = Math.round((doneCount / 3) * 100);

  // 전체 진행률
  document.getElementById('sev-overall-label').textContent = doneCount >= 3 ? '모든 과제 완료!' : '과제 ' + (doneCount + 1) + ' / 3';
  document.getElementById('sev-overall-pct').textContent = pct + '%';
  document.getElementById('sev-overall-bar').style.width = pct + '%';

  // 시작 버튼 텍스트
  const startBtn = document.getElementById('sev-start-btn');
  if (doneCount === 0) startBtn.textContent = '시작하기';
  else if (doneCount < 3) startBtn.textContent = '이어하기';
  else startBtn.textContent = '결과 보기';

  // 카드 상태
  SEV_TASKS.forEach((t, i) => {
    const card = document.getElementById('sev-card-'+i);
    const badge = document.getElementById('sev-badge-'+i);
    card.className = 'sev-task-card';
    card.style.opacity = '';
    if (sevState.done[i]) {
      card.classList.add('done');
      badge.style.display = 'inline-block';
      badge.style.background = '#E8F5E9'; badge.style.color = '#16A34A';
      badge.textContent = '완료';
    } else if (i === nextIdx) {
      card.classList.add('active');
      badge.style.display = 'inline-block';
      badge.style.background = '#FFF0D6'; badge.style.color = '#E07B00';
      badge.textContent = '진행중';
    } else {
      card.style.opacity = '.55';
      badge.style.display = 'none';
    }
  });
}

function startSevNext() {
  const nextIdx = sevState.done.indexOf(false);
  if (nextIdx < 0) {
    showSevComplete();
  } else {
    startSevTask(nextIdx);
  }
}

let sevCalibrated = false;

async function startSevTask(idx) {
  if (sevState.done[idx]) return;

  if (!mediaRecorder) {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      // 지원되는 MIME 타입 선택 (기본적으로 webm, 모바일 사파리는 mp4 등 일수도 있으나 데스크탑/최신크롬 기준 webm 적용)
      const mime = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4';
      mediaRecorder = new MediaRecorder(stream, { mimeType: mime });
      
      mediaRecorder.ondataavailable = e => {
        if (e.data.size > 0) chunkArrays.push(e.data);
      };
      
      mediaRecorder.onstop = () => {
        const blob = new Blob(chunkArrays, { type: mediaRecorder.mimeType });
        chunkArrays = [];
        
        if (sevState.taskIdx === 0) {
          audioBlobs.vowels[audioBlobs.currentStep] = blob;
        } else if (sevState.taskIdx === 1) {
          audioBlobs.putterker = blob;
        } else if (sevState.taskIdx === 2) {
          if (tpState.currentWord) {
             audioBlobs.words.push({word: tpState.currentWord, blob: blob});
          }
        }
      };
    } catch(err) {
      console.error(err);
      alert('음성 측정을 위해 마이크 권한을 허용해주세요.');
      return;
    }
  }

  sevState.taskIdx = idx;
  sevState.step = 0;
  document.getElementById('sev-list-view').style.display = 'none';
  document.getElementById('sev-rec-view').style.display = 'flex';

  if (!sevCalibrated) {
    // 첫 과제 시작 전 환경 세팅
    document.getElementById('sev-calibration').style.display = 'flex';
    document.getElementById('sev-rec-main').style.display = 'none';
    document.getElementById('sev-rec-teleprompter').style.display = 'none';
    document.getElementById('sev-rec-done').style.display = 'none';
    document.getElementById('sev-cal-distance').style.display = 'flex';
    document.getElementById('sev-cal-measure').style.display = 'none';
    document.getElementById('sev-cal-done').style.display = 'none';
  } else {
    document.getElementById('sev-calibration').style.display = 'none';
    renderSevStep();
  }
}

function startSevCalibration() {
  document.getElementById('sev-cal-distance').style.display = 'none';
  document.getElementById('sev-cal-measure').style.display = 'flex';
  let count = 5;
  const cdEl = document.getElementById('sev-cal-countdown');
  const barEl = document.getElementById('sev-cal-bar');
  cdEl.textContent = count;
  barEl.style.width = '0%';

  const iv = setInterval(() => {
    count--;
    cdEl.textContent = count;
    barEl.style.width = ((5 - count) / 5 * 100) + '%';
    if (count <= 0) {
      clearInterval(iv);
      // 완료 표시
      document.getElementById('sev-cal-measure').style.display = 'none';
      document.getElementById('sev-cal-done').style.display = 'flex';
      sevCalibrated = true;
      // 1.5초 후 자동으로 첫 과제로
      setTimeout(() => {
        document.getElementById('sev-calibration').style.display = 'none';
        renderSevStep();
      }, 1500);
    }
  }, 1000);
}

function backToSevList() {
  stopSevAll();
  document.getElementById('sev-rec-view').style.display = 'none';
  document.getElementById('sev-list-view').style.display = '';
  renderSevList();
}

function renderSevStep() {
  const task = SEV_TASKS[sevState.taskIdx];
  const list = task.list;
  const d = list[sevState.step];
  const total = list.length;
  document.getElementById('sev-rec-title').textContent = task.name;
  const rb = document.getElementById('sev-rec-badge');
  rb.style.background = task.badge[0]; rb.style.color = task.badge[1];
  rb.textContent = (sevState.step+1) + ' / ' + total;
  const pct = Math.round((sevState.step / total) * 100);
  document.getElementById('sev-prog-bar').style.width = pct + '%';
  // 모든 서브뷰 숨김
  document.getElementById('sev-calibration').style.display = 'none';
  document.getElementById('sev-rec-main').style.display = 'none';
  document.getElementById('sev-rec-teleprompter').style.display = 'none';
  document.getElementById('sev-rec-done').style.display = 'none';

  if (sevState.taskIdx === 2) {
    // 단어 읽기 → 텔레프롬프터 모드
    rb.textContent = list.length + '개 단어';
    document.getElementById('sev-prog-bar').style.width = '0%';
    document.getElementById('sev-rec-teleprompter').style.display = 'flex';
    initTeleprompter();
  } else {
    // 모음/퍼터커 → 기존 방식
    document.getElementById('sev-word').textContent = d.word;
    document.getElementById('sev-instruction').textContent = d.instruction;
    setSevFeedback('idle');
    setSevMicIdle();
    document.getElementById('sev-rec-main').style.display = 'flex';
  }
  document.getElementById('sev-submit-label').textContent = '다음';
}

// ── 텔레프롬프터 (단어 읽기) ──
let tpState = { wordIdx: 0, recording: false, timer: null, scrollTimer: null, sec: 0 };

function initTeleprompter() {
  const track = document.getElementById('sev-tp-track');
  track.innerHTML = '';
  SEV_WORDS_RAW.forEach((w, i) => {
    const span = document.createElement('span');
    span.className = 'sev-tp-word' + (i === 0 ? ' active' : '');
    span.textContent = w;
    span.id = 'tp-w-' + i;
    track.appendChild(span);
  });
  track.style.transform = 'translateX(0px)';
  tpState = { wordIdx: 0, recording: false, timer: null, scrollTimer: null, sec: 0 };
  document.getElementById('sev-tp-mic-btn').classList.remove('recording');
  document.getElementById('sev-tp-mic-label').textContent = '눌러서 말하기';
  document.getElementById('sev-tp-fb').textContent = '마이크를 누르고 단어를 읽어 주세요';
  document.getElementById('sev-tp-fb').style.color = 'var(--t3)';
}

// ── 공통 마이크 스트림 유지 ──
let globalStream = null;

async function getMicStream() {
  if (globalStream) return globalStream;
  try {
    globalStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    return globalStream;
  } catch (err) {
    console.error("Mic access denied", err);
    return null;
  }
}

let currentTpRecorder = null;

function startTpRecorderWord(word) {
  getMicStream().then(stream => {
    if (!stream) return;
    const chunks = [];
    currentTpRecorder = new MediaRecorder(stream);
    currentTpRecorder.ondataavailable = e => chunks.push(e.data);
    currentTpRecorder.onstop = () => {
      const blob = new Blob(chunks, {type:'audio/webm'});
      audioBlobs.words.push({word: word, blob: blob});
    };
    currentTpRecorder.start();
  });
}

function scrollTeleprompter() {
  const total = SEV_WORDS_RAW.length;
  if (tpState.wordIdx >= total) return;
  
  // 이전 단어가 있으면 녹음 멈추기 & 넘기기
  if (tpState.wordIdx > 0) {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
      mediaRecorder.stop();
    }
    const prev = document.getElementById('tp-w-' + (tpState.wordIdx - 1));
    if (prev) { prev.classList.remove('active'); prev.classList.add('done'); }
    
    // 약간의 딜레이 후 재시작
    setTimeout(() => {
        tpState.currentWord = SEV_WORDS_RAW[tpState.wordIdx];
        if (tpState.recording) {
            startTpRecorderWord(tpState.currentWord);
        }
    }, 100);
  } else {
    // 첫 단어 접근
    tpState.currentWord = SEV_WORDS_RAW[tpState.wordIdx];
    if (tpState.recording) {
        startTpRecorderWord(tpState.currentWord);
    }
  }

  // 현재 단어 active
  const cur = document.getElementById('tp-w-' + tpState.wordIdx);
  if (cur) { cur.classList.add('active'); }
  // 트랙 이동 (단어를 왼쪽으로)
  const track = document.getElementById('sev-tp-track');
  const container = document.getElementById('sev-tp-container');
  const containerW = container.offsetWidth;
  const wordEl = document.getElementById('tp-w-' + tpState.wordIdx);
  if (wordEl) {
    const wordLeft = wordEl.offsetLeft;
    const offset = Math.max(0, wordLeft - containerW * 0.3);
    track.style.transform = 'translateX(-' + offset + 'px)';
  }
  // 프로그레스 업데이트
  const pct = Math.round(((tpState.wordIdx + 1) / total) * 100);
  document.getElementById('sev-prog-bar').style.width = pct + '%';
  const rb = document.getElementById('sev-rec-badge');
  rb.textContent = (tpState.wordIdx + 1) + ' / ' + total;

  tpState.wordIdx++;
  if (tpState.wordIdx >= total) {
    // 모든 단어 완료
    setTimeout(() => {
      stopTpRec();
      // 마지막 단어도 done 처리
      const last = document.getElementById('tp-w-' + (total - 1));
      if (last) { last.classList.remove('active'); last.classList.add('done'); }
      document.getElementById('sev-tp-fb').textContent = '녹음 완료!';
      document.getElementById('sev-tp-fb').style.color = '#16A34A';
      document.getElementById('sev-tp-mic-btn').classList.remove('recording');
      document.getElementById('sev-tp-mic-label').textContent = '완료';
      // 잘 했어요 화면으로
      setTimeout(() => { showSevRecDone(); }, 1200);
    }, 3000); // 3초 간격이므로 마지막에도 3초 대기 후 종료
  }
}

function startTpRecorderWord(word) {
  getMicStream().then(stream => {
    if (!stream) return;
    tpState.chunks = [];
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = e => tpState.chunks.push(e.data);
    mediaRecorder.onstop = () => {
      const blob = new Blob(tpState.chunks, {type:'audio/webm'});
      audioBlobs.words.push({word: word, blob: blob});
    };
    mediaRecorder.start();
  });
}

function toggleSevTpRec() {
  if (tpState.wordIdx >= SEV_WORDS_RAW.length) return; // 이미 완료
  if (!tpState.recording) {
    tpState.recording = true;
    document.getElementById('sev-tp-mic-btn').classList.add('recording');
    document.getElementById('sev-tp-mic-label').textContent = '탭하여 완료';
    document.getElementById('sev-tp-fb').textContent = '단어를 순서대로 읽어 주세요';
    document.getElementById('sev-tp-fb').style.color = '#E24B4A';
    
    // 즉시 첫 단어 스크롤 및 녹음 시작
    scrollTeleprompter();
    // 3초마다 다음 단어로 스크롤
    tpState.scrollTimer = setInterval(scrollTeleprompter, 3000);
  } else {
    stopTpRec();
    showSevRecDone();
  }
}

function stopTpRec() {
  tpState.recording = false;
  if (tpState.scrollTimer) { clearInterval(tpState.scrollTimer); tpState.scrollTimer = null; }
  document.getElementById('sev-tp-mic-btn').classList.remove('recording');
  document.getElementById('sev-tp-mic-label').textContent = '눌러서 말하기';
  
  if (mediaRecorder && mediaRecorder.state === 'recording') {
    mediaRecorder.stop();
  }
}

function showSevRecDone() {
  document.getElementById('sev-rec-main').style.display = 'none';
  document.getElementById('sev-rec-teleprompter').style.display = 'none';
  document.getElementById('sev-rec-done').style.display = 'flex';
  // 프로그레스 바 100% 채우기
  document.getElementById('sev-prog-bar').style.width = '100%';
  // 단어읽기는 한 번에 처리하므로 step을 마지막으로 설정
  if (sevState.taskIdx === 2) {
    sevState.step = SEV_WORDS.length - 1;
  }
}

function setSevFeedback(s, msg) {
  const txt = document.getElementById('sev-fb-text');
  if (s === 'idle')           { txt.style.color='var(--t3)'; txt.textContent='마이크를 누르고 소리를 내보세요'; }
  else if (s === 'recording') { txt.style.color='#E24B4A'; txt.textContent = msg || '녹음 중...'; }
  else if (s === 'done')      { txt.style.color='#2E7D32'; txt.textContent = msg || '잘 했어요!'; }
  else if (s === 'short')     { txt.style.color='#D97706'; txt.textContent='조금 더 길게 소리를 내보세요'; }
}

function setSevMicIdle() {
  const btn = document.getElementById('sev-mic-btn');
  btn.classList.remove('recording');
  document.getElementById('sev-mic-label').textContent = '눌러서 말하기';
  sevState.recording = false;
}

function stopSevAll() {
  if (sevState.timer) { clearInterval(sevState.timer); sevState.timer = null; }
  if (sevState.waveTimer) { clearInterval(sevState.waveTimer); sevState.waveTimer = null; }
  sevState.recording = false;
}

function drawSevWaveIdle() {}
function drawSevWaveActive() {}


function toggleSevRec() {
  if (!sevState.recording) {
    sevState.recording = true;
    document.getElementById('sev-mic-btn').classList.add('recording');
    document.getElementById('sev-mic-label').textContent = '탭하여 완료';
    sevState.sec = 0;
    
    audioBlobs.currentStep = sevState.step;
    
    getMicStream().then(stream => {
      if (!stream) { alert("마이크 권한이 필요합니다."); return; }
      tpState.chunks = [];
      mediaRecorder = new MediaRecorder(stream);
      mediaRecorder.ondataavailable = e => tpState.chunks.push(e.data);
      mediaRecorder.onstop = () => {
        const blob = new Blob(tpState.chunks, {type:'audio/webm'});
        if (sevState.taskIdx === 0) {
          audioBlobs.vowels[sevState.subIdx] = blob;
        } else if (sevState.taskIdx === 1) {
          audioBlobs.putterker = blob;
        }
      };
      mediaRecorder.start();
    });

    setSevFeedback('recording', '녹음 중... 소리를 내어 주세요');
    sevState.waveTimer = setInterval(drawSevWaveActive, 80);
    sevState.timer = setInterval(() => {
      sevState.sec++;
      if (sevState.sec < 2) setSevFeedback('recording', '조금 더 길게 소리를 내보세요');
      else setSevFeedback('recording', sevState.sec + '초 녹음 중...');
    }, 1000);
  } else {
    stopSevAll();
    drawSevWaveIdle();
    if (mediaRecorder && mediaRecorder.state === 'recording') mediaRecorder.stop();

    if (sevState.sec < 2) {
      setSevFeedback('short');
      setSevMicIdle();
    } else {
      setSevMicIdle();
      const task = SEV_TASKS[sevState.taskIdx];
      const total = task.list.length;
      if (sevState.step + 1 >= total) {
        // 과제의 마지막 항목 → 잘 했어요! 화면
        showSevRecDone();
      } else {
        // 중간 항목 → 바로 다음으로
        sevState.step++;
        renderSevStep();
      }
    }
  }
}

function sevNextStep() {
  const task = SEV_TASKS[sevState.taskIdx];
  const total = task.list.length;
  if (sevState.step + 1 >= total) {
    // 현재 과제 완료
    sevState.done[sevState.taskIdx] = true;
    // 다음 미완료 과제 찾기
    const nextIdx = sevState.done.indexOf(false);
    if (nextIdx < 0) {
      // 모든 과제 완료 → 완료 화면
      showSevComplete();
    } else {
      sevState.taskIdx = nextIdx;
      backToSevList();
    }
  } else {
    sevState.step++;
    renderSevStep();
  }
}

function showSevComplete() {
  document.getElementById('sev-rec-view').style.display = 'none';
  document.getElementById('sev-list-view').style.display = 'none';
  document.getElementById('sev-complete-view').style.display = 'flex';
  
  document.getElementById('sev-analyzing-view').style.display = 'flex';
  document.getElementById('sev-result-view').style.display = 'none';

  submitToBackend();
}

function applySevResultUI(cls) {
  const PAL = [
    { accent:'#3B5FE8', bg: '#DCFCE7', text: '#16A34A', btn: '#3B5FE8', label:'완료 ✓', cardLabel:'양호', subLabel:'현재 상태가 안정적이에요', title:'말소리가 또렷하고\n상태가 좋아요!', desc:'꾸준히 유지해주세요\n지금처럼 하면 됩니다' },
    { accent:'#F97316', bg: '#FFEDD5', text: '#EA580C', btn: '#3B5FE8', label:'진행중', cardLabel:'주의', subLabel:'꾸준한 훈련이 필요해요', title:'꾸준한 훈련이\n많은 도움이 될 거예요', desc:'매일 조금씩 연습하면\n말소리가 훨씬 또렷해질 수 있어요' },
    { accent:'#EF4444', bg: '#FEE2E2', text: '#DC2626', btn: '#EF4444', label:'주의필요', cardLabel:'위험', subLabel:'전문 상담을 권장해요', title:'지금 바로 집중적인\n훈련을 시작해보세요', desc:'전문 치료사와 함께하면\n더 빠르게 회복할 수 있어요' },
  ];
  const p = PAL[cls] || PAL[0];
  
  // 헤더 뱃지
  const badge = document.getElementById('sev-res-badge');
  badge.textContent = p.label;
  badge.style.background = p.bg;
  badge.style.color = p.text;
  
  // 신호등
  for(let i=0; i<3; i++) {
     const light = document.getElementById(`sev-light-${i}`);
     const lbl = document.getElementById(`sev-light-lbl-${i}`);
     if(i === cls) {
        light.style.width = '62px';
        light.style.height = '62px';
        light.style.background = p.accent;
        light.style.boxShadow = `0 0 20px ${p.accent}88`;
        lbl.style.color = p.accent;
     } else {
        light.style.width = '48px';
        light.style.height = '48px';
        light.style.background = 'rgba(255,255,255,0.08)';
        light.style.boxShadow = 'none';
        lbl.style.color = 'rgba(255,255,255,0.35)';
     }
  }
  
  // 중간 텍스트
  const cLabel = document.getElementById('sev-res-label');
  cLabel.textContent = (cls===0)?'양호':(cls===1)?'훈련이 도움돼요':'집중 훈련 필요';
  cLabel.style.color = p.accent;
  document.getElementById('sev-res-sublabel').textContent = p.subLabel;
  
  // 큰 메시지
  document.getElementById('sev-res-title').textContent = p.title;
  document.getElementById('sev-res-desc').textContent = p.desc;
  
  // 점 인디케이터
  for(let i=0; i<3; i++) {
     document.getElementById(`sev-dot-${i}`).style.background = (i===cls) ? p.accent : '#D1D5DB';
  }
  
  // 버튼 액센트
  const btn = document.getElementById('sev-detail-btn');
  btn.style.background = p.btn;
  btn.style.boxShadow = `0 4px 14px ${p.btn}55`;
  
  // 화면 전환
  document.getElementById('sev-analyzing-view').style.display = 'none';
  document.getElementById('sev-result-view').style.display = 'flex';
}

async function submitToBackend() {
  try {
    const fd = new FormData();
    if (audioBlobs.putterker) fd.append('putterker', audioBlobs.putterker, 'putterker.webm');
    
    if (audioBlobs.vowels[0]) fd.append('vowel_a', audioBlobs.vowels[0], 'vowel_a.webm');
    if (audioBlobs.vowels[1]) fd.append('vowel_i', audioBlobs.vowels[1], 'vowel_i.webm');
    if (audioBlobs.vowels[2]) fd.append('vowel_u', audioBlobs.vowels[2], 'vowel_u.webm');
    
    audioBlobs.words.forEach((w) => {
       fd.append('word_files', w.blob, w.word + '.webm');
    });
    fd.append('word_sex', 'M');
    fd.append('word_age', 50);

    const res = await fetch('http://localhost:8000/api/predict', {
      method: 'POST',
      body: fd
    });
    const data = await res.json();
    console.log("Prediction Result:", data);

    if (data.status === 'success') {
       let cls = data.severity_class; // 0: Normal, 1: Mild, 2: Severe
       if (cls === undefined) cls = 0;
       if (cls === 2) setSev('severe');
       else if (cls === 1) setSev('moderate');
       else setSev('mild');
       applySevResultUI(cls);
    } else {
       applySevResultUI(0);
    }
  } catch(e) {
    console.error("Backend Error:", e);
    applySevResultUI(0);
  }
}


/* ══════════════════════════════════════════════════════════
   PROTOTYPE CONTROLS
══════════════════════════════════════════════════════════ */
function setDep(v) {
  dep = v;
  ['high','mid','low'].forEach(x => document.getElementById('d-'+x).classList.remove('on'));
  document.getElementById('d-'+v).classList.add('on');
}
function setSev(v) {
  sev = v;
  ['severe','moderate','mild'].forEach(x => document.getElementById('s-'+x).classList.remove('on'));
  document.getElementById('s-'+v).classList.add('on');
}
function setAllLv(lv) {
  Object.keys(LEVELS).forEach(id => {
    const maxLv = LEVELS[id].length;
    playerLvl[id] = Math.min(lv, maxLv);
  });
  [1,2,3,4].forEach(n => document.getElementById('pl-'+n).classList.remove('on'));
  document.getElementById('pl-'+lv).classList.add('on');
}
function setMode(v) {
  mode = v;
  const focusActive = v === 'focus';
  // update tab buttons
  document.getElementById('mode-tab-integ').style.background = focusActive ? 'transparent' : 'var(--primary)';
  document.getElementById('mode-tab-integ').style.color = focusActive ? 'var(--t3)' : 'white';
  document.getElementById('mode-tab-focus').style.background = focusActive ? 'var(--green)' : 'transparent';
  document.getElementById('mode-tab-focus').style.color = focusActive ? 'white' : 'var(--t3)';
  // update home badge
  const badge = document.getElementById('mode-badge');
  if (badge) {
    badge.textContent = focusActive ? '순수 재활 · 우울 정상' : 'rPPG + 중증도 연동';
    badge.style.background = focusActive ? 'var(--green-l)' : 'var(--primary-l)';
    badge.style.color = focusActive ? '#15803D' : 'var(--primary)';
  }
  // hide/show rPPG dep controls
  const depCtrl = document.getElementById('dep-ctrl');
  if (depCtrl) depCtrl.style.display = focusActive ? 'none' : 'flex';
}

/* ══════════════════════════════════════════════════════════
   rPPG SIMULATION
══════════════════════════════════════════════════════════ */
/* ── 일일 플로우 모드 ── */
let dailyFlow = false;

function startDailyFlow() {
  dailyFlow = true;
  goto('rppg');
}

function rppgNext() {
  if (dailyFlow) {
    dailyFlow = false;
    goto('tasks');
  } else {
    goto('home');
  }
}

function resetRppg() {
  document.getElementById('rppg-before').style.display = 'block';
  document.getElementById('rppg-during').style.display = 'none';
  document.getElementById('rppg-after').style.display  = 'none';
  document.getElementById('rppg-bottom-btn').style.display = 'none';
  // 플로우 모드에 따라 버튼 텍스트 변경
  const btn = document.getElementById('rppg-next-btn');
  btn.textContent = dailyFlow ? '맞춤 훈련 시작 →' : '홈으로 돌아가기';
}

function startRppg() {
  document.getElementById('rppg-before').style.display = 'none';
  document.getElementById('rppg-during').style.display = 'block';
  rppgSec = 30;
  const msgEl = document.getElementById('rppg-progress-msg');
  msgEl.textContent = '조금만요';
  document.getElementById('rppg-fill').style.width = '0%';

  // bpm animation
  const r = RPPG[dep];
  let bpmCur = 95;
  bpmIv = setInterval(() => {
    bpmCur += (Math.random() - 0.5) * 4;
    bpmCur = Math.max(60, Math.min(100, bpmCur));
    document.getElementById('bpm-val').textContent = Math.round(bpmCur);
  }, 300);

  rppgIv = setInterval(() => {
    rppgSec--;
    const pct = ((30 - rppgSec) / 30) * 100;
    document.getElementById('rppg-fill').style.width = pct + '%';

    if (rppgSec <= 20 && rppgSec > 10) {
      msgEl.textContent = '잘하고 있어요';
    }
    if (rppgSec <= 10 && rppgSec > 0) {
      msgEl.textContent = '거의 다 됐어요';
    }
    if (rppgSec <= 0) {
      clearInterval(rppgIv);
      clearInterval(bpmIv);
      showRppgResult();
    }
  }, 1000);
}

function showRppgResult() {
  document.getElementById('rppg-during').style.display = 'none';
  document.getElementById('rppg-after').style.display  = 'flex';
  document.getElementById('rppg-bottom-btn').style.display = 'block';
  const c = combo();

  const r = RPPG[dep];
  const el = document.getElementById('rr-level-text');
  el.textContent = r.lvl;
  el.style.color = 'var(--primary)';
  document.getElementById('rr-desc').textContent = r.desc;

  document.getElementById('rr-preview-strat').textContent = '쉬운 연습 ' + c.ids.length + '가지';
  document.getElementById('rr-preview-dur').textContent   = c.dur.replace(/분/, '분이면 충분해요');
}

/* ══════════════════════════════════════════════════════════
   TASKS RENDER
══════════════════════════════════════════════════════════ */
function renderAllEx() {
  const groups = [
    { name: '기초 준비', ids: [1, 2, 12] },
    { name: '호흡/발성 연습', ids: [3, 4, 5, 6, 7, 8, 9] },
    { name: '발음 연습', ids: [10, 16] },
    { name: '말하기 연습', ids: [11, 13, 14, 15] },
  ];
  const VIDEO_IDS = [1,2,3,4,5,6,7,8,10,11,12,16];
  let html = '';
  groups.forEach(g => {
    html += `<div class="all-group-title">${g.name}</div>`;
    g.ids.forEach(id => {
      const ex = EX[id];
      if (!ex) return;
      const hasVideo = VIDEO_IDS.includes(id);
      html += `<div class="all-ex-card" onclick="openExSingle(${id})">
        <div>
          <div class="all-ex-name">${ex.n}</div>
          <div class="all-ex-desc">${ex.d}</div>
          ${hasVideo ? '<div class="all-ex-video">영상 가이드 있음</div>' : ''}
        </div>
        <div class="all-ex-dur">${ex.dur}</div>
      </div>`;
    });
  });
  document.getElementById('all-ex-body').innerHTML = html;
}

function renderTasks() {
  const c = combo();
  // 전략 카드 (따뜻한 톤)
  const sc = document.getElementById('strat-card');
  sc.style.background = c.stratBg;
  document.getElementById('sc-msg').textContent = c.msg;
  document.getElementById('sc-msg').style.color = c.stratText;
  document.getElementById('sc-dur').textContent = c.dur.replace(/분/, '분이면 돼요');
  document.getElementById('sc-cnt').textContent = c.ids.length + '가지 연습';

  const grpNames = {'gb':'숨쉬기 연습', 'ga':'발음 연습', 'gp':'말하기 연습'};
  const dotColors = {'gb':'var(--primary)', 'ga':'var(--accent)', 'gp':'#EC4899'};
  let html = '', lastG = '';
  c.ids.forEach(id => {
    const ex = EX[id];
    if (ex.g !== lastG) {
      lastG = ex.g;
      html += `<div class="sec-hdr">
        <div class="sec-dot" style="background:${dotColors[ex.g]};"></div>
        <div class="sec-lbl">${grpNames[ex.g]}</div>
      </div>`;
    }
    const lv = getLvl(id);
    const lvHtml = lv ? `<span class="lv-badge">Lv.${lv.lv}</span>` : '';
    html += `<div class="ex-card ${ex.g}" onclick="openExSingle(${id})">
      <div class="ex-b" style="padding-left:4px;">
        <div class="ex-name">${ex.n} ${lvHtml}</div>
        <div class="ex-desc">${ex.d}</div>
        <div class="ex-tags">
          <span class="tag tag-d">${ex.dur}</span>
        </div>
      </div>
      <div class="ex-arr">›</div>
    </div>`;
  });
  document.getElementById('task-list').innerHTML = html;
}

/* ══════════════════════════════════════════════════════════
   EXERCISE FLOW
══════════════════════════════════════════════════════════ */
let curIdx = 0;
let vidIv = null, vidSec = 0;
let recIv = null;

const TIPS = {
  1:  "등을 곧게 펴고, 발바닥을 바닥에 붙이세요. 어깨는 편안히 내리고, 턱을 살짝 당겨 주세요. 이 자세가 발성을 훨씬 도와줍니다.",
  2:  "입술 오므리기 5회 → 혀 내밀기 5회 → 크게 벌리기 5회 순서로 진행해요. 천천히, 끝까지 충분히 움직여 주세요.",
  3:  '"아~~~" 소리를 최대한 길고 안정적으로 유지하세요. 숨이 다 할 때까지 끊기지 않게 이어가세요.',
  4:  '"아~" 소리를 내면서 낮은 음에서 천천히 위로 올려보세요. 미끄러지듯 부드럽게, 급하지 않게.',
  5:  '"아~" 소리를 내면서 높은 음에서 천천히 아래로 내려보세요. 목에 힘을 빼고 편안하게.',
  6:  "화면에 표시된 목표 음도에 맞춰 발성하세요. 처음엔 어렵지만 천천히 시도하면 됩니다.",
  7:  '"아!" 소리를 힘차고 크게 외치세요. 평소보다 훨씬 크게 — 처음엔 어색해도 괜찮아요.',
  8:  '"이!" 발음 시 성대를 확실히 닫는 느낌으로 힘주어 시작하세요. 강하게 시작하는 것이 핵심이에요.',
  9:  '크게 하품하듯 입을 벌리고 깊게 숨을 들이쉬세요. 그리고 "하~" 하고 천천히 내쉬세요.',
  10: '"발/팔", "달/탈" 처럼 비슷한 단어를 정확히 구별해서 말하세요. 천천히, 또렷하게 발음하세요.',
  11: '문장에서 강조할 단어를 바꾸어 읽으세요. "나는 사과를 먹었다" 처럼 강세 위치를 달리해보세요.',
  12: "코로 3초 들이쉬고, 입으로 5초 이상 천천히 내쉬세요. 배가 나오면 복식 호흡이 잘 되는 거예요.",
  13: "테이블을 손으로 두드리며 음절 박자에 맞추어 말하세요. 탭과 말소리가 동시에 나오도록 하세요.",
  14: "평소보다 2배 천천히 읽으세요. 각 음절을 또렷하게 발음하고, 절대 서두르지 마세요.",
  15: '문장을 최대한 크게, 또렷하게 읽으세요. 힘차게 "LOUD!" 느낌으로 읽으면 좋아요.',
  16: '"/퍼터커/" 를 최대한 빠르고 정확하게 반복하세요. 처음엔 천천히, 점점 빠르게 하세요.',
  'mini': '"아~~~" 3초 → /퍼터커/ 5회 → 기준 단어 5개 순서로 진행합니다. 매일 같은 단어로 추이를 비교해요.',
};

const METRICS = {
  3:  {lbl:"현재 발성 시간", u:"초",    goal:"목표: 15초 이상",       max:15,  mode:'time'},
  4:  {lbl:"음도 변화폭",   u:"Hz",   goal:"목표: 80Hz 이상",       max:80,  mode:'pitch'},
  5:  {lbl:"음도 변화폭",   u:"Hz",   goal:"목표: 80Hz 이상",       max:80,  mode:'pitch'},
  6:  {lbl:"목표음도 오차", u:"Hz",   goal:"목표: 오차 ±15Hz 이내", max:15,  mode:'err'},
  7:  {lbl:"현재 음량",     u:"dB",   goal:"목표: 70dB 이상",       max:70,  mode:'dB'},
  8:  {lbl:"음성 선명도",   u:"점",   goal:"목표: 80점 이상",       max:80,  mode:'pct'},
  9:  {lbl:"호기 지속시간", u:"초",   goal:"목표: 10초 이상",       max:10,  mode:'time'},
  10: {lbl:"STT 명료도",   u:"%",    goal:"목표: 70% 이상",        max:70,  mode:'pct'},
  11: {lbl:"강세 정확도",   u:"%",    goal:"목표: 70% 이상",        max:70,  mode:'pct'},
  12: {lbl:"호기 지속시간", u:"초",   goal:"목표: 8초 이상",        max:8,   mode:'time'},
  13: {lbl:"타이밍 정확도", u:"%",    goal:"목표: 75% 이상",        max:75,  mode:'pct'},
  14: {lbl:"말 속도",       u:"어/분", goal:"목표: 100어/분 이하",   max:100, mode:'rate'},
  15: {lbl:"현재 음량",     u:"dB",   goal:"목표: 70dB 이상",       max:70,  mode:'dB'},
  16: {lbl:"DDK 속도",      u:"Hz",   goal:"목표: 4.0Hz 이상",      max:4.0, mode:'ddk'},
  'mini':{lbl:"경과 시간",  u:"초",   goal:"3가지 과제 완료",       max:60,  mode:'time'},
};

const SELF_DATA = {
  1: {
    fb:"좋은 자세가 발성을 도와줘요. 훈련 내내 유지해보세요!",
    checks:["등을 곧게 펴기","발바닥을 바닥에 붙이기","어깨를 편안히 내리기","턱을 살짝 당기기"]
  },
  2: {
    fb:"구강 근육이 따뜻해졌어요. 이제 발성 훈련이 더 잘 돼요!",
    checks:["입술 오므리기 3회","혀 내밀기 3회","크게 벌리기 3회"]
  },
};
let selfTimerIv = null;

function startSession() {
  sessionLvChanges = []; // 레벨 변동 기록 초기화
  curIdx = 0;
  loadExercise();
  goto('run');
}

function openExSingle(id) {
  const c = combo();
  let idx = c.ids.indexOf(id);
  if (idx < 0) {
    // 콤보에 없는 운동 → 임시로 끝에 추가
    c.ids.push(id);
    const ex = EX[id];
    c.results.push({e:ex.e, n:ex.n, met:'완료'});
    idx = c.ids.length - 1;
  }
  curIdx = idx;
  loadExercise();
  goto('run');
}

function loadExercise() {
  stopRecTimer();
  const c = combo();
  const id = c.ids[curIdx];
  const ex = (id === 'mini') ? {n:'미니 평가', e:'평가', gn:'준비 운동', t:'auto'} : EX[id];
  const total = c.ids.length;

  document.getElementById('run-cat').textContent   = ex.gn;
  document.getElementById('run-name').textContent  = ex.n;
  document.getElementById('run-badge').textContent = (curIdx+1) + ' / ' + total;
  document.getElementById('run-pfill').style.width = (curIdx / total * 100) + '%';
  document.getElementById('tip-txt').textContent   = TIPS[id] || ex.detail || '';

  // 영상 매핑
  const VIDEO_MAP = {
    1:  'videos/1. 발성의 시작, 바른 자세 교정 훈련_1080p_caption.mp4',
    2:  'videos/2. 구강 운동 가이드 (통합 수정본)_1080p_caption.mp4',
    3:  'videos/3. 최대발성지속 시범 및 안내_1080p_caption.mp4',
    4:  'videos/4.음도 글라이딩 정석 시연 (흰 배경)_1080p_caption.mp4',
    5:  'videos/5. 음도 글라이딩 완벽 하강 시연 (흰 배경)_1080p_caption.mp4',
    6:  'videos/6. 정교한 소리 조절, 피치 조절 훈련 (흰 배경)_1080p_caption.mp4',
    7:  'videos/7. 볼륨업 (크게 발성) 훈련 안내_1080p_caption.mp4',
    8:  'videos/8. 성문폐쇄 (Voice Onset) 훈련 안내_1080p_caption.mp4',
    10: 'videos/10. 정확한 발음의 기초, 대조 훈련 (최소 대립쌍)_1080p_caption.mp4',
    11: 'videos/11. 의미를 전달하는 힘, 대립강세 훈련 (흰 배경)_1080p_caption (1).mp4',
    12: 'videos/12_1. 발성의 기초, 복식 호흡 훈련 (흰 배경)_1080p_caption.mp4',
    16: 'videos/16. 조음 민첩성 향상, DDK 직접 훈련 (_퍼터커_)_1080p_caption.mp4',
  };
  const videoEl = document.getElementById('ex-video');
  const thumbFallback = document.getElementById('vid-thumb-fallback');
  const ctrlFallback = document.getElementById('vid-ctrl-fallback');
  if (VIDEO_MAP[id]) {
    videoEl.style.display = 'block';
    videoEl.src = VIDEO_MAP[id];
    videoEl.load();
    thumbFallback.style.display = 'none';
    ctrlFallback.style.display = 'none';
  } else {
    videoEl.style.display = 'none';
    videoEl.src = '';
    thumbFallback.style.display = 'flex';
    ctrlFallback.style.display = 'flex';
    document.getElementById('vid-ico').textContent = ex.e;
  }

  // 오늘의 목표 표시
  const lvData = getLvl(id);
  const lvBar  = document.getElementById('lv-info');
  if (lvData) {
    lvBar.style.display = 'block';
    // 환자 친화적 목표 문구
    const friendlyGoals = {
      2:  ['입술·혀·턱 각 3회','입술·혀·턱 각 5회','입술·혀·턱 각 5회 빠르게'],
      3:  ['3초 이상 소리 내기','5초 이상 소리 내기','8초 이상 소리 내기','12초 이상 소리 내기'],
      4:  ['낮은 음에서 올리기','편안하게 올리기','넓게 올리기','최대한 넓게 올리기'],
      5:  ['높은 음에서 내리기','편안하게 내리기','넓게 내리기','최대한 넓게 내리기'],
      6:  ['목표 음 따라가기','정확하게 맞추기','빠르게 맞추기','자유롭게 조절하기'],
      7:  ['60dB 이상 내기','65dB 이상 내기','70dB 이상 내기','75dB 이상 크게'],
      8:  ['확실하게 시작하기','빠르게 시작하기','연속 5회','연속 10회'],
      9:  ['하품-한숨 3회','하품-한숨 5회','길게 내쉬기','발성 연결하기'],
      10: ['쉬운 단어 4쌍','쉬운 단어 6쌍','어려운 단어 6쌍','어려운 단어 8쌍'],
      11: ['2가지 강세 연습','3가지 강세 연습','빠르게 전환','자유 문장'],
      12: ['복식호흡 3회','복식호흡 5회','복식호흡 5회 + 길게','복식호흡 5회 + 발성'],
      13: ['2음절 단어 + 박자','3음절 단어 + 박자','짧은 문장 + 박자','긴 문장 + 박자'],
      14: ['짧은 문장 천천히','긴 문장 천천히','또렷하게 읽기','자연스럽게 읽기'],
      15: ['짧은 문장 크게','긴 문장 크게','또렷하고 크게','자연스럽고 크게'],
      16: ['/퍼터커/ 천천히','/퍼터커/ 보통 속도','/퍼터커/ 빠르게','/퍼터커/ 최대 속도'],
    };
    const fg = friendlyGoals[id];
    const goalText = fg ? '오늘 목표: ' + fg[lvData.lv - 1] : lvData.goalTxt;
    document.getElementById('lv-goal-run').textContent = goalText;
  } else {
    lvBar.style.display = 'none';
  }

  // 힌트 텍스트
  document.getElementById('phase-hint').textContent = VIDEO_MAP[id] ? '영상 보고 천천히 따라해요' : '천천히 따라해보세요';

  resetVid();
  stopStressCycle();
  showStressDemo(id === 11);
  document.getElementById('vid-box').style.display      = 'block';
  const tipCard = document.querySelector('#screen-run .tip-card2');
  if (tipCard) tipCard.style.display = 'block';
  // 팁 접힌 상태로 리셋
  document.getElementById('tip-body').classList.remove('open');
  document.getElementById('tip-arrow').classList.remove('open');
  document.getElementById('phase-a').style.display      = 'block';
  document.getElementById('phase-b').style.display      = 'none';
  document.getElementById('phase-pitch').style.display  = 'none';
  document.getElementById('phase-b-read').style.display = 'none';
  document.getElementById('phase-c').style.display      = 'none';
  document.getElementById('phase-breath').style.display = 'none';
  document.getElementById('run-body').scrollTop = 0;
}

function startTask() {
  const c = combo();
  const id = c.ids[curIdx];
  const ex = (id === 'mini') ? {t:'auto'} : EX[id];

  document.getElementById('phase-a').style.display = 'none';
  document.getElementById('vid-box').style.display = 'none';
  document.querySelector('#screen-run .tip-card2').style.display = 'none';
  document.querySelector('#screen-run .body').scrollTop = 0;

  // 호흡 운동 전용
  const BREATH_EX = [9, 12];
  if (BREATH_EX.includes(id)) {
    document.getElementById('lv-info').style.display = 'none';
    startBreathGuide(id);
    return;
  }

  // 음도올리기/내리기/피치조절 전용
  const PITCH_EX = [4, 5, 6];
  if (PITCH_EX.includes(id)) {
    startPitchGuide(id);
    return;
  }

  if (ex.t === 'self') {
    const sd = SELF_DATA[id] || {fb:'잘 하셨어요!', checks:['과제를 따라해보세요']};
    document.getElementById('self-fb').textContent  = sd.fb;
    document.getElementById('self-fb').style.display   = 'none';
    document.getElementById('self-next').style.display = 'none';
    document.getElementById('self-btn').disabled       = false;
    document.getElementById('self-status').textContent = '지금 따라해보세요';
    document.getElementById('self-pulse').style.display = 'block';
    // 체크리스트 생성
    const checksEl = document.getElementById('self-checks');
    checksEl.innerHTML = sd.checks.map(txt =>
      `<div class="self-check-item">
        <div class="self-check-dot"></div>
        <div class="self-check-label">${txt}</div>
      </div>`
    ).join('');
    // 타이머 시작
    let selfSec = 0;
    document.getElementById('self-timer').textContent = '0:00';
    if (selfTimerIv) clearInterval(selfTimerIv);
    selfTimerIv = setInterval(() => {
      selfSec++;
      const m = Math.floor(selfSec / 60);
      const s = String(selfSec % 60).padStart(2, '0');
      document.getElementById('self-timer').textContent = m + ':' + s;
    }, 1000);
    document.getElementById('phase-c').style.display   = 'block';
  } else if (READ_EX[id]) {
    // 읽기 과제 전용 Phase B-read
    startReadTask(id);
  } else {
    const m = Object.assign({}, METRICS[id] || METRICS['mini']);
    // 레벨별 목표 덮어쓰기
    const lvData = getLvl(id);
    if (lvData && lvData.goalTxt) {
      m.goal = lvData.goalTxt;
      m.max  = lvData.max;
    }
    // 원형 프로그레스 초기화
    document.getElementById('ring-lbl').textContent = m.lbl;
    document.getElementById('ring-u').textContent   = m.u;
    document.getElementById('ring-val').textContent = (m.mode === 'rate') ? '180' : (m.mode === 'err' ? '35' : '0.0');
    document.getElementById('ring-fill').style.strokeDashoffset = '553';
    document.getElementById('ring-fill').style.stroke = 'var(--primary)';
    const VOICE_INIT_FB = {
      3:  '소리를 길~게 이어보세요!',
      4:  '낮은 음에서 천천히 올려보세요!',
      5:  '높은 음에서 부드럽게 내려보세요!',
      6:  '목표 음에 맞춰 소리 내보세요!',
      7:  '힘차게 크게 소리 내보세요!',
      8:  '강하게 "이!" 시작해보세요!',
      16: '"퍼터커" 반복해보세요!',
    };
    document.getElementById('ring-msg').textContent = VOICE_INIT_FB[id] || '소리를 내보세요';
    document.getElementById('ring-msg').style.color = 'var(--t1)';
    document.getElementById('voice-active').style.display = 'block';
    document.getElementById('voice-done').style.display   = 'none';
    document.getElementById('voice-next-btn').style.display = 'none';
    document.getElementById('phase-b').style.display = 'block';
    startRecTimer(id, m);
  }
}

/* ── 호흡 가이드 ──────────────────────── */
let breathIv = null;
function startBreathGuide(id) {
  // 운동별 설정
  const BREATH_CONFIG = {
    9:  { reps:3, inhale:4000, exhale:6000, rest:2000,
          inMsg:'크게 하품하듯 들이쉬세요', inSub:'입을 크게 벌리고',
          outMsg:'"하~" 내쉬세요', outSub:'천천히, 편안하게',
          doneMsg:'하품-한숨 3회를 완료했어요', doneFb:'목과 성대가 이완되고 있어요. 좋아요!' },
    12: { reps:3, inhale:3000, exhale:5000, rest:2000,
          inMsg:'코로 들이쉬세요', inSub:'배가 나오도록',
          outMsg:'입으로 내쉬세요', outSub:'천천히, 길게',
          doneMsg:'복식호흡 3회를 완료했어요', doneFb:'호흡이 점점 안정되고 있어요. 잘 하고 계세요!' },
  };
  const cfg = BREATH_CONFIG[id] || BREATH_CONFIG[12];
  const totalReps = cfg.reps;
  const inhaleTime = cfg.inhale;
  const exhaleTime = cfg.exhale;
  const restTime   = cfg.rest;
  let rep = 0;

  const circle  = document.getElementById('breath-circle');
  const guide   = document.getElementById('breath-guide');
  const sub     = document.getElementById('breath-sub');
  const counter = document.getElementById('breath-counter');
  const doneEl  = document.getElementById('breath-done');
  const fbEl    = document.getElementById('breath-fb');
  const nextBtn = document.getElementById('breath-next');

  // 초기화
  circle.className = 'breath-circle';
  guide.textContent = '준비하세요';
  sub.textContent = '편안한 자세로 시작해요';
  counter.textContent = '1 / ' + totalReps;
  doneEl.style.display = 'none';
  fbEl.style.display = 'none';
  nextBtn.style.display = 'none';
  document.getElementById('phase-breath').style.display = 'block';

  if (breathIv) clearTimeout(breathIv);

  // 1.5초 후 시작
  breathIv = setTimeout(() => runCycle(0), 1500);

  function runCycle(r) {
    if (r >= totalReps) {
      // 완료
      circle.className = 'breath-circle';
      guide.textContent = '';
      sub.textContent = '';
      counter.style.display = 'none';
      document.querySelector('.breath-circle-outer').style.display = 'none';
      doneEl.querySelector('.bd-sub').textContent = cfg.doneMsg;
      fbEl.textContent = cfg.doneFb;
      doneEl.style.display = 'block';
      fbEl.style.display = 'flex';
      nextBtn.style.display = 'block';
      return;
    }
    rep = r;
    counter.textContent = (r + 1) + ' / ' + totalReps;
    counter.style.display = 'block';
    document.querySelector('.breath-circle-outer').style.display = 'flex';

    // 들이쉬기
    circle.className = 'breath-circle inhale';
    guide.textContent = cfg.inMsg;
    sub.textContent = cfg.inSub;
    breathIv = setTimeout(() => {
      // 내쉬기
      circle.className = 'breath-circle exhale';
      guide.textContent = cfg.outMsg;
      sub.textContent = cfg.outSub;
      breathIv = setTimeout(() => {
        // 쉬기
        if (r + 1 < totalReps) {
          circle.className = 'breath-circle';
          guide.textContent = '잠시 쉬세요';
          sub.textContent = '';
          breathIv = setTimeout(() => runCycle(r + 1), restTime);
        } else {
          runCycle(r + 1);
        }
      }, exhaleTime);
    }, inhaleTime);
  }
}

function stopBreathGuide() {
  if (breathIv) { clearTimeout(breathIv); breathIv = null; }
}

/* ── 음도올리기/내리기/피치조절 가이드 ──────────── */
let pitchIv = null;
let curPitchId = null;
let pitchTotalReps = 3;

// 곡선 경로 위의 점 좌표 계산
function getPitchPoint(progress, type) {
  // progress: 0~1
  const W = 320, H = 200, pad = 30;
  const x = pad + progress * (W - pad * 2);
  let y;
  if (type === 'up') {
    // 아래→위 곡선 (아크)
    y = (H - pad) - progress * (H - pad * 2) - Math.sin(progress * Math.PI) * 30;
  } else if (type === 'down') {
    // 위→아래 곡선
    y = pad + progress * (H - pad * 2) + Math.sin(progress * Math.PI) * 30;
  } else {
    // 피치조절: 물결 곡선
    y = H / 2 + Math.sin(progress * Math.PI * 3) * 60;
  }
  return {x, y};
}

function buildPitchPath(type) {
  let d = '';
  for (let i = 0; i <= 100; i++) {
    const p = getPitchPoint(i / 100, type);
    d += (i === 0 ? 'M' : 'L') + p.x.toFixed(1) + ',' + p.y.toFixed(1);
  }
  return d;
}

function startPitchGuide(id) {
  curPitchId = id;
  pitchTotalReps = 3;
  const type = id === 4 ? 'up' : id === 5 ? 'down' : 'wave';

  // 곡선 경로 생성
  const fullPath = buildPitchPath(type);
  document.getElementById('pitch-path-bg').setAttribute('d', fullPath);
  document.getElementById('pitch-path').setAttribute('d', '');

  // Hz 라벨 & 메시지
  const msgs = {
    4: '소리를 내면서 올려보세요',
    5: '소리를 내면서 내려보세요',
    6: '목표 음에 맞춰보세요',
  };
  document.getElementById('pitch-msg').textContent = msgs[id] || '';
  document.getElementById('pitch-msg').style.color = 'var(--t1)';
  document.getElementById('pitch-hi-lbl').textContent = id === 6 ? '' : '아';

  // 초기 위치
  const startP = getPitchPoint(0, type);
  document.getElementById('pitch-dot').setAttribute('cx', startP.x);
  document.getElementById('pitch-dot').setAttribute('cy', startP.y);
  document.getElementById('pitch-dot-pulse').setAttribute('cx', startP.x);
  document.getElementById('pitch-dot-pulse').setAttribute('cy', startP.y);
  document.getElementById('pitch-hz').style.left = startP.x + 'px';
  document.getElementById('pitch-hz').style.top  = startP.y + 'px';
  const startHz = id === 5 ? 280 : id === 6 ? 180 : 120;
  document.getElementById('pitch-hz').textContent = startHz + ' Hz';
  document.getElementById('pitch-hz').style.background = 'var(--primary)';
  document.getElementById('pitch-hz').style.setProperty('--arrow-color', 'var(--primary)');
  document.getElementById('pitch-wave-fill').style.width = '0%';
  document.getElementById('pitch-rep').textContent = '1 / ' + pitchTotalReps + '회';

  // 표시
  document.getElementById('pitch-active').style.display = 'block';
  document.getElementById('pitch-done').style.display = 'none';
  document.getElementById('pitch-next-btn').style.display = 'none';
  document.getElementById('phase-pitch').style.display = 'block';

  if (pitchIv) clearInterval(pitchIv);
  setTimeout(() => runPitchCycle(0), 800);
}

function runPitchCycle(r) {
  if (r >= pitchTotalReps) {
    if (pitchIv) { clearInterval(pitchIv); pitchIv = null; }
    document.getElementById('pitch-active').style.display = 'none';
    const doneMsg = {
      4: {title:'잘 했어요!', sub:'음을 부드럽게 올렸어요'},
      5: {title:'잘 했어요!', sub:'음을 편안하게 내렸어요'},
      6: {title:'잘 했어요!', sub:'목표 음에 정확하게 맞췄어요'},
    };
    const dm = doneMsg[curPitchId] || {title:'잘 했어요!', sub:'충분히 잘 했어요!'};
    document.getElementById('pitch-done-title').textContent = dm.title;
    document.getElementById('pitch-done-sub').textContent   = dm.sub;
    document.getElementById('pitch-done').style.display = 'block';
    document.getElementById('pitch-next-btn').style.display = 'block';
    spawnConfetti();
    return;
  }

  const type = curPitchId === 4 ? 'up' : curPitchId === 5 ? 'down' : 'wave';
  document.getElementById('pitch-rep').textContent = (r + 1) + ' / ' + pitchTotalReps + '회';

  // 리셋
  document.getElementById('pitch-path').setAttribute('d', '');
  const startP = getPitchPoint(0, type);
  document.getElementById('pitch-dot').setAttribute('cx', startP.x);
  document.getElementById('pitch-dot').setAttribute('cy', startP.y);
  document.getElementById('pitch-dot-pulse').setAttribute('cx', startP.x);
  document.getElementById('pitch-dot-pulse').setAttribute('cy', startP.y);
  document.getElementById('pitch-wave-fill').style.width = '0%';

  const msgs = { 4: '소리를 내면서 올려보세요', 5: '소리를 내면서 내려보세요', 6: '목표 음에 맞춰보세요' };
  document.getElementById('pitch-msg').textContent = msgs[curPitchId] || '';
  document.getElementById('pitch-msg').style.color = 'var(--t1)';

  let progress = 0;
  const startHz = curPitchId === 5 ? 280 : curPitchId === 6 ? 180 : 120;
  const endHz   = curPitchId === 5 ? 120 : curPitchId === 6 ? 180 : 280;

  pitchIv = setInterval(() => {
    progress += 0.025;
    if (progress > 1) progress = 1;

    const p = getPitchPoint(progress, type);
    document.getElementById('pitch-dot').setAttribute('cx', p.x);
    document.getElementById('pitch-dot').setAttribute('cy', p.y);
    document.getElementById('pitch-dot-pulse').setAttribute('cx', p.x);
    document.getElementById('pitch-dot-pulse').setAttribute('cy', p.y);

    // Hz 라벨 위치
    const canvas = document.getElementById('pitch-canvas');
    const svgRect = canvas.getBoundingClientRect();
    const scaleX = svgRect.width / 320;
    const scaleY = svgRect.height / 200;
    document.getElementById('pitch-hz').style.left = (p.x * scaleX) + 'px';
    document.getElementById('pitch-hz').style.top  = (p.y * scaleY) + 'px';

    // Hz 값 시뮬레이션
    let hz;
    if (curPitchId === 6) {
      hz = Math.round(180 + Math.sin(progress * Math.PI * 3) * 60);
    } else {
      hz = Math.round(startHz + (endHz - startHz) * progress);
    }
    document.getElementById('pitch-hz').textContent = hz + ' Hz';

    // 진행 경로 그리기
    let pathD = '';
    for (let i = 0; i <= Math.round(progress * 100); i++) {
      const pp = getPitchPoint(i / 100, type);
      pathD += (i === 0 ? 'M' : 'L') + pp.x.toFixed(1) + ',' + pp.y.toFixed(1);
    }
    document.getElementById('pitch-path').setAttribute('d', pathD);

    // 진행 바
    document.getElementById('pitch-wave-fill').style.width = (progress * 100) + '%';

    // 단계별 격려
    if (progress > 0.3 && progress < 0.6) {
      document.getElementById('pitch-msg').textContent = '좋아요!';
      document.getElementById('pitch-msg').style.color = 'var(--primary)';
    } else if (progress >= 0.6 && progress < 0.9) {
      document.getElementById('pitch-msg').textContent = '조금만 더!';
    }

    // 완료
    if (progress >= 1) {
      clearInterval(pitchIv); pitchIv = null;
      document.getElementById('pitch-dot').style.fill = '#16A34A';
      document.getElementById('pitch-dot-pulse').style.fill = '#16A34A';
      document.getElementById('pitch-path').style.stroke = '#16A34A';
      document.getElementById('pitch-hz').style.background = '#16A34A';
      const arrow = document.getElementById('pitch-hz');
      arrow.style.setProperty('border-top-color', '#16A34A');

      const doneTexts = { 4: '여기까지 올렸어요!', 5: '여기까지 내렸어요!', 6: '정확하게 맞췄어요!' };
      document.getElementById('pitch-msg').textContent = doneTexts[curPitchId] || '잘 했어요!';
      document.getElementById('pitch-msg').style.color = '#16A34A';

      setTimeout(() => {
        // 리셋 색상
        document.getElementById('pitch-dot').style.fill = '';
        document.getElementById('pitch-dot-pulse').style.fill = '';
        document.getElementById('pitch-path').style.stroke = '';
        document.getElementById('pitch-hz').style.background = '';
        document.getElementById('pitch-msg').style.color = 'var(--t1)';
        runPitchCycle(r + 1);
      }, 1500);
    }
  }, 150);
}

function continuePitch() {
  document.getElementById('pitch-done').style.display = 'none';
  document.getElementById('pitch-next-btn').style.display = 'none';
  document.getElementById('pitch-active').style.display = 'block';
  setTimeout(() => runPitchCycle(0), 500);
}

function stopPitchGuide() {
  if (pitchIv) { clearInterval(pitchIv); pitchIv = null; }
}

function confirmSelf() {
  if (selfTimerIv) { clearInterval(selfTimerIv); selfTimerIv = null; }
  document.getElementById('self-btn').disabled = true;
  document.getElementById('self-status').textContent = '잘 하셨어요!';
  document.getElementById('self-pulse').style.display = 'none';
  document.getElementById('self-fb').style.display = 'flex';
  document.getElementById('self-next').style.display = 'block';
}

function nextEx() {
  stopRecTimer();
  const c = combo();
  const id = c.ids[curIdx];
  checkLevelChange(id); // 자동 레벨업/다운 체크
  curIdx++;
  if (curIdx >= c.ids.length) {
    goto('result');
  } else {
    loadExercise();
  }
}

/* ══════════════════════════════════════════════════════════
   READ TASK DATA & LOGIC
══════════════════════════════════════════════════════════ */

// 읽기 과제 대상 운동 ID → 타입 정의
const READ_EX = {
  10: 'pair',   // 대조훈련 → 최소대립쌍 카드
  13: 'tap',    // 탭핑 → 박자+문장
  14: 'slow',   // 천천히읽기 → 슬로우 리딩
  15: 'loud',   // 크게읽기 → 라우드 리딩
  11: 'stress', // 대립강세 → 강세 문장 (슬로우와 유사)
};

const READ_DATA = {
  // 슬로우/강세 리딩 문장 목록 (천천히읽기 #14, 대립강세 #11)
  slow: [
    {text:"오늘 날씨가 참 좋네요.", syl:["오","늘"," ","날","씨","가"," ","참"," ","좋","네","요","."]},
    {text:"사과를 먹었습니다.", syl:["사","과","를"," ","먹","었","습","니","다","."]},
    {text:"병원에 가야 합니다.", syl:["병","원","에"," ","가","야"," ","합","니","다","."]},
    {text:"천천히 말해 주세요.", syl:["천","천","히"," ","말","해"," ","주","세","요","."]},
    {text:"잘 하고 있어요.", syl:["잘"," ","하","고"," ","있","어","요","."]},
  ],
  // 라우드리딩 문장 목록 (#15)
  loud: [
    {text:"오늘도 열심히 해봐요!"},
    {text:"크게 말하면 더 잘 들려요!"},
    {text:"힘차게 소리 내 보세요!"},
    {text:"목소리가 점점 커지고 있어요!"},
    {text:"잘 하고 있습니다!"},
  ],
  // 대조훈련 최소대립쌍 (#10)
  pair: [
    {a:"발",  b:"팔",  sa:"[bal]",  sb:"[phal]"},
    {a:"달",  b:"탈",  sa:"[dal]",  sb:"[thal]"},
    {a:"불",  b:"풀",  sa:"[bul]",  sb:"[phul]"},
    {a:"바",  b:"파",  sa:"[ba]",   sb:"[pha]"},
    {a:"도",  b:"토",  sa:"[do]",   sb:"[tho]"},
    {a:"가",  b:"카",  sa:"[ga]",   sb:"[kha]"},
    {a:"지",  b:"치",  sa:"[ji]",   sb:"[chi]"},
    {a:"배",  b:"패",  sa:"[bae]",  sb:"[phae]"},
  ],
  // 탭핑 문장 (#13)
  tap: [
    {text:"사과를 먹었습니다.", beats:9},
    {text:"오늘 날씨가 좋아요.", beats:9},
    {text:"병원에 갑니다.", beats:7},
    {text:"천천히 읽어요.", beats:7},
    {text:"잘 하고 있어요.", beats:8},
  ],
  // 대립강세 (#11)
  stress: [
    {text:"나는 사과를 먹었다.", variants:["나는","사과를","먹었다"], cur:0},
    {text:"오늘 병원에 갔다.", variants:["오늘","병원에","갔다"], cur:0},
    {text:"천천히 크게 말해요.", variants:["천천히","크게","말해요"], cur:0},
  ],
};

let readType = 'slow';
let readIdx  = 0;      // 현재 단어/문장 인덱스
let readList = [];     // 현재 과제 항목 배열
let sylIdx   = -1;     // 슬로우리딩 음절 인덱스
let sylIv    = null;
let loudIv   = null;
let tapIv    = null;
let tapBeat  = 0;
let sttIv    = null;

function startReadTask(id) {
  stopReadTimers();
  readType = READ_EX[id];
  readIdx  = 0;

  // 배지 색상/텍스트
  const badge = document.getElementById('read-type-badge');
  const badgeMap = {
    slow:   ['rtb-slow', '슬로우 리딩'],
    loud:   ['rtb-loud', '라우드 리딩'],
    pair:   ['rtb-pair', '대조훈련 (최소대립쌍)'],
    tap:    ['rtb-tap',  '탭핑 리딩'],
    stress: ['rtb-slow', '대립강세 리딩'],
  };
  badge.className = 'read-type-badge ' + badgeMap[readType][0];
  badge.textContent = badgeMap[readType][1];

  // 영역 전부 숨기고 해당 타입만 표시
  ['sent-area','loud-area','pair-area','tap-area'].forEach(id2 =>
    document.getElementById(id2).style.display = 'none');

  if (readType === 'slow' || readType === 'stress') {
    readList = READ_DATA[readType === 'stress' ? 'stress' : 'slow'];
    document.getElementById('sent-area').style.display = 'block';
    loadSentence();
    startSylTimer();
  } else if (readType === 'loud') {
    readList = READ_DATA.loud;
    document.getElementById('sent-area').style.display = 'block';
    document.getElementById('loud-area').style.display = 'block';
    loadSentence();
    startLoudTimer();
  } else if (readType === 'pair') {
    readList = READ_DATA.pair;
    document.getElementById('pair-area').style.display = 'block';
    loadPair();
  } else if (readType === 'tap') {
    readList = READ_DATA.tap;
    document.getElementById('tap-area').style.display = 'block';
    loadTap();
    startTapTimer();
  }

  document.getElementById('read-fb').className = 'fb-bar2 warn';
  document.getElementById('read-fb').textContent = '읽으면 STT가 자동으로 인식해요';
  document.getElementById('read-stt').textContent = '—';
  document.getElementById('phase-b-read').style.display = 'block';

  // STT 시뮬
  startSttTimer();
}

function loadSentence() {
  const item = readList[readIdx];
  document.getElementById('sent-num').textContent =
    '문장 ' + (readIdx+1) + ' / ' + readList.length;

  if (readType === 'stress') {
    // 강세 과제: 강조 단어 표시
    const v = item.variants[item.cur % item.variants.length];
    const highlighted = item.text.replace(v, `<span style="color:var(--primary);font-weight:900;text-decoration:underline;">${v}</span>`);
    document.getElementById('sent-text').innerHTML =
      `<span style="font-size:13px;color:var(--t3);display:block;margin-bottom:6px;">강조: "${v}"</span>` + highlighted;
  } else {
    // 슬로우/라우드: 음절 하이라이트 span 생성
    if (item.syl) {
      const spans = item.syl.map((s, i) =>
        `<span class="syl" id="syl-${i}">${s}</span>`).join('');
      document.getElementById('sent-text').innerHTML = spans;
    } else {
      document.getElementById('sent-text').textContent = item.text;
    }
  }
}

function loadPair() {
  const item = readList[readIdx];
  document.getElementById('pair-num').textContent = '쌍 ' + (readIdx+1) + ' / ' + readList.length;
  document.getElementById('pair-a-word').textContent = item.a;
  document.getElementById('pair-b-word').textContent = item.b;
  document.getElementById('pair-a-sub').textContent  = item.sa;
  document.getElementById('pair-b-sub').textContent  = item.sb;
  document.getElementById('pair-a').classList.remove('active');
  document.getElementById('pair-b').classList.remove('active');
  document.getElementById('pair-stt').style.display = 'none';
}

function selectPair(which) {
  document.getElementById('pair-a').classList.toggle('active', which === 'a');
  document.getElementById('pair-b').classList.toggle('active', which === 'b');
  const item = readList[readIdx];
  const correct = which === 'a' ? item.a : item.b;
  document.getElementById('pair-stt').style.display = 'flex';
  document.getElementById('pair-stt-val').textContent = correct + ' — 정확';
  document.getElementById('pair-stt-val').style.color = 'var(--green)';
  document.getElementById('read-fb').className = 'fb-bar2 good';
  document.getElementById('read-fb').textContent = '정확하게 구별했어요!';
}

function loadTap() {
  const item = readList[readIdx];
  document.getElementById('tap-sent').textContent = item.text;
  // 박자 점 생성
  let dots = '';
  for (let i = 0; i < item.beats; i++) {
    dots += `<div class="tap-dot" id="td-${i}"></div>`;
  }
  document.getElementById('tap-beats').innerHTML = dots;
  tapBeat = 0;
}

/* 슬로우 리딩 음절 하이라이트 타이머 */
function startSylTimer() {
  if (sylIv) clearInterval(sylIv);
  sylIdx = -1;
  const item = readList[readIdx];
  if (!item.syl) return;
  sylIv = setInterval(() => {
    // 이전 하이라이트 제거
    if (sylIdx >= 0) {
      const prev = document.getElementById('syl-' + sylIdx);
      if (prev) prev.classList.remove('cur');
    }
    sylIdx++;
    if (sylIdx >= item.syl.length) {
      clearInterval(sylIv); sylIv = null;
      document.getElementById('read-fb').className = 'fb-bar2 good';
      document.getElementById('read-fb').textContent = '잘 읽었어요! 다음 문장으로 이동하세요';
      return;
    }
    const cur = document.getElementById('syl-' + sylIdx);
    if (cur) cur.classList.add('cur');
  }, 450); // 음절당 0.45초 페이스
}

/* 라우드 리딩 dB 애니메이션 */
function startLoudTimer() {
  if (loudIv) clearInterval(loudIv);
  let db = 52;
  loudIv = setInterval(() => {
    db += (Math.random() - 0.3) * 8;
    db = Math.max(45, Math.min(85, db));
    document.getElementById('loud-db').textContent = Math.round(db);
    const pct = ((db - 45) / 40) * 100;
    document.getElementById('loud-db-fill').style.width = pct + '%';
    if (db >= 70) {
      document.getElementById('read-fb').className = 'fb-bar2 good';
      document.getElementById('read-fb').textContent = '충분해요! 이 크기를 유지하세요!';
    } else {
      document.getElementById('read-fb').className = 'fb-bar2 warn';
      document.getElementById('read-fb').textContent = '조금 더 크게! 70dB 이상으로!';
    }
  }, 400);
}

/* 탭핑 박자 애니메이션 */
function startTapTimer() {
  if (tapIv) clearInterval(tapIv);
  const item = readList[readIdx];
  tapIv = setInterval(() => {
    const prev = document.getElementById('td-' + (tapBeat - 1));
    if (prev) prev.classList.remove('on');
    const cur = document.getElementById('td-' + tapBeat);
    if (cur) cur.classList.add('on');
    tapBeat++;
    if (tapBeat >= item.beats) { tapBeat = 0; }
  }, 500);
}

/* STT 시뮬 타이머 */
function startSttTimer() {
  if (sttIv) clearInterval(sttIv);
  let pct = 0;
  sttIv = setInterval(() => {
    pct = Math.min(pct + Math.random() * 12, 95);
    document.getElementById('read-stt').textContent = Math.round(pct) + '%';
    if (pct > 70) {
      document.getElementById('read-stt').style.color = 'var(--green)';
    }
  }, 800);
}

function stopReadTimers() {
  if (sylIv)  { clearInterval(sylIv);  sylIv  = null; }
  if (loudIv) { clearInterval(loudIv); loudIv = null; }
  if (tapIv)  { clearInterval(tapIv);  tapIv  = null; }
  if (sttIv)  { clearInterval(sttIv);  sttIv  = null; }
}

function readNext() {
  stopReadTimers();
  readIdx++;
  if (readIdx >= readList.length) {
    // 모든 항목 완료
    document.getElementById('read-fb').className = 'fb-bar2 good';
    document.getElementById('read-fb').textContent = '모든 항목 완료! "다음으로"를 눌러주세요';
    document.getElementById('read-nav').style.display = 'none';
    return;
  }
  if (readType === 'pair') { loadPair(); }
  else if (readType === 'tap') { loadTap(); startTapTimer(); }
  else { loadSentence(); if (readType === 'loud') startLoudTimer(); else startSylTimer(); }
  startSttTimer();
  document.getElementById('read-stt').textContent = '—';
  document.getElementById('read-stt').style.color = 'var(--primary)';
}

function readPrev() {
  if (readIdx <= 0) return;
  stopReadTimers();
  readIdx--;
  if (readType === 'pair') { loadPair(); }
  else if (readType === 'tap') { loadTap(); startTapTimer(); }
  else { loadSentence(); if (readType === 'loud') startLoudTimer(); else startSylTimer(); }
  startSttTimer();
  document.getElementById('read-stt').textContent = '—';
  document.getElementById('read-stt').style.color = 'var(--primary)';
  document.getElementById('read-nav').style.display = 'flex';
}

/* Video simulation */
function resetVid() {
  if (vidIv) { clearInterval(vidIv); vidIv = null; }
  vidSec = 0;
  document.getElementById('vid-fill').style.width = '0%';
  document.getElementById('vid-ctime').textContent = '0:00 / 0:08';
  document.getElementById('vid-btn').textContent   = '▶';
}
let stressIv = null;
function showStressDemo(show) {
  const demo = document.getElementById('stress-demo');
  const ico = document.getElementById('vid-ico');
  if (!demo) return;
  if (show) { demo.classList.add('active'); ico.style.display = 'none'; }
  else { demo.classList.remove('active'); ico.style.display = ''; resetStressHighlight(); }
}
function resetStressHighlight() {
  for (let i = 1; i <= 3; i++) {
    document.getElementById('stress-' + i).classList.remove('highlight');
    document.getElementById('stress-tag-' + i).style.opacity = '0';
  }
}
function cycleStress() {
  let idx = 0;
  stressIv = setInterval(() => {
    resetStressHighlight();
    const cur = (idx % 3) + 1;
    document.getElementById('stress-' + cur).classList.add('highlight');
    document.getElementById('stress-tag-' + cur).style.opacity = '1';
    idx++;
  }, 2600);
  // trigger first immediately
  document.getElementById('stress-1').classList.add('highlight');
  document.getElementById('stress-tag-1').style.opacity = '1';
}
function stopStressCycle() {
  if (stressIv) { clearInterval(stressIv); stressIv = null; }
}

function toggleTip() {
  const body = document.getElementById('tip-body');
  const arrow = document.getElementById('tip-arrow');
  body.classList.toggle('open');
  arrow.classList.toggle('open');
}

function toggleVid() {
  const isEx11 = (document.getElementById('run-name').textContent.indexOf('대립강세') !== -1);
  if (vidIv) {
    clearInterval(vidIv); vidIv = null;
    document.getElementById('vid-btn').textContent = '▶';
    if (isEx11) stopStressCycle();
    return;
  }
  document.getElementById('vid-btn').textContent = '⏸';
  if (isEx11) { showStressDemo(true); cycleStress(); }
  vidIv = setInterval(() => {
    vidSec += 0.3;
    const pct = (vidSec / 8) * 100;
    document.getElementById('vid-fill').style.width = Math.min(pct, 100) + '%';
    const s = Math.min(Math.floor(vidSec), 8);
    document.getElementById('vid-ctime').textContent = `0:0${s} / 0:08`;
    if (vidSec >= 8) {
      clearInterval(vidIv); vidIv = null; vidSec = 0;
      document.getElementById('vid-btn').textContent = '▶';
      document.getElementById('vid-fill').style.width = '100%';
      document.getElementById('vid-ctime').textContent = '0:08 / 0:08';
      if (isEx11) stopStressCycle();
    }
  }, 300);
}
function replayVid() {
  const isEx11 = (document.getElementById('run-name').textContent.indexOf('대립강세') !== -1);
  if (isEx11) { stopStressCycle(); showStressDemo(false); }
  resetVid(); setTimeout(toggleVid, 100);
}

/* Record simulation */
// 운동별 맞춤 격려 메시지
const VOICE_FB = {
  3:  '소리가 점점 안정되고 있어요!',
  4:  '음이 부드럽게 올라가고 있어요!',
  5:  '음이 편안하게 내려오고 있어요!',
  6:  '목표 음에 점점 가까워지고 있어요!',
  7:  '목소리가 힘차게 나오고 있어요!',
  8:  '성대가 확실하게 닫히고 있어요!',
  16: '점점 빨라지고 있어요!',
};

// 운동별 목표 달성 축하 메시지
const VOICE_DONE_MSG = {
  3:  {title:'잘 했어요!', sub:'소리를 안정적으로 유지했어요'},
  4:  {title:'잘 했어요!', sub:'음을 부드럽게 올렸어요'},
  5:  {title:'잘 했어요!', sub:'음을 편안하게 내렸어요'},
  6:  {title:'잘 했어요!', sub:'목표 음에 정확하게 맞췄어요'},
  7:  {title:'잘 했어요!', sub:'힘찬 목소리가 나왔어요'},
  8:  {title:'잘 했어요!', sub:'성대를 확실하게 닫았어요'},
  16: {title:'잘 했어요!', sub:'빠르고 정확하게 반복했어요'},
};

// 단계별 격려 (진행률 기준)
const RING_MILESTONES = [
  {at: 25, msg: '좋아요!'},
  {at: 50, msg: '잘 하고 있어요!'},
  {at: 75, msg: '조금만 더!'},
];

let voiceGoalReached = false;
let curVoiceId = null;
let curVoiceM  = null;

function startRecTimer(id, m) {
  let t = 0;
  voiceGoalReached = false;
  curVoiceId = id;
  curVoiceM  = m;
  const ringFill = document.getElementById('ring-fill');
  const ringVal  = document.getElementById('ring-val');
  const ringMsg  = document.getElementById('ring-msg');
  const CIRCUMFERENCE = 553; // 2 * π * 88
  let lastMilestone = -1;

  recIv = setInterval(() => {
    t += 0.5;
    let val, pct;
    switch (m.mode) {
      case 'time':  val = t;                              pct = (val / m.max) * 100; break;
      case 'pitch': val = Math.min(20 + t * 7, 95);       pct = (val / m.max) * 100; break;
      case 'err':   val = Math.max(35 - t * 2.5, 6);      pct = ((35 - val) / 29) * 100; break;
      case 'dB':    val = Math.min(55 + t * 2.5, 78);     pct = (val / m.max) * 100; break;
      case 'pct':   val = Math.min(30 + t * 6, 92);       pct = (val / m.max) * 100; break;
      case 'rate':  val = Math.max(180 - t * 9, 82);      pct = ((180 - val) / 80) * 100; break;
      case 'ddk':   val = Math.min(1.5 + t * 0.4, 5.5);   pct = (val / m.max) * 100; break;
      default:      val = t; pct = (val / m.max) * 100;
    }
    pct = Math.min(pct, 100);
    const disp = (m.mode === 'time' || m.mode === 'ddk') ? val.toFixed(1) : Math.round(val);
    ringVal.textContent = disp;

    // 원형 프로그레스 업데이트
    const offset = CIRCUMFERENCE - (pct / 100) * CIRCUMFERENCE;
    ringFill.style.strokeDashoffset = offset;

    // 색상 변화 (진행에 따라)
    if (pct >= 100) {
      ringFill.style.stroke = '#16A34A'; // 초록
    } else if (pct >= 70) {
      ringFill.style.stroke = '#3B82F6'; // 진한 파랑
    }

    // 단계별 격려 메시지
    for (let i = 0; i < RING_MILESTONES.length; i++) {
      if (pct >= RING_MILESTONES[i].at && lastMilestone < i) {
        lastMilestone = i;
        ringMsg.textContent = RING_MILESTONES[i].msg;
        ringMsg.style.color = 'var(--primary)';
      }
    }

    // 목표 달성!
    if (pct >= 100 && !voiceGoalReached) {
      voiceGoalReached = true;
      clearInterval(recIv); recIv = null;

      // 약간의 딜레이 후 축하 화면
      setTimeout(() => {
        document.getElementById('voice-active').style.display = 'none';
        const done = VOICE_DONE_MSG[id] || {title:'잘 했어요!', sub:'충분히 잘 해냈어요!'};
        document.getElementById('goal-done-title').textContent = done.title;
        document.getElementById('goal-done-sub').textContent   = done.sub;
        document.getElementById('voice-done').style.display    = 'block';
        document.getElementById('voice-next-btn').style.display = 'block';
        spawnConfetti();
      }, 600);
    }
  }, 500);
}

function spawnConfetti() {
  // 기존 컨테이너 제거
  const old = document.getElementById('confetti-fx');
  if (old) old.remove();

  const wrap = document.createElement('div');
  wrap.id = 'confetti-fx';
  wrap.className = 'confetti-container';
  document.body.appendChild(wrap);

  const colors = ['#3B5FE8','#F59E0B','#16A34A','#EF4444','#8B5CF6','#EC4899','#06B6D4','#FF6B35'];
  const cx = window.innerWidth / 2;
  const cy = window.innerHeight * 0.35;

  for (let i = 0; i < 50; i++) {
    const c = document.createElement('div');
    c.className = 'confetti';
    c.style.left = cx + 'px';
    c.style.top = cy + 'px';
    c.style.background = colors[Math.floor(Math.random() * colors.length)];

    // 방사형으로 퍼지기
    const angle = (Math.PI * 2 * i) / 50 + (Math.random() - 0.5) * 0.5;
    const dist = 80 + Math.random() * 160;
    const tx = Math.cos(angle) * dist;
    const ty = Math.sin(angle) * dist + 40 + Math.random() * 80; // 아래로 떨어지는 효과
    c.style.setProperty('--tx', tx + 'px');
    c.style.setProperty('--ty', ty + 'px');
    c.style.animationDelay = (Math.random() * 0.3) + 's';
    c.style.animationDuration = (1.5 + Math.random() * 1.2) + 's';
    wrap.appendChild(c);
  }

  // 3초 후 제거
  setTimeout(() => wrap.remove(), 4000);
}

function continueVoice() {
  // "한 번 더 해볼래요?" → 다시 시작
  document.getElementById('voice-done').style.display   = 'none';
  document.getElementById('voice-next-btn').style.display = 'none';
  document.getElementById('voice-active').style.display = 'block';
  document.getElementById('ring-fill').style.strokeDashoffset = '553';
  document.getElementById('ring-fill').style.stroke = 'var(--primary)';
  document.getElementById('ring-val').textContent = '0.0';
  document.getElementById('ring-msg').textContent = '다시 해볼까요!';
  document.getElementById('ring-msg').style.color = 'var(--t1)';
  if (curVoiceM) startRecTimer(curVoiceId, curVoiceM);
}
function stopRecTimer() {
  if (recIv)  { clearInterval(recIv);  recIv  = null; }
  if (vidIv)  { clearInterval(vidIv);  vidIv  = null; }
  if (rppgIv) { clearInterval(rppgIv); rppgIv = null; }
  if (bpmIv)  { clearInterval(bpmIv);  bpmIv  = null; }
  stopReadTimers();
  stopBreathGuide();
  stopPitchGuide();
  document.getElementById('read-nav').style.display = 'flex';
}

/* ══════════════════════════════════════════════════════════
   RESULT RENDER
══════════════════════════════════════════════════════════ */
function renderResult() {
  const c = combo();
  document.getElementById('rh-sub').textContent = '총 ' + c.dur + ' · ' + c.ids.length + '가지 운동 완료';
  document.getElementById('rs-done').textContent = c.ids.length + '/' + c.ids.length;
  let html = '';
  c.results.forEach(r => {
    html += `<div class="res-ex-row">
      <div class="rer-b" style="flex:1;">
        <div class="rer-name">${r.n}</div>
        <div class="rer-met">${r.met}</div>
      </div>
      <div class="rer-done">완료</div>
    </div>`;
  });
  document.getElementById('result-list').innerHTML = html;
  document.getElementById('res-msg').innerHTML = c.resMsg;

  // 레벨 변동 요약 표시
  const lvWrap = document.getElementById('lv-changes-wrap');
  if (sessionLvChanges.length > 0) {
    let lvHtml = '';
    sessionLvChanges.forEach(ch => {
      const isUp = ch.dir === 'up';
      const msg  = isUp
        ? ch.exName + ' 난이도가 한 단계 올라갔어요!'
        : ch.exName + '은 조금 쉬운 단계로 돌아갈게요';
      lvHtml += `<div style="background:#EDEDEF;border-radius:12px;padding:14px 16px;margin-bottom:8px;">
        <div style="font-size:var(--fs-md);font-weight:600;color:#2D2D2F;">${msg}</div>
      </div>`;
    });
    lvWrap.innerHTML = lvHtml;
    lvWrap.style.display = 'block';
  } else {
    lvWrap.style.display = 'none';
  }

  updateGrowth();
}

/* ══════════════════════════════════════════════════════════
   D-DAY 골든타임
══════════════════════════════════════════════════════════ */
let STROKE_DATE = new Date('2026-01-30'); // 발병일 (설정 화면에서 업데이트됨)

/* ══════════════════════════════════════════════════════════
   SETUP SCREEN
══════════════════════════════════════════════════════════ */
(function initSetup() {
  // 태어난 해 옵션 채우기
  const sel = document.getElementById('su-year');
  if (!sel) return;
  const now = new Date().getFullYear();
  for (let y = now - 30; y >= now - 100; y--) {
    const o = document.createElement('option');
    o.value = y;
    o.textContent = y + '년  (' + (now - y) + '세)';
    sel.appendChild(o);
  }
  // 오늘 이후 날짜 선택 못하게
  document.getElementById('su-stroke').max = new Date().toISOString().slice(0, 10);
})();

function onStrokeChange() {
  const val = document.getElementById('su-stroke').value;
  if (!val) {
    document.getElementById('su-phase-card').style.display = 'none';
    checkSetup(); return;
  }
  const stroke  = new Date(val);
  const today   = new Date(); today.setHours(0,0,0,0);
  const elapsed = Math.floor((today - stroke) / 86400000);
  const remain  = 180 - elapsed;

  let phase, phaseColor, evalFreq, trainFreq, golden;
  if (elapsed <= 30) {
    phase = '급성기';              phaseColor = '#EF4444';
    evalFreq  = '2주마다 재평가';
    trainFreq = '매일 30~40분';
    golden    = '골든타임 ' + remain + '일 남음';
  } else if (elapsed <= 90) {
    phase = '아급성기';            phaseColor = '#F59E0B';
    evalFreq  = '4주마다 재평가';
    trainFreq = '매일 40~50분';
    golden    = '골든타임 ' + remain + '일 남음';
  } else if (elapsed <= 180) {
    phase = '만성기 (골든타임 내)'; phaseColor = '#6B7280';
    evalFreq  = '8주마다 재평가';
    trainFreq = '주 5회 30~40분';
    golden    = '골든타임 ' + remain + '일 남음';
  } else {
    phase = '유지기 (만성기)';     phaseColor = '#6B7280';
    evalFreq  = '12주마다 재평가';
    trainFreq = '주 3회 이상';
    golden    = '발병 후 ' + elapsed + '일 경과';
  }

  document.getElementById('su-phase-badge').textContent       = phase;
  document.getElementById('su-phase-badge').style.background  = phaseColor;
  document.getElementById('su-elapsed').textContent           = elapsed === 0 ? '오늘 진단' : elapsed + '일 경과';
  document.getElementById('su-eval-freq').textContent         = evalFreq;
  document.getElementById('su-train-freq').textContent        = trainFreq;
  document.getElementById('su-golden').textContent            = golden;
  document.getElementById('su-phase-card').style.display      = 'block';
  checkSetup();
}

function checkSetup() {
  const ok = document.getElementById('su-name').value.trim() &&
             document.getElementById('su-year').value &&
             document.getElementById('su-stroke').value;
  document.getElementById('su-btn').classList.toggle('disabled', !ok);
}

function completeSetup() {
  const name   = document.getElementById('su-name').value.trim();
  const year   = parseInt(document.getElementById('su-year').value);
  const stroke = document.getElementById('su-stroke').value;
  // 전역 저장
  window.patientName = name;
  window.patientAge  = new Date().getFullYear() - year;
  STROKE_DATE        = new Date(stroke);
  // 홈 화면 업데이트
  document.getElementById('home-name').textContent = '안녕하세요, ' + name + '님';
  calcDday();
  // 이음 메인 화면에 이름 표시
  const eumName = document.getElementById('eum-name');
  if (eumName) eumName.textContent = name + '님, 환영합니다';
  goto('eum');
}

function calcDday() {
  const today  = new Date(); today.setHours(0,0,0,0);
  const stroke = new Date(STROKE_DATE); stroke.setHours(0,0,0,0);
  const elapsed   = Math.floor((today - stroke) / 86400000); // 경과일
  const remaining = 180 - elapsed; // 골든타임 180일 기준
  const badge = document.getElementById('dday-badge');
  if (!badge) return;
  if (remaining > 0) {
    const cls = elapsed < 30 ? 'dday-acute'
              : elapsed < 90 ? 'dday-subacute'
              : 'dday-chronic';
    badge.className = 'dday-badge ' + cls;
    badge.innerHTML = '골든타임 D-<span id="dday-num">' + remaining + '</span>';
  } else {
    badge.className = 'dday-badge dday-chronic';
    badge.innerHTML = '발병 후 <span id="dday-num">' + elapsed + '</span>일';
  }
}

/* ══════════════════════════════════════════════════════════
   STAMP 시스템 — 한국 명소 10곳
══════════════════════════════════════════════════════════ */
const STAMPS = [
  { ico:'🏯', place:'경복궁'      },
  { ico:'🗼', place:'남산타워'    },
  { ico:'🌊', place:'해운대'      },
  { ico:'🌋', place:'한라산'      },
  { ico:'🏝', place:'제주도'      },
  { ico:'🎋', place:'담양 죽녹원' },
  { ico:'🏔', place:'설악산'      },
  { ico:'⛩', place:'불국사'      },
  { ico:'🌸', place:'진해 벚꽃길' },
  { ico:'🎑', place:'안동 하회마을' },
];

function showKakaoPreview() {
  const c = combo();
  const days = 13;
  const stages = [
    {max:3,  txt:'씨앗을 심었어요', ico:''},
    {max:7,  txt:'싹이 트기 시작했어요', ico:''},
    {max:14, txt:'새싹이 자라고 있어요', ico:''},
    {max:30, txt:'꽃봉오리가 맺혔어요', ico:''},
    {max:999,txt:'활짝 피었어요!', ico:''},
  ];
  const st = stages.find(s => days <= s.max);
  document.getElementById('kp-days').textContent = days + '일째 꾸준히 하고 있어요.';
  document.getElementById('kp-done').textContent = '오늘도 ' + c.ids.length + '가지 운동을 마쳤어요!';
  document.getElementById('kp-growth-txt').textContent = st.txt;
  document.getElementById('kp-growth-ico').textContent = st.ico;
  document.getElementById('kakao-overlay').style.display = 'flex';
}

function closeKakaoPreview() {
  document.getElementById('kakao-overlay').style.display = 'none';
}

function selectMood(el) {
  document.querySelectorAll('.rm-item').forEach(i => i.classList.remove('selected'));
  el.classList.add('selected');
}

function updateGrowth() {
  // 연속 일수에 따른 단계 (프로토타입: 디버그 바에서 변경 가능)
  const days = 13; // TODO: 실제 앱에서는 저장된 연속 일수
  let stage, stageName, bgGrad, photoFilter, plants;

  if (days <= 3) {
    stage = 0; stageName = '씨앗을 심었어요';
    bgGrad = 'linear-gradient(180deg, #D4D4D8 0%, #A1A1AA 100%)';
    photoFilter = 'brightness(0.82) saturate(0.5)';
    plants = [{h:8,color:'#8B9B6E',flower:false}];
  } else if (days <= 7) {
    stage = 1; stageName = '싹이 트기 시작했어요';
    bgGrad = 'linear-gradient(180deg, #BCC5CE 0%, #94A89A 100%)';
    photoFilter = 'brightness(0.88) saturate(0.65)';
    plants = [{h:18,color:'#7CB86A',flower:false},{h:12,color:'#8BC37A',flower:false}];
  } else if (days <= 14) {
    stage = 2; stageName = '새싹이 자라고 있어요';
    bgGrad = 'linear-gradient(180deg, #B6D4E8 0%, #7CB86A 100%)';
    photoFilter = 'brightness(0.93) saturate(0.8)';
    plants = [{h:30,color:'#6B9B5E',flower:false,leaf:true},{h:22,color:'#7CB86A',flower:false,leaf:true},{h:16,color:'#8BC37A',flower:false}];
  } else if (days <= 30) {
    stage = 3; stageName = '꽃봉오리가 맺혔어요';
    bgGrad = 'linear-gradient(180deg, #87CEEB 0%, #5EA94E 100%)';
    photoFilter = 'brightness(0.97) saturate(0.9)';
    plants = [{h:40,color:'#5A8F4E',flower:'#F9C74F',leaf:true},{h:32,color:'#6B9B5E',flower:'#FFB3BA',leaf:true},{h:24,color:'#7CB86A',flower:false,leaf:true},{h:18,color:'#8BC37A',flower:false}];
  } else {
    stage = 4; stageName = '활짝 피었어요!';
    bgGrad = 'linear-gradient(180deg, #60B5F0 0%, #3DA33A 100%)';
    photoFilter = 'brightness(1.05) saturate(1.1)';
    plants = [{h:48,color:'#4A8040',flower:'#FF6B8A',leaf:true},{h:38,color:'#5A8F4E',flower:'#F9C74F',leaf:true},{h:44,color:'#6B9B5E',flower:'#C3A6FF',leaf:true},{h:28,color:'#7CB86A',flower:'#FFB3BA',leaf:true},{h:20,color:'#8BC37A',flower:false,leaf:true}];
  }

  document.getElementById('growth-bg').style.background = bgGrad;
  document.getElementById('growth-photo').style.filter = photoFilter;
  document.getElementById('growth-day').textContent = days + '일째 함께하고 있어요';
  document.getElementById('growth-stage').textContent = stageName;

  // 식물 렌더링
  let plantsHtml = '';
  plants.forEach((p, i) => {
    const left = 30 + i * 28;
    plantsHtml += `<div style="position:absolute;bottom:0;left:${left}px;display:flex;flex-direction:column;align-items:center;">`;
    if (p.flower) {
      plantsHtml += `<div style="width:14px;height:14px;border-radius:50%;background:${p.flower};box-shadow:0 0 6px ${p.flower}80;margin-bottom:-2px;"></div>`;
    }
    if (p.leaf) {
      plantsHtml += `<div style="width:12px;height:8px;border-radius:50% 0;background:${p.color};opacity:.7;transform:rotate(-30deg);margin-bottom:-3px;margin-left:-8px;"></div>`;
    }
    plantsHtml += `<div style="width:3px;height:${p.h}px;border-radius:2px;background:${p.color};"></div>`;
    plantsHtml += `</div>`;
  });
  document.getElementById('growth-plants').innerHTML = plantsHtml;

  // 애니메이션 재실행
  const scene = document.getElementById('growth-scene');
  if (scene) { scene.style.animation='none'; scene.offsetHeight; scene.style.animation=''; }
}

// ── 페이지 초기화 ──
calcDday();
