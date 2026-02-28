import time
import pyttsx3

def test_pyttsx3_latency():
    print("=== pyttsx3 (오프라인 내장 TTS) 속도 테스트 ===")
    
    # TTS 엔진 초기화
    engine = pyttsx3.init()
    
    # 윈도우 기본 보이스 설정 (보통 0번이 영어, 1번이 한국어인 경우가 많습니다)
    voices = engine.getProperty('voices')
    print("▶ 현재 PC에 설치된 한국어 AI 목소리 목록:")
    korean_voices = []
    for voice in voices:
        if 'Korean' in voice.name or 'ko-KR' in voice.id:
            korean_voices.append(voice)
            print(f"  - {voice.name}")
            
    if korean_voices:
        # 기본적으로 첫 번째 한국어 목소리로 세팅
        engine.setProperty('voice', korean_voices[0].id)
            
    # --------------------------------------------------------------------------
    # [설정] 여기서 원하는 말하기 속도를 마음대로 수정해서 테스트해 보세요!
    # 기본: 200, 약간 느림: 150, 빠름: 250~300 (너무 높이면 소리가 안 날 수 있음)
    # --------------------------------------------------------------------------
    TARGET_RATE = 200
    engine.setProperty('rate', TARGET_RATE)
    # --------------------------------------------------------------------------
    
    # 볼륨 조절 (0.0 ~ 1.0)
    engine.setProperty('volume', 1.0)

    test_text = f"안녕하세요. 현재 말하기 속도는 {TARGET_RATE}입니다."
    
    print(f"\n[엔터 키를 누르면 방금 설정하신 속도({TARGET_RATE})로 텍스트를 읽습니다!]")
    input()
    
    start_time = time.time()
    
    engine.say(test_text)
    print(f"[소요 시간] 음성을 즉각적으로 처리하는 데 {time.time() - start_time:.4f}초가 걸렸습니다.")
    print(f"🗣️ 에이전트: \"{test_text}\"")
    
    engine.runAndWait()
    
    print("\n[완료] 음성 출력이 끝났습니다.")

if __name__ == "__main__":
    test_pyttsx3_latency()
