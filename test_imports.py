"""Quick import test for all modules"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

print("Testing imports...")

try:
    from config import THEME, GEMINI_API_KEY
    print("[OK] config")
except Exception as e:
    print(f"[FAIL] config: {e}")

try:
    from modules.target_manager import TargetManager
    tm = TargetManager()
    t = tm.add_target("cup", [10, 20, 100, 200])
    print(f"[OK] target_manager: {t.display_name}")
except Exception as e:
    print(f"[FAIL] target_manager: {e}")

try:
    from modules.digital_ptz import DigitalPTZ
    ptz = DigitalPTZ()
    print(f"[OK] digital_ptz: zoomed={ptz.is_zoomed}")
except Exception as e:
    print(f"[FAIL] digital_ptz: {e}")

try:
    from modules.voice_controller import VoiceController
    vc = VoiceController()
    r = vc.parse_command("종이컵 1 확대해 줘")
    print(f"[OK] voice_controller: {r}")
except Exception as e:
    print(f"[FAIL] voice_controller: {e}")

try:
    from modules.obs_capture import OBSCapture
    print("[OK] obs_capture (import only)")
except Exception as e:
    print(f"[FAIL] obs_capture: {e}")

try:
    from modules.vision_ai import VisionAI
    print("[OK] vision_ai (import only)")
except Exception as e:
    print(f"[FAIL] vision_ai: {e}")

try:
    from modules.tts_engine import TTSEngine
    print("[OK] tts_engine (import only)")
except Exception as e:
    print(f"[FAIL] tts_engine: {e}")

print("\nAll import tests complete!")
