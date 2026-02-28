import os
import sys
import numpy as np
import time
import pygame
import speech_recognition as sr
from faster_whisper import WhisperModel

# 오디오 재생(효과음)을 위한 pygame 믹서 초기화
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
pygame.mixer.init()
WAKE_SOUND_PATH = os.path.join("sound", "wake_up.mp3")
START_SOUND_PATH = os.path.join("sound", "stream_start.mp3")
STOP_SOUND_PATH = os.path.join("sound", "stream_stop.mp3")

def play_audio(file_path):
    """지정된 오디오 파일을 재생합니다."""
    if os.path.exists(file_path):
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        # 효과음이 재생되는 동안 잠시 대기
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
    else:
        print(f"[경고] 오디오 파일을 찾을 수 없습니다: {file_path}")

# Windows에서 CUDA 러닝 타임 에러 방지
try:
    import site
    packages_dir = site.getsitepackages()[0]
    os.add_dll_directory(os.path.join(packages_dir, "nvidia", "cublas", "bin"))
    os.add_dll_directory(os.path.join(packages_dir, "nvidia", "cudnn", "bin"))
except Exception:
    pass

MODEL_SIZE = "small"
# 인식할 호출어 목록 (STT가 다르게 인식할 수 있으므로 비슷한 발음도 포함)
# 실제 터미널 테스트에서 확인된 오인식 발음 추가
WAKE_WORDS = [
    "헤이짭스", "헤이 짭스", "헤이잡스", "헤이 잡스", 
    "페이집스", "헤이 찹쓰", "에이집스", "헤이 짭쓰", "헤이 짭",
    "헤이 쨥스", "해이 짭스"
]
# 에이전트를 종료하기 위한 명령어 목록
TERMINATE_WORDS = ["종료", "꺼 줘", "꺼줘", "그만", "종종", "종료해", "시스템 종료", "시스템종료"]

def load_local_whisper():
    print(f"\n[설정] AI 에이전트 '{MODEL_SIZE}' 모델 (CPU) 로딩을 시작합니다...")
    model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    print(f"[SUCCESS] 모델 로드 성공! 호출어 감지를 시작합니다.\n")
    return model

def transcribe_from_memory(model, audio_data: sr.AudioData):
    try:
        raw_bytes = audio_data.get_raw_data(convert_rate=16000, convert_width=2)
        audio_np = np.frombuffer(raw_bytes, np.int16).flatten().astype(np.float32) / 32768.0
        
        # CPU 환경 최적화 및 호출어 인식률 향상을 위한 프롬프트 추가
        # initial_prompt를 주면 모델이 해당 단어들이 나올 것이라고 예상하여 오인식률이 크게 줄어듭니다.
        hint_prompt = "에이전트, 헤이짭스, 헤이 짭스, 종료, 꺼 줘, 시스템 종료, 화면 녹화 시작. "
        
        segments, info = model.transcribe(
            audio_np, 
            beam_size=1, 
            language="ko",
            condition_on_previous_text=False,
            vad_filter=True,
            initial_prompt=hint_prompt
        )
        recognized_text = "".join([segment.text + " " for segment in segments]).strip()
        return recognized_text
    except Exception as e:
        print(f"[오류] 변환 중 에러 발생: {e}")
        return ""

def is_word_detected(text, word_list):
    """텍스트 내에 특정 단어 목록 중 하나가 포함되어 있는지 확인합니다."""
    # 공백 제거 및 소문자화(영어일 경우 대비)하여 검색
    cleaned_text = text.replace(" ", "").lower()
    for word in word_list:
        if word.replace(" ", "").lower() in cleaned_text:
            return True, word
    return False, None

def run_agent():
    model = load_local_whisper()
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    print("[시스템] 주변 소음 수준을 측정합니다. 2초간 잠시 조용히 해주세요...")
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=2)
        recognizer.pause_threshold = 0.5 
        
    print("\n=======================================================")
    print(f"🤖 호출 대기 모드 진입 완료! (호출어: {', '.join(WAKE_WORDS)})")
    print("   호출어를 말씀하시면, 그 다음 나오는 짧은 문장을 '명령'으로 인식합니다.")
    print("=======================================================\n")
    
    # 준비 완료 시 시작음 재생
    play_audio(START_SOUND_PATH)

    state = "WAKE_WORD_LISTENING" # 'WAKE_WORD_LISTENING' 상시 청취 또는 'COMMAND_LISTENING' 명령 청취

    try:
        while True:
            with mic as source:
                if state == "WAKE_WORD_LISTENING":
                    print("\n💤 [대기] 호출어를 기다리는 중...")
                    # 타임아웃 없이 호출어를 상시 청취합니다 (짧은 문장 단위로 끊음)
                    # 호출어는 보통 짧으므로 phrase_time_limit를 짧게 줍니다.
                    audio_data = recognizer.listen(source, timeout=None, phrase_time_limit=5)
                    
                    text = transcribe_from_memory(model, audio_data)
                    if text:
                        print(f"   (인식됨: {text})")
                        
                        # 종료 명령 체크
                        term_detected, _ = is_word_detected(text, TERMINATE_WORDS)
                        if term_detected:
                            print("\n[시스템] '종료' 명령이 감지되었습니다. 에이전트를 안전하게 종료합니다. 👋")
                            play_audio(STOP_SOUND_PATH)
                            return
                            
                        detected, word = is_word_detected(text, WAKE_WORDS)
                        
                        if detected:
                            print(f"\n🔔 [호출됨!] '{word}' 감지 완료! 무엇을 도와드릴까요?")
                            # 알림음 재생
                            play_audio(WAKE_SOUND_PATH)
                            # 상태를 명령 청취 모드로 변경
                            state = "COMMAND_LISTENING"
                            
                elif state == "COMMAND_LISTENING":
                    print("🎧 [명령 듣는 중] ... (말씀해주세요)")
                    try:
                        # 10초 이내에 명령을 내리지 않으면 다시 대기 모드로 돌아감
                        audio_data = recognizer.listen(source, timeout=10, phrase_time_limit=15)
                        
                        start_time = time.time()
                        command_text = transcribe_from_memory(model, audio_data)
                        elapsed = time.time() - start_time
                        
                        if command_text:
                            print(f"\n=================================")
                            print(f"🎯 [최종 명령 수신] (변환: {elapsed:.2f}초)")
                            print(f"▶ {command_text}")
                            print(f"=================================\n")
                            
                            # 명령 중에도 '종료'라고 하면 종료 처리
                            term_detected, _ = is_word_detected(command_text, TERMINATE_WORDS)
                            if term_detected:
                                print("[시스템] '종료' 명령이 감지되었습니다. 에이전트를 안전하게 종료합니다. 👋")
                                play_audio(STOP_SOUND_PATH)
                                return
                                
                            # 여기서 나중에 OBS 녹화 시작, 화면 분석 등의 로직과 연결됩니다.
                            
                            # 명령 처리가 끝났으므로 다시 호출 대기 모드로 돌아감
                            state = "WAKE_WORD_LISTENING"
                        else:
                            print("⚠️ [안내] 명령이 명확하지 않습니다. 다시 호출해주세요.")
                            state = "WAKE_WORD_LISTENING"
                            
                    except sr.WaitTimeoutError:
                        print("⏳ [시간 초과] 명령이 입력되지 않았습니다. 대기 모드로 돌아갑니다.")
                        state = "WAKE_WORD_LISTENING"

    except KeyboardInterrupt:
        print("\n\n[INFO] 프로그램을 종료합니다.")

if __name__ == "__main__":
    run_agent()
