"""
voice_controller.py — 음성 명령 파싱
STT 워커로부터 전달받은 텍스트를 구조화된 명령으로 변환합니다.
"""
import re


class VoiceController:
    """음성 명령 텍스트를 구조화된 액션으로 파싱합니다."""

    # 키워드 → 액션 매핑
    ACTION_PATTERNS = {
        "set_target": [
            r"타겟.*설정", r"타겟.*등록", r"이거.*설정", r"이것.*설정",
            r"이거.*타겟", r"이것.*타겟", r"타겟.*해",
            r"이것도.*타겟", r"이거도.*타겟",
        ],
        "zoom_in": [
            r"확대", r"줌.*인", r"줌인", r"크게", r"클로즈.*업",
        ],
        "reset_view": [
            r"구도.*복원", r"원래.*대로", r"풀.*샷", r"줌.*아웃",
            r"복원", r"리셋", r"전체.*화면", r"다시.*원래",
        ],
        "remove_target": [
            r"타겟.*삭제", r"타겟.*제거", r"삭제",
        ],
        "list_targets": [
            r"모든.*타겟", r"타겟.*목록", r"타겟.*알려",
            r"타겟.*뭐", r"뭐.*있", r"등록.*뭐",
            r"타겟.*리스트", r"타겟.*확인",
        ],
    }

    def parse_command(self, text):
        """
        음성 인식 텍스트를 구조화된 명령으로 변환합니다.

        Returns:
            dict: {"action": str, "target": str|None, "raw_text": str}
        """
        if not text:
            return {"action": "unknown", "target": None, "raw_text": ""}

        cleaned = text.strip()
        result = {"action": "unknown", "target": None, "raw_text": cleaned}

        # 액션 판별
        for action, patterns in self.ACTION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, cleaned):
                    result["action"] = action
                    break
            if result["action"] != "unknown":
                break

        # 타겟 이름/번호 추출 (줌인, 삭제 등에서 사용)
        if result["action"] in ("zoom_in", "remove_target"):
            result["target"] = self._extract_target(cleaned)

        return result

    def _extract_target(self, text):
        """
        텍스트에서 타겟 식별자를 추출합니다.
        예: "종이컵 1 확대해 줘" → "종이컵 1"
            "타겟 2 확대" → "타겟 2"
        """
        # "타겟 N" 패턴
        match = re.search(r"타겟\s*(\d+)", text)
        if match:
            return f"타겟 {match.group(1)}"

        # "물체이름 N" 패턴 (예: "종이컵 1")
        # 확대/줌인/삭제 등의 동사 키워드 이전 부분에서 추출
        action_keywords = ["확대", "줌", "크게", "삭제", "제거", "클로즈"]
        for kw in action_keywords:
            idx = text.find(kw)
            if idx > 0:
                before = text[:idx].strip()
                if before:
                    return before

        return None
