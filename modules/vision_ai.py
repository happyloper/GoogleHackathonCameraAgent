"""
vision_ai.py — Gemini Vision API를 통한 손가락 포인팅 감지 + Bounding Box 추출
"""
import os
import json
import re
import cv2
import tempfile

from config import GEMINI_API_KEY, GEMINI_MODEL


class VisionAI:
    """Gemini Vision을 사용하여 손가락이 가리키는 객체를 감지합니다."""

    # Gemini에 전송할 프롬프트 (핵심 프롬프트 엔지니어링)
    DETECT_PROMPT_BASE = """이 이미지에서 사람이 손가락(또는 손)으로 가리키고 있는 물체를 정확히 찾아주세요.

다음 규칙을 반드시 따라주세요:
1. 손가락 끝이 향하는 방향에 있는 물체를 찾으세요. 손가락 끝에서 가장 가까운 물체입니다.
2. 손가락 끝의 위치와 방향을 주의 깊게 분석하세요. 손가락이 왼쪽을 가리키면 왼쪽 물체, 오른쪽을 가리키면 오른쪽 물체입니다.
3. 해당 물체의 이름과 bounding box 좌표를 JSON으로만 반환해주세요.
4. 좌표는 이미지 크기 기준 0~1000 범위의 정규화된 값으로 주세요.
5. 설명이나 추가 텍스트 없이 JSON만 출력해주세요.
{exclude_section}
응답 형식:
{{"label": "물체이름", "bbox": [y_min, x_min, y_max, x_max]}}
"""

    def __init__(self):
        self.client = None

    def _ensure_client(self):
        """Gemini 클라이언트를 초기화합니다 (지연 초기화)."""
        if self.client is None:
            from google import genai
            self.client = genai.Client(api_key=GEMINI_API_KEY)
            print("[Vision] Gemini 클라이언트 초기화 완료")

    def detect_pointed_object(self, frame, existing_bboxes=None):
        """
        OpenCV 프레임에서 손가락이 가리키는 객체를 감지합니다.

        Args:
            frame: OpenCV numpy 배열 (BGR)
            existing_bboxes: 이미 등록된 타겟들의 bbox 리스트 [[x1,y1,x2,y2], ...] (픽셀 좌표)

        Returns:
            dict: {"label": str, "bbox": [x1, y1, x2, y2]} (픽셀 좌표)
                  또는 None (감지 실패 시)
        """
        self._ensure_client()

        try:
            h, w = frame.shape[:2]

            # 이미 등록된 타겟 영역 제외 문구 생성
            exclude_section = ""
            if existing_bboxes and len(existing_bboxes) > 0:
                exclude_lines = []
                for i, bbox in enumerate(existing_bboxes):
                    # 픽셀 → 0~1000 정규화
                    ny1 = int(bbox[1] * 1000 / h)
                    nx1 = int(bbox[0] * 1000 / w)
                    ny2 = int(bbox[3] * 1000 / h)
                    nx2 = int(bbox[2] * 1000 / w)
                    exclude_lines.append(f"  - 이미 등록됨: [{ny1}, {nx1}, {ny2}, {nx2}]")
                exclude_section = (
                    "\n6. 아래 영역에 이미 등록된 물체가 있습니다. "
                    "이 영역과 겹치는 물체는 절대 선택하지 마세요. 반드시 다른 물체를 찾으세요:\n"
                    + "\n".join(exclude_lines) + "\n"
                )

            prompt = self.DETECT_PROMPT_BASE.format(exclude_section=exclude_section)

            # 프레임을 임시 JPEG 파일로 저장 후 업로드
            temp_path = os.path.join(tempfile.gettempdir(), "camera_agent_detect.jpg")
            cv2.imwrite(temp_path, frame)

            # Gemini에 이미지 업로드
            uploaded_file = self.client.files.upload(file=temp_path)

            # 이미지 + 프롬프트 전송 (429 레이트리밋 시 자동 재시도)
            import time as _time
            for attempt in range(2):
                try:
                    response = self.client.models.generate_content(
                        model=GEMINI_MODEL,
                        contents=[uploaded_file, prompt],
                    )
                    break
                except Exception as api_err:
                    if "429" in str(api_err) and attempt == 0:
                        print("[Vision] API 한도 초과 — 30초 후 재시도...")
                        _time.sleep(30)
                    else:
                        raise api_err

            print(f"[Vision] Gemini 응답: {response.text}")

            # JSON 파싱
            result = self._parse_response(response.text, w, h)

            # 임시 파일 정리
            try:
                os.remove(temp_path)
            except Exception:
                pass

            return result

        except Exception as e:
            print(f"[Vision] 감지 실패: {e}")
            return None

    def _parse_response(self, text, img_width, img_height):
        """
        Gemini 응답에서 JSON을 추출하고 정규화 좌표를 픽셀 좌표로 변환합니다.
        
        Gemini는 좌표를 [y_min, x_min, y_max, x_max] 형식의 0~1000 정규화 값으로 반환합니다.
        이를 [x1, y1, x2, y2] 픽셀 좌표로 변환합니다.
        """
        try:
            # JSON 블록 추출 (```json ... ``` 또는 순수 JSON)
            json_match = re.search(r'\{[^}]+\}', text, re.DOTALL)
            if not json_match:
                print(f"[Vision] JSON 파싱 실패. 원본 응답: {text}")
                return None

            data = json.loads(json_match.group())

            label = data.get("label", "물체")
            bbox_norm = data.get("bbox", [])

            if len(bbox_norm) != 4:
                print(f"[Vision] bbox 형식 오류: {bbox_norm}")
                return None

            # Gemini 형식: [y_min, x_min, y_max, x_max] (0~1000)
            # → 픽셀: [x1, y1, x2, y2]
            y_min, x_min, y_max, x_max = bbox_norm
            print(f"[Vision] Gemini 원본 좌표 (y_min,x_min,y_max,x_max): {bbox_norm}")
            print(f"[Vision] 이미지 크기: {img_width}x{img_height}")

            x1 = int(x_min * img_width / 1000)
            y1 = int(y_min * img_height / 1000)
            x2 = int(x_max * img_width / 1000)
            y2 = int(y_max * img_height / 1000)

            print(f"[Vision] 변환된 픽셀 좌표 (x1,y1,x2,y2): [{x1}, {y1}, {x2}, {y2}]")

            # 좌표 범위 클램핑
            x1 = max(0, min(x1, img_width))
            y1 = max(0, min(y1, img_height))
            x2 = max(0, min(x2, img_width))
            y2 = max(0, min(y2, img_height))

            result = {"label": label, "bbox": [x1, y1, x2, y2]}
            print(f"[Vision] 감지 결과: {result}")
            return result

        except (json.JSONDecodeError, ValueError) as e:
            print(f"[Vision] 파싱 에러: {e}, 원본: {text}")
            return None
