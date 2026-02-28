import os
import sys
from google import genai
from dotenv import load_dotenv

# 출력 인코딩을 UTF-8로 설정 (Windows cmd의 cp949 오류 방지)
sys.stdout.reconfigure(encoding='utf-8')

# .env 파일 로드
load_dotenv()

# API 키 가져오기
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("[ERROR] GEMINI_API_KEY를 찾을 수 없습니다. .env 파일을 확인해주세요.")
    exit(1)

print("[SUCCESS] GEMINI_API_KEY 로드 성공!")

try:
    # Gemini API 클라이언트 초기화
    client = genai.Client(api_key=api_key)

    print("요청 전송 중...")
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents="구글 해커톤을 시작합니다! 힘이 되는 짧은 응원의 메시지를 작성해줘."
    )
    print("\n--- Gemini 응답 ---")
    print(response.text)
    print("-------------------")
    print("[SUCCESS] Gemini API 기본 연동 테스트 성공!")
except Exception as e:
    print(f"[ERROR] Gemini API 요청 중 오류 발생: {e}")
