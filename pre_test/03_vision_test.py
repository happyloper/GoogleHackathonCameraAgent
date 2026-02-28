import os
import sys
from google import genai
from google.genai import types
from dotenv import load_dotenv

# 출력 인코딩을 UTF-8로 설정
sys.stdout.reconfigure(encoding='utf-8')

# .env 파일 로드
load_dotenv()

# API 키 가져오기
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("[ERROR] GEMINI_API_KEY를 찾을 수 없습니다.")
    exit(1)

import glob

# 이미지 파일 경로 확인 (captures 폴더에서 가장 최근 파일 가져오기)
capture_dir = os.path.join(os.path.dirname(__file__), "captures")
image_files = glob.glob(os.path.join(capture_dir, "obs_*.jpg"))

if not image_files:
    print(f"[ERROR] {capture_dir} 폴더에 캡처된 이미지가 없습니다. 먼저 OBS 스크린샷 캡처를 진행해주세요.")
    exit(1)

# 수정 시간이 가장 최근인 파일 선택
image_path = max(image_files, key=os.path.getmtime)
print(f"[INFO] 최근 캡처 이미지 로드: {image_path}")

try:
    print("[INFO] Gemini Client 초기화 및 이미지 업로드 중...")
    client = genai.Client(api_key=api_key)
    
    # 로컬 파일을 Gemini에 업로드
    # SDK 1.x 버전에서는 client.files.upload()를 사용합니다.
    uploaded_file = client.files.upload(file=image_path)
    print(f"[INFO] 업로드 완료: {uploaded_file.name}")
    
    # 모델에 텍스트 프롬프트와 함께 이미지를 전달하여 분석 요청
    print("[INFO] Gemini Vision(gemini-2.5-flash)에 분석 요청 전송 중...")
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[
            uploaded_file,
            "이 이미지는 OBS를 통해 캡처된 화면입니다. 이미지에 무엇이 보이는지 상세히 설명해주세요."
        ]
    )
    
    print("\n--- Gemini Vision 응답 ---")
    print(response.text)
    print("--------------------------")
    
    # 텍스트 결과 저장 (이미지 파일명과 동일한 이름의 .txt 파일 생성)
    # 예: captures/obs_20260228_105938.jpg -> captures/obs_20260228_105938.txt
    text_output_path = os.path.splitext(image_path)[0] + ".txt"
    with open(text_output_path, "w", encoding="utf-8") as f:
        f.write(response.text)
    print(f"[SUCCESS] 이미지 분석 결과가 텍스트 파일로 저장되었습니다: {text_output_path}")
    print("[SUCCESS] 이미지 인식 테스트가 성공적으로 완료되었습니다!")

except Exception as e:
    print(f"[ERROR] Gemini Vision 요청 중 오류 발생: {e}")
