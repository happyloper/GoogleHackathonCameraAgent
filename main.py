"""
main.py — AI 가상 카메라 감독 런처
=================================
⚠️ 이 파일의 전역 범위에서 PyQt5, google.genai 등을 import하면 안 됩니다!
   multiprocessing.spawn()이 이 파일을 다시 읽기 때문에,
   STT 자식 프로세스에 Qt DLL이 딸려 들어가 크래시합니다.
"""
import multiprocessing
import sys
import os


def main():
    """메인 엔트리포인트. STT 프로세스를 먼저 spawn한 뒤 UI를 시작합니다."""

    # Windows 콘솔 인코딩 설정
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("=" * 60)
    print("  JJABS Camera Director -- AI 가상 카메라 감독")
    print("=" * 60)

    # ── 1. Pipe 생성 (양방향 통신) ──
    parent_conn, child_conn = multiprocessing.Pipe()

    # ── 2. STT 워커 프로세스 시작 (PyQt5를 import하기 전에!) ──
    from modules.stt_worker import stt_process
    stt_proc = multiprocessing.Process(
        target=stt_process,
        args=(child_conn,),
        daemon=True,
    )
    stt_proc.start()
    print(f"[Main] STT 프로세스 시작됨 (PID: {stt_proc.pid})")

    # ── 3. PyQt5 UI 시작 (이 시점 이후 PyQt5 import 안전) ──
    print("[Main] UI 시작...")
    from modules.ui_main import run_ui
    run_ui(parent_conn)

    # ── 4. UI 종료 후 정리 ──
    if stt_proc.is_alive():
        stt_proc.terminate()
        stt_proc.join(timeout=3)
    print("[Main] 프로그램 종료")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
