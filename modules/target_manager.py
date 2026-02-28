"""
target_manager.py — 등록된 타겟 객체 관리
"""
from config import TARGET_COLORS


class Target:
    """단일 타겟 객체"""

    def __init__(self, target_id, label, bbox, color):
        self.id = target_id
        self.label = label
        self.bbox = bbox  # [x1, y1, x2, y2] 픽셀 좌표
        self.color = color

    @property
    def display_name(self):
        return f"Target {self.id}: {self.label}"

    def to_dict(self):
        return {
            "id": self.id,
            "label": self.label,
            "bbox": self.bbox,
            "color": self.color,
            "display_name": self.display_name,
        }


class TargetManager:
    """타겟 목록을 관리합니다."""

    def __init__(self):
        self.targets = []
        self._next_id = 1

    def add_target(self, label, bbox):
        """
        새 타겟을 등록합니다.

        Args:
            label: 물체 이름 (예: "종이컵")
            bbox: [x1, y1, x2, y2] 픽셀 좌표

        Returns:
            Target 객체
        """
        color_idx = (self._next_id - 1) % len(TARGET_COLORS)
        color = TARGET_COLORS[color_idx]

        target = Target(self._next_id, label, bbox, color)
        self.targets.append(target)
        self._next_id += 1

        print(f"[Target] 등록: {target.display_name} @ {bbox} (색상: {color})")
        return target

    def get_target(self, query):
        """
        쿼리로 타겟을 검색합니다.
        "타겟 1", "종이컵 1", "종이컵", 숫자 등을 지원합니다.

        Args:
            query: 검색어 (str)

        Returns:
            Target 또는 None
        """
        if not query or not self.targets:
            return None

        query_clean = query.strip()

        # 1) 숫자로만 검색 (예: "1")
        if query_clean.isdigit():
            target_id = int(query_clean)
            return self._find_by_id(target_id)

        # 2) "타겟 N" 패턴
        import re
        match = re.search(r"타겟\s*(\d+)", query_clean)
        if match:
            target_id = int(match.group(1))
            return self._find_by_id(target_id)

        # 3) "라벨 N" 패턴 (예: "종이컵 1")
        match = re.search(r"(.+?)\s*(\d+)\s*$", query_clean)
        if match:
            label_part = match.group(1).strip()
            number = int(match.group(2))
            # 해당 라벨의 N번째 타겟 찾기
            count = 0
            for t in self.targets:
                if label_part in t.label:
                    count += 1
                    if count == number:
                        return t

        # 4) 라벨 부분 매칭 (첫 번째 일치)
        for t in self.targets:
            if query_clean in t.label or t.label in query_clean:
                return t

        return None

    def _find_by_id(self, target_id):
        """ID로 타겟을 찾습니다."""
        for t in self.targets:
            if t.id == target_id:
                return t
        return None

    def get_all(self):
        """모든 타겟 목록을 반환합니다."""
        return list(self.targets)

    def remove_target(self, target_id):
        """타겟을 삭제합니다."""
        self.targets = [t for t in self.targets if t.id != target_id]

    def count(self):
        return len(self.targets)
