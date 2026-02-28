"""
obs_capture.py — OBS WebSocket을 통한 실시간 프레임 캡처
기존 pre_test/04_obs_mirroring_test.py 로직을 클래스로 모듈화
"""
import base64
import numpy as np
import cv2
from obsws_python import ReqClient

from config import OBS_HOST, OBS_PORT, OBS_PASSWORD, OBS_MIRROR_WIDTH, OBS_MIRROR_HEIGHT, OBS_MIRROR_QUALITY


class OBSCapture:
    """OBS WebSocket을 통해 실시간으로 프레임을 캡처하는 클래스"""

    def __init__(self):
        self.client = None
        self.connected = False
        self.current_scene = None

    def connect(self):
        """OBS WebSocket 서버에 연결합니다."""
        try:
            self.client = ReqClient(
                host=OBS_HOST,
                port=OBS_PORT,
                password=OBS_PASSWORD,
                timeout=5
            )
            # 현재 씬 이름 가져오기
            scene_resp = self.client.get_current_program_scene()
            self.current_scene = scene_resp.current_program_scene_name
            self.connected = True
            print(f"[OBS] 연결 성공! 현재 씬: {self.current_scene}")
            return True
        except Exception as e:
            print(f"[OBS] 연결 실패: {e}")
            self.connected = False
            return False

    def capture_frame(self):
        """
        현재 OBS 씬의 스크린샷을 캡처하여 OpenCV numpy 배열로 반환합니다.
        Returns:
            numpy.ndarray 또는 None (실패 시)
        """
        if not self.connected or not self.client:
            return None

        try:
            # 씬 이름 갱신 (씬 전환 대응)
            scene_resp = self.client.get_current_program_scene()
            self.current_scene = scene_resp.current_program_scene_name

            # Base64 JPEG 스크린샷 요청
            screenshot_resp = self.client.get_source_screenshot(
                self.current_scene,
                "jpeg",
                OBS_MIRROR_WIDTH,
                OBS_MIRROR_HEIGHT,
                OBS_MIRROR_QUALITY,
            )

            image_data = screenshot_resp.image_data
            if image_data.startswith("data:image"):
                base64_str = image_data.split(",")[1]
            else:
                base64_str = image_data

            # Base64 → numpy 배열 → OpenCV BGR 이미지
            image_bytes = base64.b64decode(base64_str)
            np_arr = np.frombuffer(image_bytes, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            return frame

        except Exception as e:
            print(f"[OBS] 프레임 캡처 실패: {e}")
            return None

    def disconnect(self):
        """OBS WebSocket 연결을 종료합니다."""
        self.client = None
        self.connected = False
        print("[OBS] 연결 해제")
