"""Append StaticFiles mount to main.py"""
import os

APPEND_CODE = '''

# == Static File Serving (prototype directory) ==
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

PROTOTYPE_DIR = r"D:\\\\이음\\\\prototype"

@app.get("/chunk_processor.js")
def serve_chunk_processor():
    p = os.path.join(PROTOTYPE_DIR, "chunk_processor.js")
    if os.path.exists(p):
        return FileResponse(p, media_type="application/javascript")
    return FileResponse(os.path.join(r"D:\\\\이음", "chunk_processor.js"), media_type="application/javascript")

@app.get("/therapy_ui_v4.html")
def serve_frontend():
    return FileResponse(os.path.join(PROTOTYPE_DIR, "therapy_ui_v4.html"), media_type="text/html")

if os.path.isdir(PROTOTYPE_DIR):
    app.mount("/", StaticFiles(directory=PROTOTYPE_DIR, html=True), name="static")
'''

main_path = os.path.join(os.path.dirname(__file__), "main.py")

# Detect encoding
for enc in ("utf-8-sig", "utf-8", "cp949"):
    try:
        with open(main_path, "r", encoding=enc) as f:
            content = f.read()
        print(f"Read with {enc}")
        break
    except Exception as e:
        print(f"Failed {enc}: {e}")
        content = None

if content is None:
    print("Could not read main.py")
    exit(1)

# Check if already added
if "StaticFiles" in content and "serve_frontend" in content:
    print("StaticFiles already mounted, skipping.")
    exit(0)

# Remove old broken partial mounts if any
marker = "\n# == Static File Serving"
if marker in content:
    content = content[:content.index(marker)]

new_content = content.rstrip() + APPEND_CODE.replace("\\\\\\\\", "\\\\")

# Write back with same encoding
try:
    with open(main_path, "w", encoding=enc) as f:
        f.write(new_content)
    print(f"Successfully appended StaticFiles mount ({enc})")
except Exception as e:
    print(f"Write error: {e}")
