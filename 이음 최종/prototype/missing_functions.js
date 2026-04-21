// ====== MISSING FUNCTIONS FROM BACKUP ======

// --- applySevResultUI ---
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

// --- buildAndGotoTodayTraining ---
function buildAndGotoTodayTraining() {
  // 1. 마지막 예측 결과에서 피처 수집
  const pred = window._lastPredictFeatures || {};

  const mpt_avg   = (pred.MPT_아 || pred.MPT_이 || pred.MPT_우)
                    ? ((pred.MPT_아||0) + (pred.MPT_이||0) + (pred.MPT_우||0)) / 3
                    : null;
  const energy    = pred.mean_energy_db || null;
  const ddk       = pred.ddk_rate || null;
  const jitter    = pred.jitter || pred.jitter_local_이 || null;
  const crr       = pred.crr || null;

  // 2. 어떤 패턴이 문제인지 감지
  const triggeredExIds = new Set();

  function pickRandom(arr) {
    return arr[Math.floor(Math.random() * arr.length)];
  }

  if (mpt_avg !== null && mpt_avg < THRESHOLDS.mpt.problem_below) {
    triggeredExIds.add(pickRandom(PATTERN_EXERCISES.mpt_short));
  }
  if (energy !== null && energy < THRESHOLDS.energy.problem_below) {
    triggeredExIds.add(pickRandom(PATTERN_EXERCISES.low_volume));
  }
  if (ddk !== null && ddk < THRESHOLDS.ddk.problem_below) {
    triggeredExIds.add(pickRandom(PATTERN_EXERCISES.slow_speech));
    // DDK 느리면 빠른 말도 체크 불필요, 이미 포함
  }
  if (jitter !== null && jitter > THRESHOLDS.jitter.problem_above) {
    triggeredExIds.add(pickRandom(PATTERN_EXERCISES.poor_quality));
  }
  if (crr !== null && crr < THRESHOLDS.crr.problem_below) {
    triggeredExIds.add(pickRandom(PATTERN_EXERCISES.unclear_phones));
    triggeredExIds.add(pickRandom(PATTERN_EXERCISES.unclear_overall));
  }

  // 3. 최소 6개 보장 — 부족분을 16개 전체 중 안 뽑힌 것에서 랜덤 채우기
  const allIds = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16];
  const MIN_SESSION = 6;

  if (triggeredExIds.size < MIN_SESSION) {
    const remaining = allIds.filter(id => !triggeredExIds.has(id));
    // 셔플
    for (let i = remaining.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [remaining[i], remaining[j]] = [remaining[j], remaining[i]];
    }
    const needed = MIN_SESSION - triggeredExIds.size;
    remaining.slice(0, needed).forEach(id => triggeredExIds.add(id));
  }

  // 4. 그룹 순서로 정렬 (gb → ga → gp)
  const groupOrder = { gb: 0, ga: 1, gp: 2 };
  _todayTrainingIds = [...triggeredExIds].sort((a, b) => {
    const ga = groupOrder[EX[a].g] ?? 9;
    const gb = groupOrder[EX[b].g] ?? 9;
    return ga !== gb ? ga - gb : a - b;
  });

  // 5. 화면 렌더링 후 이동
  renderTodayTraining();
  goto('today-training');
}

// --- getLevelInfo ---
function getLevelInfo(s) {
    if (s === null || s === undefined) return { label:'미측정', colorClass:'gray' };
    if (s >= 75) return { label:'양호',      colorClass:'green' };
    if (s >= 55) return { label:'경미',      colorClass:'green' }; 
    if (s >= 35) return { label:'훈련 필요', colorClass:'orange' };
    return             { label:'심각',      colorClass:'red' };
  }

// --- getMicStream ---
function getMicStream() {
  if (globalStream) return globalStream;
  try {
    globalStream = await navigator.mediaDevices.getUserMedia({ audio: true });

    // 오디오 레벨 시각화를 위한 Web Audio API 연동
    try {
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const source = audioCtx.createMediaStreamSource(globalStream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      const dataArray = new Uint8Array(analyser.frequencyBinCount);

      setInterval(() => {
        analyser.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) sum += dataArray[i];
        let avg = sum / dataArray.length;
        
        // 화면 하단 중앙이나 어딘가에 점으로 표시 (테스트용 피드백)
        let meter = document.getElementById('audio-meter');
        if (!meter) {
            meter = document.createElement('div');
            meter.id = 'audio-meter';
            meter.style.position = 'fixed';
            meter.style.bottom = '90px';
            meter.style.left = '50%';
            meter.style.transform = 'translateX(-50%)';
            meter.style.background = 'rgba(0,0,0,0.5)';
            meter.style.padding = '8px 16px';
            meter.style.borderRadius = '20px';
            meter.style.color = 'white';
            meter.style.fontSize = '12px';
            meter.style.zIndex = '9999';
            meter.style.pointerEvents = 'none';
            document.body.appendChild(meter);
        }
        meter.innerHTML = '마이크 수음: <div style="display:inline-block; width:100px; height:8px; background:#444; border-radius:4px; margin-left:8px; overflow:hidden;"><div style="width:' + Math.min(100, avg*1.5) + '%; height:100%; background:#4ade80;"></div></div>';
      }, 100);
    } catch(e) {
      console.warn("AudioContext setup failed:", e);
    }

    return globalStream;
  } catch (err) {
    console.error("Mic access denied", err);
    return null;
  }
}

