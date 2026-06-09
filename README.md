# im-not-ai

AI가 생성한 한국어 글을 자연스러운 한국어로 윤문해주는 macOS 앱

> 원본 프로젝트: [epoko77-ai/im-not-ai](https://github.com/epoko77-ai/im-not-ai)

---

## 기능

- **빠른 윤문**: 1단계 처리 — AI 특유 표현을 빠르게 교정
- **정밀 윤문**: 3단계 처리 (탐지 → 윤문 → 검증) — 정확도 우선
- **diff 보기**: 변경 전후 비교 (추가/삭제/수정 색상 구분)
- **품질 등급**: A~D 등급 및 변경률 표시
- **옵션 칩**: 격식체, 구어체, 학술체 등 문체 선택

## 탐지 카테고리

| 카테고리 | 설명 |
|---------|------|
| A | 번역투 ("~를 통해", "가지고 있다" 등) |
| B | 영어 용어 과다 |
| C | 기계적 나열 구조 (첫째/둘째) |
| D | AI 특유 관용구 ("결론적으로", "시사하는 바") |
| E | 리듬 균일성 |
| F | 수식 중복 |
| G | Hedging 과다 |
| H | 접속사 남발 |
| I | 개조식 과의존 |
| J | 과잉 친절 |

## 기술 스택

| 항목 | 내용 |
|------|------|
| 언어 | Python 3.10 |
| GUI | tkinter |
| AI | OpenRouter API — `google/gemini-2.5-flash` |
| HTTP | `urllib.request` (외부 의존성 없음) |
| 패키징 | py2app |

## 설치 및 실행

### 요구사항

- macOS
- Python 3.10+
- [OpenRouter API 키](https://openrouter.ai/)

### 소스에서 실행

```bash
python3 main.py
```

처음 실행 시 앱 우측 상단 `API 키` 버튼에서 OpenRouter API 키를 입력하세요.

### 앱 빌드

```bash
pip install py2app
python setup.py py2app
```

### DMG 생성

```bash
bash build_dmg.sh
```

## 파일 구조

```
├── main.py          # 앱 진입점 + tkinter GUI
├── api_client.py    # OpenRouter API 호출 + JSON 파싱
├── prompts.py       # 시스템/유저 프롬프트 정의
├── config.py        # API 키 저장/불러오기
├── setup.py         # py2app 빌드 설정
└── build_dmg.sh     # DMG 인스톨러 생성 스크립트
```
