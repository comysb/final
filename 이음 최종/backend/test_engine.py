import sys
import os
import traceback

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("=== PutterkerEngine 로드 테스트 ===")
try:
    from main import PutterkerEngine
    e = PutterkerEngine()
    print("Putterker OK")
except Exception as ex:
    traceback.print_exc()
    print("Putterker FAILED:", ex)

print("\n=== AiiuEngine 로드 테스트 ===")
try:
    from main import AiiuEngine
    a = AiiuEngine()
    print("Aiiu OK")
except Exception as ex:
    traceback.print_exc()
    print("Aiiu FAILED:", ex)

print("\n=== WordEngine 로드 테스트 ===")
try:
    from main import WordEngine
    w = WordEngine()
    print("Word OK")
except Exception as ex:
    traceback.print_exc()
    print("Word FAILED:", ex)