// --- openTodayExSingle ---
function openTodayExSingle(id) {
  // 오늘의 훈련 세션에서 해당 운동을 combo처럼 주입하고 바로 실행
  const c = combo();
  // 임시로 _todayTrainingIds 전체를 세션으로 주입
  c._savedIds    = c.ids;
  c._savedResults = c.results;
  c.ids     = _todayTrainingIds;
  c.results = _todayTrainingIds.map(i => ({
    e: EX[i].e, n: EX[i].n, met: '완료'
  }));
  let idx = c.ids.indexOf(id);
  if (idx < 0) idx = 0;
  curIdx = idx;
  loadExercise();
  goto('run');
}

// --- pickRandom ---
function pickRandom(arr) {
    return arr[Math.floor(Math.random() * arr.length)];
  }

// --- renderDomainResult ---
function renderDomainResult() {
  const report = window._lastDomainReport || {};
  const scores = report.domain_scores || {};
  const overall = report.overall_score;

  function getLevelInfo(s) {
    if (s === null || s === undefined) return { label:'미측정', colorClass:'gray' };
    if (s >= 75) return { label:'양호',      colorClass:'green' };
    if (s >= 55) return { label:'경미',      colorClass:'green' }; 
    if (s >= 35) return { label:'훈련 필요', colorClass:'orange' };
    return             { label:'심각',      colorClass:'red' };
  }

  // 전체 점수
  const tScoreEl = document.getElementById('total-score');
  if (tScoreEl) tScoreEl.textContent = overall !== null && overall !== undefined ? Math.round(overall) : '--';
  const tStatusEl = document.getElementById('total-status');
  if (tStatusEl) {
    const oLv = getLevelInfo(overall);
    tStatusEl.textContent = oLv.label;
  }

  // 4개 영역 매핑
  const DOMAINS = [
    { key:'발성', id:'phonation' },
    { key:'호흡', id:'respiration' },
    { key:'조음', id:'articulation' },
    { key:'운율', id:'prosody' },
  ];

  const CIRCUM = 188.5; // 기존 원둘레: 2 * PI * 30

  DOMAINS.forEach(d => {
    const s = scores[d.key];
    const lv = getLevelInfo(s);
    
    // 점수 업데이트
    const scEl = document.getElementById(d.id + '-score');
    if(scEl) scEl.textContent = s !== null && s !== undefined ? Math.round(s) : '--';
    
    // 뱃지 업데이트
    const stEl = document.getElementById(d.id + '-status');
    if(stEl) {
      stEl.textContent = lv.label;
      stEl.className = 'status-badge ' + lv.colorClass;
    }
    
    // 원 차트 업데이트
    const ring = document.getElementById(d.id + '-ring');
    if(ring) {
      ring.className.baseVal = 'ring-progress ' + lv.colorClass;
      const offset = s !== null && s !== undefined ? CIRCUM - (s/100)*CIRCUM : CIRCUM;
      ring.style.strokeDashoffset = offset;
    }
  });

  // 점수 기반 권고 텍스트 생성
  const weakDomains = DOMAINS
    .filter(d => scores[d.key] !== null && scores[d.key] !== undefined)
    .sort((a,b) => scores[a.key] - scores[b.key]);
  
  if (weakDomains.length >= 2) {
    const guideMsg = document.querySelector('.wave-bg h2');
    if(guideMsg) {
       guideMsg.textContent = `현재 가장 우선적으로 개선이 필요한 영역은 ${weakDomains[0].key}과(와) ${weakDomains[1].key}입니다.`;
    }
  }

  // 레이더 차트 업데이트
  // 중심점 50,50 반경 40 
  // 조음(상 50,10), 발성(우 90,50), 운율(하 50,90), 호흡(좌 10,50)
  const rAr = scores['조음'] || 0;
  const rPh = scores['발성'] || 0;
  const rPr = scores['운율'] || 0;
  const rRe = scores['호흡'] || 0;

  const ptTop = `50,${50 - Math.min((rAr/100)*40, 40)}`;
  const ptRight = `${50 + Math.min((rPh/100)*40, 40)},50`;
  const ptBottom = `50,${50 + Math.min((rPr/100)*40, 40)}`;
  const ptLeft = `${50 - Math.min((rRe/100)*40, 40)},50`;
  const pointsStr = `${ptTop} ${ptRight} ${ptBottom} ${ptLeft}`;

  // '오늘' 데이터 폴리곤 찾아서 업데이트 (파란색)
  const todayPoly = document.querySelector('polygon[stroke="#3B5FE8"]');
  if(todayPoly) todayPoly.setAttribute('points', pointsStr);
}

