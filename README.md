# 🎬 K-POP FanTube Automation Pipeline

> AI를 활용한 K-POP 팬튜브 쇼츠 제작 자동화 파이프라인

## 📌 프로젝트 개요

유튜브 아이돌 자체 컨텐츠 영상에서 **쇼츠 후보 클립을 자동으로 추출**하는 AI 파이프라인입니다.

기존에 수동으로 진행하던 아래 작업들을 자동화합니다.
- 수십 개의 영상을 직접 보며 재미있는 구간 기억해두기
- 여러 영상 간 엮을 수 있는 클립 조합 찾기
- 쇼츠 주제 및 제목 아이디어 도출

```
[YouTube 영상] → [음성 추출] → [자막 변환] → [AI 분석] → [쇼츠 후보 리스트]
   yt-dlp          ffmpeg        Whisper      Claude API      .txt 저장
```

## 🛠️ 기술 스택

| 역할 | 도구 | 비고 |
|------|------|------|
| 영상/음성 다운로드 | yt-dlp | 무료 |
| 음성 → 텍스트 변환 | OpenAI Whisper large-v3 | 로컬 실행 (무료) |
| AI 클립 분석 | Claude API (Anthropic) | 유료 (소액) |
| 영상 처리 | ffmpeg | 무료 |

## 💻 개발 환경

- OS: Ubuntu 22.04 (WSL2)
- GPU: NVIDIA RTX 3060 (CUDA 11.8)
- Python: 3.10

## 📦 설치 방법

```bash
# 1. 저장소 클론
git clone https://github.com/{your-username}/fantube-automation.git
cd fantube-automation

# 2. 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate

# 3. 패키지 설치
pip install yt-dlp anthropic
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install openai-whisper

# 4. ffmpeg 설치 (Ubuntu)
sudo apt install ffmpeg -y
```

## 🚀 사용 방법

```bash
# test_pipeline.py 에서 URL 설정 후 실행
python test_pipeline.py
```

`results/` 폴더에 타임스탬프 포함 자막 txt 파일이 생성됩니다.

```
[03:34 ~ 03:38] 50이라는 숫자를 내 귀에 들리게 하지 마
[16:43 ~ 16:52] 내가 만두라고 하면 만두지!
[18:31 ~ 18:35] 나 버터 고소할 거야 / 고소하니까
```

## 📁 프로젝트 구조

```
fantube-automation/
├── test_pipeline.py       # 메인 파이프라인 스크립트
├── audio/                 # 다운로드된 음성 파일 (gitignore)
├── results/               # 자막 추출 결과 txt (gitignore)
└── README.md
```

## ✅ 현재 구현 상태

- [x] yt-dlp 음성 추출
- [x] Whisper large-v3 한국어 자막 변환
- [x] 타임스탬프 포함 결과 저장
- [x] 반복 구간 자동 제거 후처리
- [ ] Claude API 쇼츠 후보 자동 분석 (진행 예정)
- [ ] 멤버별 클립 자동 태깅 (예정)
- [ ] 자막 데이터베이스 누적 구축 (예정)
- [ ] 벡터 DB 기반 클립 매칭 (예정)
- [ ] 제목/태그 자동 생성 멀티 Agent (예정)

## 📊 Whisper 성능 (RTX 3060 기준)

| 영상 길이 | 처리 시간 |
|----------|----------|
| 30분 | 약 5~10분 |

## 🗒️ 개발 노트

- 배경음악 구간에서 Whisper hallucination 발생 → `condition_on_previous_text=False` 옵션으로 완화
- 반복 텍스트는 `repeat_threshold=3` 기준으로 후처리 제거
- 아이돌 자체 콘텐츠 특유의 신조어/자체 용어 오인식 존재 (Claude 분석 시 감안 필요)

## 📝 라이선스

MIT License
