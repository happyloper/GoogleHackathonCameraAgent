"""
ui_main.py — 프리미엄 PyQt5 UI 메인 윈도우
다크 네온 테마 + OBS 미러링 + 바운딩 박스 오버레이 + 디지털 PTZ

⚠️ 이 모듈은 메인 프로세스에서만 import됩니다.
   STT 프로세스에서는 절대 import하지 마세요!
"""
import os
import sys
import time
import cv2
import numpy as np

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QGraphicsDropShadowEffect, QSizePolicy,
)
from PyQt5.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation,
    QEasingCurve, QRectF, QPointF,
)
from PyQt5.QtGui import (
    QImage, QPixmap, QPainter, QPen, QColor, QFont,
    QLinearGradient, QBrush, QPainterPath, QFontDatabase,
)

from config import (
    THEME, SOUND_WAKE, SOUND_START, OBS_MIRROR_FPS,
)
from modules.obs_capture import OBSCapture
from modules.vision_ai import VisionAI
from modules.target_manager import TargetManager
from modules.digital_ptz import DigitalPTZ
from modules.voice_controller import VoiceController
from modules.tts_engine import TTSEngine


# ===================================================================
# PipePollingThread — STT Pipe 수신 스레드
# ===================================================================
class PipePollingThread(QThread):
    """STT 프로세스의 Pipe를 폴링하여 메시지를 수신합니다."""
    message_received = pyqtSignal(dict)

    def __init__(self, pipe_conn, parent=None):
        super().__init__(parent)
        self.pipe_conn = pipe_conn
        self._running = True

    def run(self):
        while self._running:
            try:
                if self.pipe_conn.poll(0.5):  # 0.5초마다 체크
                    msg = self.pipe_conn.recv()
                    self.message_received.emit(msg)
            except (EOFError, BrokenPipeError):
                break
            except Exception as e:
                print(f"[Pipe] 수신 오류: {e}")

    def stop(self):
        self._running = False


# ===================================================================
# GeminiWorkerThread — Gemini Vision API 비동기 호출
# ===================================================================
class GeminiWorkerThread(QThread):
    """Gemini Vision API를 별도 스레드에서 호출합니다."""
    result_ready = pyqtSignal(object)  # dict 또는 None

    def __init__(self, vision_ai, frame, existing_bboxes=None, parent=None):
        super().__init__(parent)
        self.vision_ai = vision_ai
        self.frame = frame
        self.existing_bboxes = existing_bboxes

    def run(self):
        result = self.vision_ai.detect_pointed_object(self.frame, self.existing_bboxes)
        self.result_ready.emit(result)


