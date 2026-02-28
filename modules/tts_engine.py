"""
tts_engine.py — Edge TTS 기반 음성 합성 + 효과음 재생
기존 pre_test/08_edge_tts_test.py 로직을 클래스로 모듈화
"""
import os
import time
import asyncio
import threading
import edge_tts
import pygame

from config import TTS_VOICE, TTS_RATE

# pygame 지원 메시지 숨기기
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

# 임시 오디오 저장 폴더
AUDIO_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp_audio")
os.makedirs(AUDIO_DIR, exist_ok=True)


class TTSEngine:
    """Edge TTS를 사용한 고품질 한국어 음성 합성 엔진"""

    def __init__(self):
        self._mixer_initialized = False
        self._init_mixer()

    def _init_mixer(self):
        """pygame mixer 초기화"""
        if not self._mixer_initialized:
            try:
                pygame.mixer.init()
                self._mixer_initialized = True
            except Exception as e:
                print(f"[TTS] pygame mixer 초기화 실패: {e}")

    def play_sound(self, file_path):
        """효과음 파일을 동기적으로 재생합니다."""
        if not os.path.exists(file_path):
            print(f"[TTS] 오디오 파일 없음: {file_path}")
            return
        try:
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.05)
        except Exception as e:
            print(f"[TTS] 효과음 재생 실패: {e}")

    def play_sound_async(self, file_path):
        """효과음을 별도 스레드에서 재생합니다 (UI 블로킹 방지)."""
        t = threading.Thread(target=self.play_sound, args=(file_path,), daemon=True)
        t.start()

    async def _generate_speech(self, text, voice=None, rate=None):
        """Edge TTS를 사용하여 음성 파일을 생성합니다."""
        voice = voice or TTS_VOICE
        rate = rate or TTS_RATE

        timestamp = int(time.time() * 1000)
        temp_file = os.path.join(AUDIO_DIR, f"tts_{timestamp}.mp3")

        communicate = edge_tts.Communicate(text, voice, rate=rate)
        await communicate.save(temp_file)

        return temp_file

    def speak(self, text):
        """텍스트를 음성으로 합성하고 재생합니다 (동기)."""
        try:
            temp_file = asyncio.run(self._generate_speech(text))
            if os.path.exists(temp_file):
                pygame.mixer.music.load(temp_file)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.05)
                pygame.mixer.music.unload()
        except Exception as e:
            print(f"[TTS] 음성 합성 실패: {e}")

    def speak_async(self, text):
        """텍스트를 별도 스레드에서 음성 합성 + 재생합니다."""
        t = threading.Thread(target=self.speak, args=(text,), daemon=True)
        t.start()
