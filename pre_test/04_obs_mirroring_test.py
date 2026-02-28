import os
import cv2
import time
import base64
import numpy as np
from dotenv import load_dotenv
from obsws_python import ReqClient
import warnings

# PyQt 등에 의한 경고 숨기기
warnings.filterwarnings('ignore')

# .env 파일 로드
load_dotenv()
OBS_HOST = os.getenv("OBS_HOST", "localhost")
OBS_PORT = os.getenv("OBS_PORT", "4455")
OBS_PASSWORD = os.getenv("OBS_PASSWORD", "")

print("[INFO] OBS 실시간 미러링 시작 (종료: 미러링 창에서 'q' 또는 'ESC' 키 누름)")

try:
    client = ReqClient(host=OBS_HOST, port=int(OBS_PORT), password=OBS_PASSWORD, timeout=3)
    
    # 미러링할 창 설정
    window_name = "OBS Real-time Mirror (Low FPS)"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    
    # 초당 프레임 수(FPS) 제한 (예: 2~3 FPS). OBS에 부하를 주지 않기 위함.
    # 0.3초마다 1번 캡처 (약 3.3 FPS)
    delay_seconds = 0.3
    
    while True:
        start_time = time.time()
        
        # 1. OBS에서 현재 씬의 스크린샷 요청
        current_scene_resp = client.get_current_program_scene()
        current_scene_name = current_scene_resp.current_program_scene_name
        
        # 품질을 50~70 사이로 낮추고, 해상도를 절반(예: 1280x720)으로 줄여서 WebSocket 부하 감소
        screenshot_resp = client.get_source_screenshot(
            current_scene_name,
            "jpeg",
            1280,
            720,
            70
        )
        
        image_data = screenshot_resp.image_data
        if image_data.startswith("data:image"):
            base64_str = image_data.split(",")[1]
        else:
            base64_str = image_data
            
        # 2. Base64 비트스트림을 OpenCV 이미지 배열로 변환
        image_bytes = base64.b64decode(base64_str)
        np_arr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        if frame is not None:
            # 3. 화면에 띄우기
            cv2.imshow(window_name, frame)
            
        # 4. 키보드 입력 처리 및 프레임 지연
        # cv2.waitKey는 밀리초 단위 입력을 받음
        elapsed_time = time.time() - start_time
        wait_ms = max(1, int((delay_seconds - elapsed_time) * 1000))
        
        key = cv2.waitKey(wait_ms) & 0xFF
        if key == ord('q') or key == 27:  # 'q' 또는 ESC 키
            print("[INFO] 사용자에 의해 미러링을 종료합니다.")
            break

except Exception as e:
    print(f"[ERROR] 오류 발생: {e}")

finally:
    cv2.destroyAllWindows()
    print("[INFO] 프로그램 종료.")