# ===================================================================
# VideoWidget — OBS 프레임 렌더링 + 오버레이 + PTZ
# ===================================================================
class VideoWidget(QWidget):
    """OBS 미러링 프레임을 렌더링하고 바운딩 박스 오버레이를 표시합니다."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_frame = None  # QImage
        self.targets = []  # TargetManager.get_all() 결과
        self.show_overlay = True
        self.overlay_opacity = 1.0
        self._glow_phase = 0.0  # 글로우 애니메이션 위상
        self.actual_frame_w = 1280  # 실제 프레임 너비
        self.actual_frame_h = 720   # 실제 프레임 높이
        self.setMinimumSize(640, 360)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def update_frame(self, qimage):
        """새 프레임으로 업데이트합니다."""
        self.current_frame = qimage
        self._glow_phase += 0.05
        if self._glow_phase > 6.28:
            self._glow_phase = 0.0
        self.update()

    def set_targets(self, targets):
        """오버레이에 표시할 타겟 목록을 설정합니다."""
        self.targets = targets

    def paintEvent(self, event):
        """프레임과 오버레이를 그립니다."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        # 배경
        painter.fillRect(self.rect(), QColor(THEME["bg_primary"]))

        if self.current_frame is None:
            self._draw_waiting_screen(painter)
            return

        # 프레임 그리기 (위젯 크기에 맞게 스케일)
        scaled = self.current_frame.scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        x_offset = (self.width() - scaled.width()) // 2
        y_offset = (self.height() - scaled.height()) // 2
        painter.drawImage(x_offset, y_offset, scaled)

        # 바운딩 박스 오버레이
        if self.show_overlay and self.targets:
            self._draw_targets(painter, scaled.width(), scaled.height(), x_offset, y_offset)

        painter.end()

    def _draw_waiting_screen(self, painter):
        """연결 대기 화면을 그립니다."""
        painter.setPen(QColor(THEME["text_secondary"]))
        font = QFont("Segoe UI", 18)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignCenter, "📡 OBS 연결 대기 중...")

    def _draw_targets(self, painter, view_w, view_h, x_off, y_off):
        """타겟 바운딩 박스와 라벨을 그립니다."""
        # 실제 프레임 해상도 기준으로 스케일링
        ref_w = self.actual_frame_w
        ref_h = self.actual_frame_h

        for target in self.targets:
            bbox = target.bbox  # [x1, y1, x2, y2] 원본 해상도 기준
            color = QColor(target.color)

            # 원본 해상도 → 화면 위젯 좌표 변환
            scale_x = view_w / ref_w
            scale_y = view_h / ref_h

            sx1 = int(bbox[0] * scale_x) + x_off
            sy1 = int(bbox[1] * scale_y) + y_off
            sx2 = int(bbox[2] * scale_x) + x_off
            sy2 = int(bbox[3] * scale_y) + y_off

            # ── 글로우 이펙트 (외부 광선) ──
            import math
            glow_intensity = 0.5 + 0.5 * math.sin(self._glow_phase)
            glow_alpha = int(40 + 60 * glow_intensity)

            for i in range(3, 0, -1):
                glow_color = QColor(color)
                glow_color.setAlpha(glow_alpha // i)
                glow_pen = QPen(glow_color, i * 2 + 1)
                painter.setPen(glow_pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawRoundedRect(
                    sx1 - i * 2, sy1 - i * 2,
                    (sx2 - sx1) + i * 4, (sy2 - sy1) + i * 4,
                    4, 4
                )

            # ── 메인 바운딩 박스 ──
            main_pen = QPen(color, 2.5)
            painter.setPen(main_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(sx1, sy1, sx2 - sx1, sy2 - sy1, 3, 3)

            # ── 코너 마커 (L자 형태) ──
            corner_len = min(20, (sx2 - sx1) // 4, (sy2 - sy1) // 4)
            thick_pen = QPen(color, 3.5)
            painter.setPen(thick_pen)
            # 좌상단
            painter.drawLine(sx1, sy1, sx1 + corner_len, sy1)
            painter.drawLine(sx1, sy1, sx1, sy1 + corner_len)
            # 우상단
            painter.drawLine(sx2, sy1, sx2 - corner_len, sy1)
            painter.drawLine(sx2, sy1, sx2, sy1 + corner_len)
            # 좌하단
            painter.drawLine(sx1, sy2, sx1 + corner_len, sy2)
            painter.drawLine(sx1, sy2, sx1, sy2 - corner_len)
            # 우하단
            painter.drawLine(sx2, sy2, sx2 - corner_len, sy2)
            painter.drawLine(sx2, sy2, sx2, sy2 - corner_len)

            # ── 라벨 배경 (반투명 글래스) ──
            label_text = target.display_name
            font = QFont("Segoe UI Semibold", 11)
            painter.setFont(font)
            fm = painter.fontMetrics()
            text_w = fm.horizontalAdvance(label_text) + 16
            text_h = fm.height() + 8

            label_x = sx1
            label_y = sy1 - text_h - 4

            # 글래스 배경
            glass_color = QColor(0, 0, 0, 160)
            painter.setPen(Qt.NoPen)
            painter.setBrush(glass_color)
            painter.drawRoundedRect(label_x, label_y, text_w, text_h, 4, 4)

            # 라벨 위 색상 바
            painter.setBrush(color)
            painter.drawRect(label_x, label_y, 3, text_h)

            # 라벨 텍스트
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(
                label_x + 10, label_y + 4,
                text_w - 12, text_h - 4,
                Qt.AlignVCenter | Qt.AlignLeft,
                label_text
            )


# ===================================================================
# StatusBarWidget — 하단 상태바 (글래스모피즘)
# ===================================================================
class StatusBarWidget(QWidget):
    """하단 상태 표시 바"""

    STATE_STYLES = {
        "idle": {"icon": "💤", "text": "대기 중 · \"짭스\"라고 불러주세요", "color": "#4a5568"},
        "ready": {"icon": "🟢", "text": "음성 인식 준비 완료", "color": "#00ff88"},
        "wake_detected": {"icon": "🔔", "text": "호출어 감지! 명령을 말씀해주세요", "color": "#00f5ff"},
        "listening_command": {"icon": "🎧", "text": "명령 듣는 중...", "color": "#ff006e"},
        "processing": {"icon": "⚙️", "text": "AI 분석 중...", "color": "#ffbe0b"},
        "zoom_in": {"icon": "🔍", "text": "줌인", "color": "#00f5ff"},
        "zoom_out": {"icon": "🔭", "text": "구도 복원 중...", "color": "#8b5cf6"},
        "target_set": {"icon": "✅", "text": "타겟 등록 완료!", "color": "#00ff88"},
        "error": {"icon": "❌", "text": "오류 발생", "color": "#ff006e"},
        "timeout": {"icon": "⏳", "text": "시간 초과 — 대기 모드로 복귀", "color": "#4a5568"},
        "not_recognized": {"icon": "⚠️", "text": "명령을 인식하지 못했습니다", "color": "#ffbe0b"},
        "loading_stt": {"icon": "⏳", "text": "STT 모델 로딩 중...", "color": "#ffbe0b"},
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(70)
        self.state = "idle"
        self.target_count = 0
        self.last_command = ""
        self._pulse_phase = 0.0

    def set_state(self, state, extra_text=None):
        """상태를 변경합니다."""
        self.state = state
        if extra_text:
            self.last_command = extra_text
        self.update()

    def set_target_count(self, count):
        self.target_count = count
        self.update()

    def paintEvent(self, event):
        import math
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # ── 글래스 배경 ──
        bg = QColor(15, 15, 26, 220)
        painter.setPen(Qt.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(4, 0, self.width() - 8, self.height() - 4, 12, 12)

        # ── 상단 라인 (악센트 색상) ──
        style = self.STATE_STYLES.get(self.state, self.STATE_STYLES["idle"])
        accent = QColor(style["color"])

        self._pulse_phase += 0.03
        pulse = 0.6 + 0.4 * math.sin(self._pulse_phase)
        accent.setAlpha(int(255 * pulse))

        line_pen = QPen(accent, 2)
        painter.setPen(line_pen)
        painter.drawLine(20, 2, self.width() - 20, 2)

        # ── 아이콘 + 상태 텍스트 ──
        painter.setPen(QColor(255, 255, 255))
        font_main = QFont("Segoe UI", 13)
        font_main.setBold(True)
        painter.setFont(font_main)

        status_text = f"{style['icon']}  {style['text']}"
        painter.drawText(24, 18, self.width() - 48, 28, Qt.AlignVCenter | Qt.AlignLeft, status_text)

        # ── 타겟 카운트 (우측) ──
        font_count = QFont("Segoe UI Semibold", 11)
        painter.setFont(font_count)
        painter.setPen(QColor(THEME["text_secondary"]))
        count_text = f"🎯 Targets: {self.target_count}"
        painter.drawText(24, 18, self.width() - 48, 28, Qt.AlignVCenter | Qt.AlignRight, count_text)

        # ── 마지막 명령 텍스트 ──
        if self.last_command:
            font_cmd = QFont("Segoe UI", 10)
            painter.setFont(font_cmd)
            painter.setPen(QColor(THEME["text_secondary"]))
            cmd_text = f"🎙 마지막 인식: \"{self.last_command}\""
            painter.drawText(24, 42, self.width() - 48, 22, Qt.AlignVCenter | Qt.AlignLeft, cmd_text)

        painter.end()


# ===================================================================
# CameraDirectorWindow — 메인 윈도우
# ===================================================================
class CameraDirectorWindow(QMainWindow):
    """AI 가상 카메라 감독 메인 윈도우"""

    def __init__(self, pipe_conn):
        super().__init__()
        self.pipe_conn = pipe_conn

        # ── 모듈 초기화 ──
        self.obs = OBSCapture()
        self.vision = VisionAI()
        self.targets = TargetManager()
        self.ptz = DigitalPTZ()
        self.voice_ctrl = VoiceController()
        self.tts = TTSEngine()

        self._gemini_thread = None
        self._current_capture_frame = None  # Gemini 호출 시 사용할 원본 프레임

        self._setup_ui()
        self._setup_timers()
        self._setup_pipe_thread()
        self._connect_obs()

    def _setup_ui(self):
        """UI 레이아웃 구성"""
        self.setWindowTitle("🎬 JJABS Camera Director")
        self.setMinimumSize(1024, 640)
        self.resize(1280, 780)

        # 다크 테마 스타일시트
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {THEME['bg_primary']};
            }}
            QWidget {{
                background-color: transparent;
                color: {THEME['text_primary']};
            }}
        """)

        # 중앙 위젯
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        # ── 타이틀 바 ──
        title_bar = QHBoxLayout()
        title_label = QLabel("🎬 JJABS Camera Director")
        title_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title_label.setStyleSheet(f"color: {THEME['accent_cyan']}; padding: 4px;")
        title_bar.addWidget(title_label)
        title_bar.addStretch()

        # 상태 인디케이터
        self.connection_label = QLabel("● OBS 연결 중...")
        self.connection_label.setFont(QFont("Segoe UI", 10))
        self.connection_label.setStyleSheet(f"color: {THEME['accent_yellow']};")
        title_bar.addWidget(self.connection_label)

        layout.addLayout(title_bar)

        # ── 비디오 위젯 ──
        self.video_widget = VideoWidget()
        layout.addWidget(self.video_widget, stretch=1)

        # ── 하단 상태바 ──
        self.status_bar = StatusBarWidget()
        layout.addWidget(self.status_bar)

    def _setup_timers(self):
        """프레임 갱신 타이머 설정"""
        self.frame_timer = QTimer()
        self.frame_timer.timeout.connect(self._update_frame)
        # OBS_MIRROR_FPS 기준 (기본 10fps → 100ms 간격)
        self.frame_timer.start(max(30, 1000 // OBS_MIRROR_FPS))

        # 상태바 펄스 애니메이션
        self.pulse_timer = QTimer()
        self.pulse_timer.timeout.connect(self.status_bar.update)
        self.pulse_timer.start(50)

    def _setup_pipe_thread(self):
        """STT Pipe 폴링 스레드 시작"""
        if self.pipe_conn is None:
            print("[UI] Pipe connection is None. STT disabled.")
            return
        self.pipe_thread = PipePollingThread(self.pipe_conn)
        self.pipe_thread.message_received.connect(self._on_stt_message)
        self.pipe_thread.start()
        self.status_bar.set_state("loading_stt")


    def _connect_obs(self):
        """OBS에 연결합니다."""
        if self.obs.connect():
            self.connection_label.setText("● OBS 연결됨")
            self.connection_label.setStyleSheet(f"color: {THEME['accent_green']};")
        else:
            self.connection_label.setText("● OBS 연결 실패")
            self.connection_label.setStyleSheet(f"color: {THEME['accent_magenta']};")

    # ── 프레임 갱신 루프 ──
    def _update_frame(self):
        """OBS에서 프레임을 캡처하고 PTZ를 적용하여 화면에 표시합니다."""
        frame = self.obs.capture_frame()
        if frame is None:
            return

        # 원본 프레임 보관 (Gemini 타겟 감지용)
        self._current_capture_frame = frame.copy()

        # 실제 프레임 해상도 저장 (좌표 변환에 사용)
        orig_h, orig_w = frame.shape[:2]
        self.video_widget.actual_frame_w = orig_w
        self.video_widget.actual_frame_h = orig_h

        # PTZ 애니메이션 업데이트 및 적용
        self.ptz.update()
        processed_frame = self.ptz.apply_view(frame)

        # 줌인 상태에서는 오버레이 숨기기, 풀샷에서는 표시
        self.video_widget.show_overlay = not self.ptz.is_zoomed

        # OpenCV BGR → QImage RGB
        h, w, ch = processed_frame.shape
        bytes_per_line = ch * w
        qimg = QImage(processed_frame.data, w, h, bytes_per_line, QImage.Format_BGR888)

        self.video_widget.update_frame(qimg)

    # ── STT Pipe 메시지 처리 ──
    def _on_stt_message(self, msg):
        """STT 프로세스로부터 받은 메시지를 처리합니다."""
        msg_type = msg.get("type")

        if msg_type == "status":
            status = msg.get("status")
            if status == "ready":
                self.status_bar.set_state("idle")
                self.tts.play_sound_async(SOUND_START)
            elif status == "wake_detected":
                self.status_bar.set_state("wake_detected")
                self.tts.play_sound_async(SOUND_WAKE)
            elif status == "listening_command":
                self.status_bar.set_state("listening_command")
            elif status == "timeout":
                self.status_bar.set_state("timeout")
                QTimer.singleShot(2000, lambda: self.status_bar.set_state("idle"))
            elif status == "not_recognized":
                self.status_bar.set_state("not_recognized")
                QTimer.singleShot(2000, lambda: self.status_bar.set_state("idle"))

        elif msg_type == "command":
            command_text = msg.get("text", "")
            self.status_bar.set_state("processing", extra_text=command_text)
            self._execute_command(command_text)

        elif msg_type == "terminate":
            self.close()

    def _execute_command(self, text):
        """파싱된 명령을 실행합니다."""
        parsed = self.voice_ctrl.parse_command(text)
        action = parsed["action"]

        if action == "set_target":
            self._cmd_set_target()
        elif action == "zoom_in":
            self._cmd_zoom_in(parsed.get("target"))
        elif action == "reset_view":
            self._cmd_reset_view()
        elif action == "remove_target":
            self._cmd_remove_target(parsed.get("target"))
        else:
            self.status_bar.set_state("not_recognized", extra_text=text)
            self.tts.speak_async("명령을 이해하지 못했습니다.")
            QTimer.singleShot(2000, lambda: self.status_bar.set_state("idle"))

    def _cmd_set_target(self):
        """타겟 설정 명령: Gemini Vision으로 손가락이 가리키는 객체를 감지"""
        if self._current_capture_frame is None:
            self.tts.speak_async("카메라 프레임이 없습니다.")
            return

        self.status_bar.set_state("processing")

        # 이미 등록된 타겟 bbox 수집 (중복 감지 방지)
        existing_bboxes = [t.bbox for t in self.targets.get_all()]

        # Gemini API를 별도 스레드에서 호출
        self._gemini_thread = GeminiWorkerThread(
            self.vision, self._current_capture_frame, existing_bboxes
        )
        self._gemini_thread.result_ready.connect(self._on_target_detected)
        self._gemini_thread.start()

    def _on_target_detected(self, result):
        """Gemini 감지 결과를 처리합니다."""
        if result is None:
            self.status_bar.set_state("error")
            self.tts.speak_async("물체를 감지하지 못했습니다. 다시 시도해주세요.")
            QTimer.singleShot(2000, lambda: self.status_bar.set_state("idle"))
            return

        # 타겟 등록
        target = self.targets.add_target(result["label"], result["bbox"])
        self.video_widget.set_targets(self.targets.get_all())
        self.status_bar.set_target_count(self.targets.count())
        self.status_bar.set_state("target_set")

        self.tts.speak_async(f"{result['label']}을 타겟 {target.id}로 등록했습니다.")
        QTimer.singleShot(3000, lambda: self.status_bar.set_state("idle"))

    def _cmd_zoom_in(self, target_query):
        """줌인 명령"""
        if not target_query:
            # 타겟 지정 없이 "확대"만 한 경우 → 첫 번째 타겟
            all_targets = self.targets.get_all()
            if all_targets:
                target = all_targets[0]
            else:
                self.tts.speak_async("등록된 타겟이 없습니다.")
                return
        else:
            target = self.targets.get_target(target_query)
            if not target:
                self.tts.speak_async(f"{target_query}을 찾을 수 없습니다.")
                return

        self.status_bar.set_state("zoom_in", extra_text=target.display_name)
        self.ptz.zoom_to(target.bbox, duration=0.8)
        self.tts.speak_async(f"{target.display_name}으로 줌인합니다.")
        QTimer.singleShot(2000, lambda: self.status_bar.set_state("idle"))

    def _cmd_reset_view(self):
        """구도 복원 명령"""
        self.status_bar.set_state("zoom_out")
        self.ptz.reset_view(duration=0.8)
        self.tts.speak_async("구도를 복원합니다.")
        QTimer.singleShot(1000, lambda: self.status_bar.set_state("idle"))

    def _cmd_remove_target(self, target_query):
        """타겟 삭제 명령"""
        if not target_query:
            self.tts.speak_async("삭제할 타겟을 지정해주세요.")
            return

        target = self.targets.get_target(target_query)
        if target:
            self.targets.remove_target(target.id)
            self.video_widget.set_targets(self.targets.get_all())
            self.status_bar.set_target_count(self.targets.count())
            self.tts.speak_async(f"{target.display_name}을 삭제했습니다.")
        else:
            self.tts.speak_async(f"{target_query}을 찾을 수 없습니다.")

    def closeEvent(self, event):
        """윈도우 종료 시 리소스 정리"""
        # STT 프로세스에 종료 신호 전송
        try:
            if self.pipe_conn:
                self.pipe_conn.send({"type": "shutdown"})
        except Exception:
            pass

        if hasattr(self, 'pipe_thread'):
            self.pipe_thread.stop()
            self.pipe_thread.wait(2000)
        self.frame_timer.stop()
        self.pulse_timer.stop()
        self.obs.disconnect()
        event.accept()


# ===================================================================
# run_ui — UI 실행 함수 (main.py에서 호출)
# ===================================================================
def run_ui(pipe_conn):
    """PyQt5 UI를 시작합니다."""
    app = QApplication(sys.argv)

    # 기본 폰트 설정
    app.setFont(QFont("Segoe UI", 10))

    window = CameraDirectorWindow(pipe_conn)
    window.show()
    sys.exit(app.exec_())
