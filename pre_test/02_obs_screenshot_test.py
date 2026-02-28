import os
import sys
import base64
from dotenv import load_dotenv
from obsws_python import ReqClient

# 출력 인코딩을 UTF-8로 설정
sys.stdout.reconfigure(encoding='utf-8')

# .env 파일 로드
load_dotenv()

# 환경 변수에서 OBS 접속 정보 가져오기
OBS_HOST = os.getenv("OBS_HOST", "localhost")
OBS_PORT = os.getenv("OBS_PORT", "4455")
OBS_PASSWORD = os.getenv("OBS_PASSWORD", "")

print(f"[INFO] OBS 연결 시도: {OBS_HOST}:{OBS_PORT}")

try:
    # OBS WebSocket 연결
    # obsws-python의 경우 host, port, password 인자를 명시적으로 받습니다.
    # 연결 실패 시 예외가 발생합니다.
    client = ReqClient(host=OBS_HOST, port=int(OBS_PORT), password=OBS_PASSWORD, timeout=3)
    
    print("[SUCCESS] OBS WebSocket 서버에 연결되었습니다!")
    
    # 현재 화면 스크린샷 캡처 (Base64 JPEG 형태로 반환)
    # GetSourceScreenshot: 활성화된 특정 소스 또는 씬의 스크린샷 캡처
    # (여기서는 기본적으로 현재 포커스된 장면을 시도하거나 필요 시 화면 전체를 캡처할 수 있는 기능을 테스트합니다.)
    # 참조: https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md#getsourcescreenshot
    
    # 1. 활성화된 씬 이름 가져오기
    current_scene_resp = client.get_current_program_scene()
    current_scene_name = current_scene_resp.current_program_scene_name
    print(f"[INFO] 현재 활성화된 씬: {current_scene_name}")
    
    # 2. 씬을 소스로 지정하여 스크린샷 요청
    # obsws-python 라이브러리 시그니처: get_source_screenshot(self, name, img_format, width, height, quality)
    screenshot_resp = client.get_source_screenshot(
        current_scene_name,
        "jpeg",
        1920,
        1080,
        80
    )
    
    # 3. Base64 데이터를 이미지 파일로 저장
    # obsws-python은 응답 객체의 image_data 속성으로 `data:image/jpeg;base64,...` 문자열을 반환합니다.
    image_data = screenshot_resp.image_data
    if image_data.startswith("data:image"):
        # "data:image/jpeg;base64," 부분을 제거하고 순수 base64 문자열만 추출
        base64_str = image_data.split(",")[1]
    else:
        base64_str = image_data
        
    image_bytes = base64.b64decode(base64_str)
        
    import datetime
    
    # captures 폴더가 없으면 생성
    capture_dir = os.path.join(os.path.dirname(__file__), "captures")
    os.makedirs(capture_dir, exist_ok=True)
    
    # 시간값을 포함한 파일 이름 생성 (예: obs_20260228_105830.jpg)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = os.path.join(capture_dir, f"obs_{timestamp}.jpg")
    
    with open(output_filename, "wb") as f:
        f.write(image_bytes)
        
    print(f"[SUCCESS] 스크린샷이 성공적으로 저장되었습니다: {output_filename}")

except Exception as e:
    print(f"[ERROR] OBS 연동 또는 스크린샷 캡처 중 오류 발생: {e}")
    # 서버가 켜져 있지 않거나, 비밀번호가 틀린 경우 오류가 납니다.
