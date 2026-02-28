"""
config.py — 전역 설정 및 환경변수 관리
"""
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# ── OBS WebSocket ──
OBS_HOST = os.getenv("OBS_HOST", "localhost")
OBS_PORT = int(os.getenv("OBS_PORT", "4455"))
OBS_PASSWORD = os.getenv("OBS_PASSWORD", "")

# ── Gemini API ──
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"

# ── STT (Faster-Whisper) ──
STT_MODEL_SIZE = "small"
STT_DEVICE = "cpu"
STT_COMPUTE_TYPE = "int8"

# ── 호출어 / 종료어 ──
WAKE_WORDS = [
    "짭스", "잡스", "찹쓰", "짭쓰", "쨥스", "집스",
    "헤이짭스", "헤이 짭스", "헤이잡스", "헤이 잡스",
    "페이집스", "헤이 찹쓰", "에이집스", "헤이 짭쓰", "헤이 짭",
    "헤이 쨥스", "해이 짭스",
]
TERMINATE_WORDS = ["종료", "꺼 줘", "꺼줘", "그만", "종종", "종료해", "시스템 종료", "시스템종료"]

# ── TTS ──
TTS_VOICE = "ko-KR-SunHiNeural"
TTS_RATE = "+25%"

# ── 사운드 파일 경로 ──
SOUND_DIR = os.path.join(os.path.dirname(__file__), "sound")
SOUND_WAKE = os.path.join(SOUND_DIR, "wake_up.mp3")
SOUND_START = os.path.join(SOUND_DIR, "stream_start.mp3")
SOUND_STOP = os.path.join(SOUND_DIR, "stream_stop.mp3")

# ── OBS 미러링 ──
OBS_MIRROR_WIDTH = 1280
OBS_MIRROR_HEIGHT = 720
OBS_MIRROR_QUALITY = 70
OBS_MIRROR_FPS = 10  # 초당 프레임 수

# ── UI 테마 색상 (네온 다크 모드) ──
THEME = {
    "bg_primary": "#0f0f1a",
    "bg_secondary": "#1a1a2e",
    "bg_glass": "rgba(26, 26, 46, 180)",
    "accent_cyan": "#00f5ff",
    "accent_magenta": "#ff006e",
    "accent_green": "#00ff88",
    "accent_yellow": "#ffbe0b",
    "text_primary": "#ffffff",
    "text_secondary": "#8892b0",
    "border_glow": "#00f5ff",
}

# 타겟별 색상 팔레트 (순환 사용)
TARGET_COLORS = [
    "#00f5ff",  # 시안
    "#ff006e",  # 마젠타
    "#00ff88",  # 그린
    "#ffbe0b",  # 옐로우
    "#8b5cf6",  # 퍼플
    "#ff6b35",  # 오렌지
]
