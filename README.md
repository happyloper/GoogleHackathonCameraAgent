# 🎬 AI 가상 카메라 감독 (JJABS Camera Director)

본 프로젝트는 사용자의 손가락 포인팅과 음성 명령을 결합하여 실시간으로 구도를 조정하고 타겟을 관리하는 **AI 가상 카메라 감독 시스템**입니다. 구글 해커톤을 위해 개발되었으며, Gemini 2.0 Flash Vision과 Faster-Whisper, 그리고 PyQt5를 기반으로 한 프리미엄 다크 네온 UI를 제공합니다.

---

## 🚀 시작하기

### 📦 필수 설치항목
터미널에서 아래 명령을 실행하여 필요한 라이브러리를 설치합니다.
```bash
# 가상환경이 활성화된 상태에서
venv\Scripts\pip.exe install PyQt5 google-genai obsws-python faster-whisper speechrecognition edge-tts pygame opencv-python python-dotenv numpy
```

### ⚙️ 설정 (config.py 및 .env)
- `GEMINI_API_KEY`: Google AI Studio에서 발급받은 API 키
- `OBS_HOST`, `OBS_PORT`, `OBS_PASSWORD`: OBS WebSocket 설정

### ▶️ 실행
```bash
venv\Scripts\python.exe main.py
```

---

## 🎬 시연 시나리오 (Operation Guide)

### Phase 1: 타겟 지정 (Point & Remember)
사용자가 화면 속 물체를 가리키며 음성으로 명령을 내립니다.

- **명령**: 물체를 손으로 가리키며 **"짭스, 이거 타겟 설정해 줘"**
- **동작**:
    1. Gemini Vision이 현재 화면을 분석하여 손가락이 지칭하는 물체를 찾습니다.
    2. 해당 물체 주위에 **네온 바운딩 박스**가 생기며 이름이 부여됩니다.
    3. TTS: *"종이컵을 타겟 1로 등록했습니다"*

### Phase 2: 스마트 줌 (Digital PTZ)
등록된 타겟으로 부드럽게 화면을 전환합니다.

- **줌인**: **"짭스, 종이컵 1 확대해 줘"**
    - 타겟 위치로 **스무스 줌인 애니메이션**이 동작합니다.
- **복원**: **"짭스, 원래대로"** 또는 **"구도 복원"**
    - 다시 전체 화면(풀샷)으로 **부드럽게 줌아웃**합니다.

### Phase 3: 타겟 관리
- **삭제**: **"짭스, 타겟 삭제"**
- **초기화**: **"짭스, 전부 삭제"**

---

## ✨ 핵심 기술 및 아키텍처

- **2-Process Architecture**: PyQt5(UI)와 faster-whisper(STT) 간의 Windows DLL 충돌을 방지하기 위해 `multiprocessing.Pipe`를 통한 물리적 프로세스 분리 구현.
- **Gemini 2.0 Flash Vision**: 고속 0~1000 좌표 기반 정규화된 바운딩 박스 추출 및 물체 인식.
- **Digital PTZ (LERP)**: `smoothstep` 보간을 적용한 자연스러운 줌인/줌아웃 카메라 워킹.
- **Premium UI**: 다크 테마 기반의 네온 글로우 오버레이, Glassmorphism 상태 표시줄 및 미세 애니메이션 적용.

---

## 🎤 음성 명령어 예시 (WAKE WORD: "짭스")
- *"짭스, 이거 타겟 설정"*
- *"짭스, 종이컵 1 확대"*
- *"짭스, 구도 복원"*
- *"짭스, 타겟 전부 삭제"*
