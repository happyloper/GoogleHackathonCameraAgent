"""
stt_worker.py — STT 전용 독립 프로세스 워커
⚠️ 이 파일에서는 PyQt5를 절대 import하지 않습니다!
   (Windows multiprocessing.spawn 환경에서 Qt OpenMP DLL 충돌 방지)

multiprocessing.Pipe를 통해 메인 프로세스와 통신합니다.
"""
import os
import sys
import numpy as np
import time
import speech_recognition as sr

# Windows CUDA DLL 경로 주입
try:
    import site
    packages_dir = site.getsitepackages()[0]
    os.add_dll_directory(os.path.join(packages_dir, "nvidia", "cublas", "bin"))
    os.add_dll_directory(os.path.join(packages_dir, "nvidia", "cudnn", "bin"))
except Exception:
    pass

# config.py import (dotenv는 OK, PyQt5만 금지)
from config import (
    STT_MODEL_SIZE, STT_DEVICE, STT_COMPUTE_TYPE,
    WAKE_WORDS, TERMINATE_WORDS,
)


def _load_whisper():
    """Faster-Whisper 모델을 로드합니다."""
    from faster_whisper import WhisperModel
    print(f"[STT] Faster-Whisper '{STT_MODEL_SIZE}' ({STT_DEVICE}) 모델 로딩 중...")
    model = WhisperModel(STT_MODEL_SIZE, device=STT_DEVICE, compute_type=STT_COMPUTE_TYPE)
    print(f"[STT] 모델 로드 완료!")
    return model


def _transcribe(model, audio_data):
    """AudioData를 텍스트로 변환합니다."""
    try:
        raw_bytes = audio_data.get_raw_data(convert_rate=16000, convert_width=2)
        audio_np = np.frombuffer(raw_bytes, np.int16).flatten().astype(np.float32) / 32768.0

        hint_prompt = "짭스, 헤이짭스, 타겟, 설정, 확대, 줌인, 구도 복원, 종료, 꺼 줘, 종이컵. "

        segments, info = model.transcribe(
            audio_np,
            beam_size=1,
            language="ko",
            condition_on_previous_text=False,
            vad_filter=True,
            initial_prompt=hint_prompt,
        )
        return "".join([seg.text + " " for seg in segments]).strip()
    except Exception as e:
        print(f"[STT] 변환 오류: {e}")
        return ""


def _is_detected(text, word_list):
    """텍스트에서 키워드 목록 중 하나가 포함되어 있는지 확인합니다."""
    cleaned = text.replace(" ", "").lower()
    for word in word_list:
        if word.replace(" ", "").lower() in cleaned:
            return True, word
    return False, None


def stt_process(pipe_conn):
    """
    STT 전용 프로세스 엔트리포인트.
    호출어를 상시 감지하고, 명령을 인식하여 Pipe로 전송합니다.

    Pipe 전송 형식 (dict):
        {"type": "status", "status": "ready"}
        {"type": "status", "status": "wake_detected"}
        {"type": "status", "status": "listening_command"}
        {"type": "command", "text": "종이컵 1 확대해 줘"}
        {"type": "terminate"}
    """
    model = _load_whisper()
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    print("[STT] 주변 소음 측정 중 (2초)...")
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=2)
        recognizer.pause_threshold = 0.5

    # 준비 완료 알림
    pipe_conn.send({"type": "status", "status": "ready"})
    print("[STT] 호출어 대기 모드 시작!")

    state = "WAKE_WORD_LISTENING"

    try:
        while True:
            # 메인 프로세스에서 종료 신호 확인
            if pipe_conn.poll(0):
                msg = pipe_conn.recv()
                if msg.get("type") == "shutdown":
                    print("[STT] 종료 신호 수신")
                    break

            with mic as source:
                if state == "WAKE_WORD_LISTENING":
                    try:
                        audio_data = recognizer.listen(source, timeout=5, phrase_time_limit=5)
                    except sr.WaitTimeoutError:
                        continue

                    text = _transcribe(model, audio_data)
                    if not text:
                        continue

                    # 종료 명령 체크
                    term_detected, _ = _is_detected(text, TERMINATE_WORDS)
                    if term_detected:
                        pipe_conn.send({"type": "terminate"})
                        break

                    # 호출어 체크
                    wake_detected, word = _is_detected(text, WAKE_WORDS)
                    if wake_detected:
                        print(f"[STT] 호출어 감지: '{word}' (원문: {text})")
                        pipe_conn.send({"type": "status", "status": "wake_detected"})

                        # 호출어와 함께 명령이 포함되어 있는지 확인
                        # 예: "짭스 이거 타겟 설정해 줘" → 호출어 + 명령이 한 문장
                        remaining = text
                        for w in WAKE_WORDS:
                            remaining = remaining.replace(w, "").strip()
                        remaining = remaining.strip(" ,.")

                        if len(remaining) > 3:
                            # 한 문장에 호출어+명령 포함
                            print(f"[STT] 즉시 명령 인식: {remaining}")
                            pipe_conn.send({"type": "command", "text": remaining})
                            state = "WAKE_WORD_LISTENING"
                        else:
                            # 명령 대기 모드로 전환
                            state = "COMMAND_LISTENING"

                elif state == "COMMAND_LISTENING":
                    pipe_conn.send({"type": "status", "status": "listening_command"})
                    try:
                        audio_data = recognizer.listen(source, timeout=10, phrase_time_limit=15)
                    except sr.WaitTimeoutError:
                        print("[STT] 명령 대기 시간 초과")
                        pipe_conn.send({"type": "status", "status": "timeout"})
                        state = "WAKE_WORD_LISTENING"
                        continue

                    command_text = _transcribe(model, audio_data)
                    if command_text:
                        # 종료 명령 체크
                        term_detected, _ = _is_detected(command_text, TERMINATE_WORDS)
                        if term_detected:
                            pipe_conn.send({"type": "terminate"})
                            break

                        print(f"[STT] 명령 수신: {command_text}")
                        pipe_conn.send({"type": "command", "text": command_text})
                    else:
                        pipe_conn.send({"type": "status", "status": "not_recognized"})

                    state = "WAKE_WORD_LISTENING"

    except KeyboardInterrupt:
        print("[STT] 프로세스 종료")
    finally:
        pipe_conn.close()
