import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r"D:\이음복사본1\backend\main.py", "rb") as f:
    content = f.read()

# Old section (bytes-exact) to replace
old = (
    b"        raw_feats = {}\r\n"
    b"\r\n"
    b"        try:\r\n"
    b"\r\n"
    b"            feat_dict = self.engine.extract_features(path_a, path_i, path_u)\r\n"
    b"\r\n"
    b"            # ndarray\xe5\xaa\x9b \xeb\xb8\x98\xeb\x95\xb6 dict \xec\x82\x8e\xea\xb9\xad\xe6\xbf\xa1 \xe8\xab\x9b\xec\x84\x91\xec\x86\x9a\xeb\xa7\x96\r\n"
    b"\r\n"
    b"            if isinstance(feat_dict, dict):\r\n"
    b"\r\n"
    b'                raw_feats = {k: round(float(v), 5) for k, v in feat_dict.items()\r\n'
    b"\r\n"
    b'                             if k not in ("UID", "speaker_id", "\xec\x98\xa3\xeb\xb8\xb7\xec\xa0\x99\xeb\xa3\x84")\r\n'
    b"\r\n"
    b"                             and v is not None and str(v) != 'nan'}\r\n"
    b"\r\n"
    b"        except Exception as e:\r\n"
    b"\r\n"
    b'            print(f"[\xeb\xb8\x98\xec\x94\xa0\xec\x8a\xa6] raw \xeb\xb5\xbe\xef\xa7\xa3 \xe7\x95\xb0\xeb\xb6\xbf\xed\x85\xa7 \xeb\x96\x8e\xeb\x99\xa3: {e}")\r\n'
)

new = (
    b"        raw_feats = {}\r\n"
    b"\r\n"
    b"        try:\r\n"
    b"\r\n"
    b"            feat_data = self.engine.extract_features(path_a, path_i, path_u)\r\n"
    b"\r\n"
    b"            import numpy as _np\r\n"
    b"\r\n"
    b"            if isinstance(feat_data, dict):\r\n"
    b"                raw_feats = {k: round(float(v), 5) for k, v in feat_data.items()\r\n"
    b'                             if k not in ("UID", "speaker_id") and v is not None and str(v) != "nan"}\r\n'
    b"\r\n"
    b"            elif isinstance(feat_data, _np.ndarray):\r\n"
    b"                # extract_features\xeb\x8a\x94 ndarray(1x112)\xeb\xa5\xbc \xeb\xb0\x98\xed\x99\x98\xed\x95\xa8 \xe2\x86\x92 feat_cols\xeb\xa1\x9c dict \xeb\xb3\x80\xed\x99\x98\r\n"
    b"                arr = feat_data.flatten()\r\n"
    b"                cols = self.engine.feat_cols if hasattr(self.engine, 'feat_cols') else []\r\n"
    b"                for _i, _col in enumerate(cols):\r\n"
    b"                    if _i < len(arr):\r\n"
    b"                        _v = float(arr[_i])\r\n"
    b"                        if _v == _v and _col not in ('UID', 'speaker_id'):\r\n"
    b"                            raw_feats[_col] = round(_v, 5)\r\n"
    b"\r\n"
    b"            print(f'[\xec\x95\x84\xec\x9d\xb4\xec\x9a\xb0] raw \xed\x94\xbc\xec\xb2\x98 {len(raw_feats)}\xea\xb0\x9c \xec\xb6\x94\xec\xb6\x9c \xec\x99\x84\xeb\xa3\x8c')\r\n"
    b"\r\n"
    b"        except Exception as e:\r\n"
    b"\r\n"
    b'            print(f"[\xec\x95\x84\xec\x9d\xb4\xec\x9a\xb0] raw \xed\x94\xbc\xec\xb2\x98 \xec\xb6\x94\xec\xb6\x9c \xec\x8b\xa4\xed\x8c\xa8: {e}")\r\n'
)

if old in content:
    new_content = content.replace(old, new, 1)
    with open(r"D:\이음복사본1\backend\main.py", "wb") as f:
        f.write(new_content)
    print("SUCCESS: main.py updated!")
else:
    print("FAIL: target section not found")
    # Debug: find position of raw_feats
    pos = content.find(b"        raw_feats = {}")
    print(f"raw_feats found at byte pos: {pos}")
    print("Context:", content[pos:pos+400])