// --- renderTodayTraining ---
function renderTodayTraining() {
  const ids = _todayTrainingIds;
  if (!ids.length) return;

  // 예상 시간 계산 (dur 파싱)
  let totalMin = 0;
  ids.forEach(id => {
    const d = EX[id].dur || '3분';
    const nums = d.match(/\d+/g);
    if (nums) totalMin += parseInt(nums[nums.length - 1]);
  });

  document.getElementById('tt-dur-chip').textContent = totalMin + '분이면 돼요';
  document.getElementById('tt-cnt-chip').textContent = ids.length + '가지 연습';

  const grpNames  = { gb: '숨쉬기·발성 연습', ga: '발음 연습', gp: '말하기 연습' };
  const grpColors = { gb: '#3B5FE8', ga: '#F97316', gp: '#EC4899' };
  let html = '', lastG = '';

  ids.forEach(id => {
    const ex = EX[id];
    if (ex.g !== lastG) {
      lastG = ex.g;
      html += `
      <div style="display:flex;align-items:center;gap:8px;margin:16px 0 10px;">
        <div style="width:8px;height:8px;border-radius:50%;background:${grpColors[ex.g]};"></div>
        <div style="font-size:14px;font-weight:800;color:#374151;">${grpNames[ex.g]}</div>
      </div>`;
    }
    const lv = getLvl(id);
    const lvBadge = lv ? `<span style="background:#F97316;color:#fff;font-size:10px;font-weight:700;border-radius:999px;padding:2px 8px;">Lv.${lv.lv}</span>` : '';
    html += `
    <div onclick="openTodayExSingle(${id})" style="background:#fff;border-radius:14px;padding:16px 18px;margin-bottom:10px;box-shadow:0 1px 4px rgba(0,0,0,0.06);border:1px solid #F0F0F0;display:flex;align-items:center;justify-content:space-between;cursor:pointer;">
      <div style="flex:1;">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
          <span style="font-size:14px;font-weight:800;color:#1A1A2E;">${ex.n}</span>
          ${lvBadge}
        </div>
        <div style="font-size:12px;color:#6B7280;margin-bottom:6px;">${ex.d}</div>
        <span style="background:#F3F4F6;border-radius:999px;padding:3px 10px;font-size:11px;color:#374151;font-weight:600;">${ex.dur}</span>
      </div>
      <div style="font-size:20px;color:#D1D5DB;margin-left:12px;">›</div>
    </div>`;
  });

  document.getElementById('tt-exercise-list').innerHTML = html;
}

// --- scoreLevel ---
function scoreLevel(s) {
  if (s === null || s === undefined) return { label:'미측정', color:'#9CA3AF' };
  if (s >= 75) return { label:'양호',      color:'#3B82F6' };
  if (s >= 55) return { label:'경미',      color:'#10B981' };
  if (s >= 35) return { label:'훈련 필요', color:'#F59E0B' };
  return             { label:'심각',      color:'#EF4444' };
}

// --- startSttTimer ---
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

// --- startTodayTraining ---
function startTodayTraining() {
  if (!_todayTrainingIds.length) return;
  const c = combo();
  c.ids     = _todayTrainingIds;
  c.results = _todayTrainingIds.map(i => ({
    e: EX[i].e, n: EX[i].n, met: '완료'
  }));
  curIdx = 0;
  loadExercise();
  goto('run');
}

// --- startTpRecorderWord ---
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

// --- submitToBackend ---
function submitToBackend() {
  try {
    const fd = new FormData();
    if (audioBlobs.noise) fd.append('noise_file', audioBlobs.noise, 'noise.webm');
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
       // ── 영역별 점수 저장 & 렌더 ──
       window._lastDomainReport = {
         domain_scores:  data.domain_scores  || {},
         overall_score:  data.overall_score  ?? null,
         overall_level:  data.overall_level  || '--',
       };
       // ── 문제 패턴 감지용 raw 피처 저장 ──
       const det = data.details || {};
       const pkF = (det.putterker || {}).features || {};
       const aiF = (det.vowel    || {}).features  || {};
       const wdM = (det.word     || {}).metrics   || {};
       window._lastPredictFeatures = {
         // 퍼터커
         ddk_rate:      pkF.ddk_rate,
         mean_energy_db: pkF.mean_energy_db,
         jitter:        pkF.jitter,
         // 아이우
         MPT_아:        aiF['MPT_아'],
         MPT_이:        aiF['MPT_이'],
         MPT_우:        aiF['MPT_우'],
         jitter_local_이: aiF['jitter_local_이'],
         // 단어
         crr:           wdM.crr,
         vrr:           wdM.vrr,
       };
    } else {
       applySevResultUI(0);
    }
  } catch(e) {
    console.error("Backend Error:", e);
    applySevResultUI(0);
  }
}

