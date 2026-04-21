import pandas as pd, numpy as np, joblib, json

# ── 퍼터커 percentiles ──────────────────────────────────────────
df = pd.read_csv(r'D:\퍼터커\features_emb_all.csv', encoding='utf-8-sig')
FEAT = ['f0_var_hz','f0_var_semitones','mean_energy_db','var_energy_db','max_energy_db',
        'ddk_rate','ddk_mean_dur_ms','ddk_regularity_ms','pause_rate','pause_mean_dur_ms',
        'pause_regularity_ms','intelligibility_score']

n = df[df['label']==0]; s = df[df['label']==2]
print("=== 퍼터커 정상 (p5,p50,p95) vs 중증 (p5,p50,p95) ===")
for feat in FEAT:
    if feat not in df.columns: continue
    nv = n[feat].dropna(); sv = s[feat].dropna()
    if len(nv)==0 or len(sv)==0: continue
    print(f"{feat:28s}  정상[{nv.quantile(0.05):.2f} {nv.quantile(0.50):.2f} {nv.quantile(0.95):.2f}]  "
          f"중증[{sv.quantile(0.05):.2f} {sv.quantile(0.50):.2f} {sv.quantile(0.95):.2f}]")

# ── 단어 healthy_stats ──────────────────────────────────────────
ws = joblib.load(r'D:\단어\models\healthy_stats.joblib')
print("\n=== 단어 healthy_stats (정상 mean/std) ===")
for k, v in ws.items():
    print(f"  {k:20s}: mean={v['mean']:.4f}  std={v['std']:.4f}")

# ── 아이우 F1 (best threshold row) ──────────────────────────────
df_res = pd.read_csv(r'D:\아이우\results\final_results_cascade_svm_meta_no_w2v.csv', encoding='utf-8-sig')
best = df_res.loc[df_res['Youden_J'].idxmax()]
print(f"\n=== 아이우 최적 성능 (threshold={best.iloc[0]:.2f}) ===")
print(f"  Micro Acc : {best['Micro_Acc']:.4f}")
print(f"  Youden J  : {best['Youden_J']:.4f}")
