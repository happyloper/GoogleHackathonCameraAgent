import os
import sys

# Windows에서 CUDA 러닝 타임 에러(DLL 로드 실패) 방지를 위해 NVIDIA DLL 경로를 주입합니다.
try:
    import site
    packages_dir = site.getsitepackages()[0]
    os.add_dll_directory(os.path.join(packages_dir, "nvidia", "cublas", "bin"))
    os.add_dll_directory(os.path.join(packages_dir, "nvidia", "cudnn", "bin"))
except Exception:
    pass

import numpy as np
import time
import speech_recognition as sr
from faster_whisper import WhisperModel

# 모델 설정 (CPU 사용, 성능/속도 타협)
MODEL_SIZE = "small"

def load_local_whisper():
    """Faster-Whisper 모델을 메모리에 로드합니다."""
    print(f"\n[설정] Faster-Whisper '{MODEL_SIZE}' 모델 (CPU) 로딩을 시작합니다...")
    model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    print(f"[SUCCESS] Faster-Whisper 로드 성공! 언제든 말씀해 주세요.\n")
    return model

def transcribe_from_memory(model, audio_data: sr.AudioData):
    """
    speech_recognition의 AudioData(메모리)를 numpy 배열로 변환 후
    임시 파일 생성 없이 즉시 Faster-Whisper로 분석합니다.
    """
    try:
        # AudioData에서 raw bytes(16-bit PCM) 추출
        raw_bytes = audio_data.get_raw_data(convert_rate=16000, convert_width=2)
        
        # Whisper 입력 형식(float32, -1.0 ~ 1.0)에 맞게 정규화
        audio_np = np.frombuffer(raw_bytes, np.int16).flatten().astype(np.float32) / 32768.0
        
        # CPU 환경 최적화를 위한 파라미터 튜닝
        # - beam_size=1: 속도 대폭 향상 (정확도 미세 감소)
        # - condition_on_previous_text=False: 앞 문맥 연산을 생략하여 속도 증가
        # - vad_filter=True: 음성 없는 구간을 모델 내부적으로 한 번 더 걸러내어 연산량 감소
        segments, info = model.transcribe(
            audio_np, 
            beam_size=1, 
            language="ko",
            condition_on_previous_text=False,
            vad_filter=True
        )
        
        recognized_text = "".join([segment.text + " " for segment in segments]).strip()
        return recognized_text
    except Exception as e:
        print(f"\n[오류] 변환 중 에러 발생: {e}")
        return ""

def start_smart_stt():
    """VAD(음성 활동 감지)를 이용한 스마트 STT 실시간 모드"""
    model = load_local_whisper()
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    print("[시스템] 주변 소음 수준을 측정합니다. 2초간 잠시 조용히 해주세요...")
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=2)
        # 기본값(0.8초)보다 짧게 설정하여, 말을 멈추면 0.5초만 쉬어도 즉시 분석을 시작하게 함
        recognizer.pause_threshold = 0.5 
        
    print("\n=======================================================")
    print("🎙️ 스마트 대기 모드 진입 완료!")
    print("   말을 시작하면 듣고, 조용해지면 즉시 문장을 반환합니다.")
    print("   (마치시려면 터미널에서 Ctrl+C를 눌러주세요)")
    print("=======================================================\n")

    try:
        while True:
            with mic as source:
                print("\n[대기 중] 말씀해 주세요...")
                try:
                    # timeout=None (무한 대기), phrase_time_limit=15 (최대 15초 녹음)
                    audio_data = recognizer.listen(source, timeout=None, phrase_time_limit=15)
                    
                    print("[처리 중] ▶ 음성이 감지되어 문장을 분석합니다...")
                    start_time = time.time()
                    
                    # 파일 저장 없이 메모리(audio_data)를 그대로 전달하여 지연 최소화
                    text = transcribe_from_memory(model, audio_data)
                    
                    elapsed = time.time() - start_time
                    
                    if text:
                        print(f"✅ [결과] ({elapsed:.2f}초 소요): {text}")
                    else:
                        print("⚠️ [안내] (음성이 명확하지 않아 텍스트로 변환하지 못했습니다)")
                        
                except Exception as e:
                    print(f"[오류] 마이크 청취 중 에러: {e}")
                    
    except KeyboardInterrupt:
        print("\n\n[INFO] 사용자에 의해 STT 테스트가 종료되었습니다.")

if __name__ == "__main__":
    start_smart_stt()
