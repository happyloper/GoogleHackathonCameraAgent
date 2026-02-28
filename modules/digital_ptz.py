"""
digital_ptz.py — 디지털 Pan-Tilt-Zoom (스무스 줌인/줌아웃)
OpenCV 프레임에 대해 crop & scale을 적용하여 가상 카메라 줌 효과를 구현합니다.
"""
import cv2
import numpy as np
import time


class DigitalPTZ:
    """
    디지털 PTZ 컨트롤러.
    현재 뷰포트(crop 영역)를 관리하며, 부드러운 줌인/줌아웃 애니메이션을 제공합니다.
    """

    def __init__(self, frame_width=1280, frame_height=720):
        self.frame_width = frame_width
        self.frame_height = frame_height

        # 전체 뷰 (정규화 좌표 0.0 ~ 1.0)
        self.full_view = [0.0, 0.0, 1.0, 1.0]  # [x1, y1, x2, y2]

        # 현재 뷰포트 (애니메이션 과정에서 변화)
        self.current_view = list(self.full_view)

        # 애니메이션 상태
        self._animating = False
        self._anim_start_view = None
        self._anim_end_view = None
        self._anim_start_time = None
        self._anim_duration = 0.8  # 초

    @property
    def is_zoomed(self):
        """현재 줌인 상태인지 확인합니다."""
        return self.current_view != self.full_view

    @property
    def is_animating(self):
        return self._animating

    def zoom_to(self, bbox, duration=0.8, padding=0.5, min_crop_ratio=0.3):
        """
        특정 바운딩 박스로 줌인 애니메이션을 시작합니다.

        Args:
            bbox: [x1, y1, x2, y2] 픽셀 좌표
            duration: 애니메이션 지속 시간 (초)
            padding: bbox 주변 여백 비율 (0.5 = 50% 추가 공간)
            min_crop_ratio: 최소 크롭 비율 (0.3 = 프레임의 30% 이상)
        """
        # 픽셀 좌표를 정규화 좌표로 변환
        x1 = bbox[0] / self.frame_width
        y1 = bbox[1] / self.frame_height
        x2 = bbox[2] / self.frame_width
        y2 = bbox[3] / self.frame_height

        # 패딩 적용
        w = x2 - x1
        h = y2 - y1
        pad_x = w * padding
        pad_y = h * padding

        target_x1 = max(0.0, x1 - pad_x)
        target_y1 = max(0.0, y1 - pad_y)
        target_x2 = min(1.0, x2 + pad_x)
        target_y2 = min(1.0, y2 + pad_y)

        # 최소 크롭 크기 보장 (너무 과격한 줌 방지)
        target_w = target_x2 - target_x1
        target_h = target_y2 - target_y1
        if target_w < min_crop_ratio:
            center_x = (target_x1 + target_x2) / 2
            target_x1 = max(0.0, center_x - min_crop_ratio / 2)
            target_x2 = min(1.0, target_x1 + min_crop_ratio)
            target_w = target_x2 - target_x1
        if target_h < min_crop_ratio:
            center_y = (target_y1 + target_y2) / 2
            target_y1 = max(0.0, center_y - min_crop_ratio / 2)
            target_y2 = min(1.0, target_y1 + min_crop_ratio)
            target_h = target_y2 - target_y1

        # 화면 비율(16:9) 유지
        aspect = self.frame_width / self.frame_height

        if target_w / target_h > aspect:
            # 너비 기준 → 높이 확장
            new_h = target_w / aspect
            center_y = (target_y1 + target_y2) / 2
            target_y1 = max(0.0, center_y - new_h / 2)
            target_y2 = min(1.0, center_y + new_h / 2)
        else:
            # 높이 기준 → 너비 확장
            new_w = target_h * aspect
            center_x = (target_x1 + target_x2) / 2
            target_x1 = max(0.0, center_x - new_w / 2)
            target_x2 = min(1.0, center_x + new_w / 2)

        self._start_animation(
            [target_x1, target_y1, target_x2, target_y2],
            duration,
        )

    def reset_view(self, duration=0.8):
        """풀샷(전체 뷰)으로 스무스하게 복원합니다."""
        self._start_animation(list(self.full_view), duration)

    def _start_animation(self, target_view, duration):
        """애니메이션을 시작합니다."""
        self._anim_start_view = list(self.current_view)
        self._anim_end_view = target_view
        self._anim_start_time = time.time()
        self._anim_duration = duration
        self._animating = True

    def update(self):
        """매 프레임 호출하여 애니메이션 상태를 업데이트합니다."""
        if not self._animating:
            return

        elapsed = time.time() - self._anim_start_time
        t = min(elapsed / self._anim_duration, 1.0)

        # ease-in-out 보간 (smoothstep)
        t = t * t * (3.0 - 2.0 * t)

        # 선형 보간 (lerp)
        for i in range(4):
            self.current_view[i] = (
                self._anim_start_view[i] + (self._anim_end_view[i] - self._anim_start_view[i]) * t
            )

        if elapsed >= self._anim_duration:
            self.current_view = list(self._anim_end_view)
            self._animating = False

    def apply_view(self, frame):
        """
        현재 뷰포트를 프레임에 적용합니다. (crop → resize)

        Args:
            frame: 원본 OpenCV 프레임 (numpy array)

        Returns:
            처리된 프레임 (원본 크기로 resize)
        """
        if frame is None:
            return None

        h, w = frame.shape[:2]

        # 현재 뷰포트의 픽셀 좌표 계산
        x1 = int(self.current_view[0] * w)
        y1 = int(self.current_view[1] * h)
        x2 = int(self.current_view[2] * w)
        y2 = int(self.current_view[3] * h)

        # 범위 클램핑
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(w, x2)
        y2 = min(h, y2)

        # 너무 작은 영역 방지
        if x2 - x1 < 10 or y2 - y1 < 10:
            return frame

        # Crop
        cropped = frame[y1:y2, x1:x2]

        # 원본 크기로 resize (부드러운 보간)
        resized = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)

        return resized
