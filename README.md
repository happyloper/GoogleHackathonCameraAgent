# 🎬 AI 가상 카메라 감독 (JJABS Camera Director)

[![JJABS Humanoid Robot](https://img.youtube.com/vi/JkMVSxqGRvg/maxresdefault.jpg)](https://youtu.be/JkMVSxqGRvg)
*(↑ 클릭하여 제작 중인 로봇 영상을 확인해보세요!)*

[![JJABS Camera Director 실제 시연 영상 보기](https://img.youtube.com/vi/baLYMAm0dIQ/maxresdefault.jpg)](https://youtu.be/baLYMAm0dIQ)
*(↑ 클릭하여 해커톤 데모 시연 영상을 확인해보세요!)*

## 👋 프로젝트 배경 및 스토리

저는 **메이커**로서 위 영상과 같은 휴머노이드 로봇이나 다양한 하드웨어를 제작하는 과정을 촬영하는 일이 많습니다. 3D 프린터 출력, 정밀한 납땜, 복잡한 로봇 부품 조립 등 양손을 모두 써야 하는 작업 중에 **멀티 카메라를 전환**하거나 **특정 부품을 클로즈업**하는 것은 혼자서 감당하기 매우 힘든 일이었습니다.

"내가 작업하는 동안, 내 의도를 알아채고 알아서 카메라를 (로봇팔을 이용해) 움직여주는 조수가 있으면 어떨까?"

이런 실제 필요에서 출발하여 **Google Gemini AI**의 강력한 비전 인식과 음성 제어 기술을 결합해, **작업 중 손가락으로 가리키고 음성으로 명령하면 AI가 자동으로 카메라 타겟을 인식하고 조정해주는 촬영 보조 시스템**을 개발하게 되었습니다.

> 해커톤 현장에 실제 거대한 로봇팔과 카메라 장비를 모두 가져올 수는 없어, 이번 프로젝트에서는 **소프트웨어만으로 "타겟 지정 → AI 비전 분석 → 좌표 추출 → 타겟팅 및 로봇팔 이동 메커니즘"**을 완벽하게 구현하여 시연합니다. AI가 감지한 정확한 바운딩 박스 중심 좌표를 로봇팔 컨트롤러에 전달하면, 물리적 카메라가 자동으로 해당 물체를 스무스하게 추적하는 시스템의 핵심 두뇌 역할을 합니다.

---

## 🚀 시작하기

### 📦 설치
```bash
venv\Scripts\pip.exe install PyQt5 google-genai obsws-python faster-whisper speechrecognition edge-tts pygame opencv-python python-dotenv numpy
```

### ⚙️ 설정 (.env)
- `GEMINI_API_KEY`: Google AI Studio API 키
- `OBS_HOST`, `OBS_PORT`, `OBS_PASSWORD`: OBS WebSocket 설정

### ▶️ 실행
```bash
venv\Scripts\python.exe main.py
```

---

## 🎬 시연 시나리오

### Phase 1: 타겟 지정 (Point & Remember)
물체를 손으로 가리키며 **"짭스, 이거 타겟 설정해 줘"**
1. Gemini Vision이 손가락 방향을 분석하여 물체 감지
2. **네온 바운딩 박스** + 이름 자동 부여
3. TTS: *"종이컵을 타겟 1로 등록했습니다"*

### Phase 2: 로봇팔 이동 + 스마트 줌
**"짭스, 종이컵 확대해 줘"**
1. 🤖 타겟 위치에 **크로스헤어 타겟팅 애니메이션** 표시
2. TTS: *"로봇팔을 종이컵 위치로 이동합니다."*
3. 1.5초 후 → 해당 타겟으로 **스무스 줌인** (카메라 클로즈업)
4. **"짭스, 원래대로"** → 풀샷 복귀

### Phase 3: 타겟 관리
- **"짭스, 모든 타겟 알려줘"** → 음성으로 전체 목록 안내
- **"짭스, 타겟 삭제"** → 타겟 제거

---

## ✨ 핵심 기술

| 기술 | 설명 |
|------|------|
| **Gemini 2.5 Flash Vision** | 손가락 방향 분석 + 바운딩 박스 좌표 추출, 기등록 타겟 제외 로직 |
| **2-Process Architecture** | PyQt5(UI)와 faster-whisper(STT)의 DLL 충돌 방지를 위한 프로세스 분리 |
| **Digital PTZ** | smoothstep 보간 기반 줌인/줌아웃 카메라 워킹 |
| **로봇팔 연동 (확장)** | 타겟 좌표를 시리얼/네트워크로 로봇팔에 전송하여 물리적 카메라 제어 |
| **Premium UI** | 다크 네온 테마, 크로스헤어 타겟팅 애니메이션, Glassmorphism 상태바 |

---

## 🎤 음성 명령어 (WAKE WORD: "짭스")
- *"짭스, 이거 타겟 설정"*
- *"짭스, 종이컵 확대"*
- *"짭스, 모든 타겟 알려줘"*
- *"짭스, 구도 복원"*
- *"짭스, 타겟 삭제"*
