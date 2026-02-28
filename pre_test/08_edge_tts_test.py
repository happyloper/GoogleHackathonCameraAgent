import os
import time
import asyncio
import edge_tts
import pygame

# 오디오 재생을 위한 pygame 초기화
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
pygame.mixer.init()

# 오디오 파일을 저장할 전용 폴더 생성
AUDIO_DIR = "temp_audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

async def generate_and_play_edge_tts(text, voice="ko-KR-SunHiNeural", rate="+25%"):
    # 전용 폴더 안에 고유한 파일명으로 저장 (덮어쓰기 방지 고려)
    timestamp = int(time.time())
    temp_file = os.path.join(AUDIO_DIR, f"tts_{timestamp}.mp3")
    
    start_time = time.time()
    
    # 텍스트를 음성 파일로 생성 (비동기)
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(temp_file)
    
    generation_time = time.time() - start_time
    print(f"[소요 시간] 음성 파일을 생성하는 데 {generation_time:.4f}초가 걸렸습니다.")
    
    # 생성된 파일 재생
    if os.path.exists(temp_file):
        pygame.mixer.music.load(temp_file)
        pygame.mixer.music.play()
        print(f"🗣️ 에이전트: \"{text}\"")
        
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
            
        # 재생 완료 후 파일 닫음 처리 (삭제는 나중에 일괄 처리하거나 보관 가능)
        pygame.mixer.music.unload()
            
def test_edge_tts():
    print("=== Edge TTS (고품질 내레이터 AI 목소리) 테스트 ===")
    test_text = "안녕하세요. 저는 윈도우 내레이터이자 엣지 브라우저에서 사용되는 고품질 AI 목소리입니다. 속도를 25퍼센트 올려서 빠르게 말하고 있습니다."
    
    print(f"\n[엔터 키를 누르면 '{AUDIO_DIR}' 폴더에 mp3 파일이 생성되고 재생됩니다!]")
    input()
    
    # SunHi(여성), InJoon(남성) 두 가지가 대표적입니다.
    asyncio.run(generate_and_play_edge_tts(test_text, voice="ko-KR-SunHiNeural"))
    
    print("\n[완료] 테스트가 종료되었습니다.")

if __name__ == "__main__":
    test_edge_tts()
