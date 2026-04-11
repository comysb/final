"""
STEP 1: 데이터 매핑
xlsx 3개 시트(아/이/우) ↔ wav 파일 경로 연결
출력: results/session_mapping.csv
"""
import os
import pandas as pd
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.config import *


def load_mapping(verbose=True):
    """
    xlsx 3개 시트에서 각 모음별 레이블을 읽고
    (화자, 세션) 단위로 통합 → 누락 모음은 path=None 처리.

    Returns
    -------
    df : pd.DataFrame
        columns: UID, speaker_id, 장애정도, path_아, path_이, path_우
    """
    SHEET_INFO = {
        "아": ("1_연장발성_아", DIR_A, "001"),
        "이": ("7_연장발성_이", DIR_I, "007"),
        "우": ("8_연장발성_우", DIR_U, "008"),
    }

    # ── 각 시트에서 (speaker, session) → label 매핑 + 파일 경로
    vowel_maps = {}   # {"아": {(spk, sess): {"label": int, "path": str}}}

    for vowel, (sheet_name, folder, task) in SHEET_INFO.items():
        df_sheet = pd.read_excel(XLSX_PATH, sheet_name=sheet_name)
        df_sheet = df_sheet[["UID", "화자 ID", "회차", "장애 정도"]].dropna(subset=["UID"])
        df_sheet.columns = ["UID", "화자ID", "회차", "장애정도"]

        vmap = {}
        for _, row in df_sheet.iterrows():
            spk   = str(row["화자ID"]).strip()
            sess  = str(int(row["회차"])).strip()
            label = int(row["장애정도"])
            fname = f"{spk}_{task}_{sess}.wav"
            fpath = os.path.join(folder, fname)
            vmap[(spk, sess)] = {
                "label": label,
                "path":  fpath if os.path.isfile(fpath) else None,
            }
        vowel_maps[vowel] = vmap

    # ── 모든 (speaker, session) 합집합
    all_keys = set()
    for vmap in vowel_maps.values():
        all_keys.update(vmap.keys())

    # ── 세션별 통합
    records = []
    for (spk, sess) in sorted(all_keys):
        # 레이블 수집 (여러 시트에서 같은 화자 → 동일해야 하지만 최빈값 사용)
        labels = [vowel_maps[v][(spk, sess)]["label"]
                  for v in ["아", "이", "우"]
                  if (spk, sess) in vowel_maps[v]]
        label = max(set(labels), key=labels.count)  # 최빈값

        # 파일 경로 (없으면 None)
        path_a = vowel_maps["아"].get((spk, sess), {}).get("path")
        path_i = vowel_maps["이"].get((spk, sess), {}).get("path")
        path_u = vowel_maps["우"].get((spk, sess), {}).get("path")

        # 존재하는 모음 수
        n_present = sum(p is not None for p in [path_a, path_i, path_u])
        if n_present == 0:
            continue  # 실제 파일 없으면 제외

        records.append({
            "UID":       f"{spk}_{sess}",
            "speaker_id": spk,
            "장애정도":  label,
            "path_아":   path_a,
            "path_이":   path_i,
            "path_우":   path_u,
            "n_vowels":  n_present,
        })

    df = pd.DataFrame(records)

    if verbose:
        from collections import Counter
        print(f"\n{'='*55}")
        print(f"[매핑 결과 (새 xlsx 3시트 기준)]")
        print(f"  총 세션: {len(df)} (화자:{df['speaker_id'].nunique()}명)")
        print(f"\n  모음 완성도별:")
        for n in [3, 2, 1]:
            cnt = (df["n_vowels"] == n).sum()
            print(f"    {n}모음 완비: {cnt}개")
        print(f"\n  클래스 분포:")
        for cls, name in CLASS_NAMES.items():
            cnt = (df["장애정도"] == cls).sum()
            print(f"    {cls}({name}): {cnt}세션")
        print(f"{'='*55}\n")

    return df


if __name__ == "__main__":
    df = load_mapping(verbose=True)
    df.to_csv(MAPPING_CSV, index=False, encoding="utf-8-sig")
    print(f"저장: {MAPPING_CSV}")
