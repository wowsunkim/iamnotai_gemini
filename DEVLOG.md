# im-not-ai Mac App 개발 일지

> **원본 프로젝트**: https://github.com/epoko77-ai/im-not-ai  
> **버전**: v2.0  
> **플랫폼**: macOS (Intel x86_64)  
> **AI 백엔드**: OpenRouter API — `google/gemini-2.0-flash-001`

---

## 목차

1. [원본 프로젝트 분석](#1-원본-프로젝트-분석)
2. [프로젝트 구조](#2-프로젝트-구조)
3. [기술 스택](#3-기술-스택)
4. [기능 구현 과정](#4-기능-구현-과정)
5. [UI 개선 과정](#5-ui-개선-과정)
6. [버그 수정 내역](#6-버그-수정-내역)
7. [빌드 및 배포](#7-빌드-및-배포)
8. [파일 설명](#8-파일-설명)
9. [실행 및 빌드 방법](#9-실행-및-빌드-방법)

---

## 1. 원본 프로젝트 분석

### 개요

`im-not-ai`는 Claude Code 기반 **한국어 AI 글 윤문 스킬**이다.  
ChatGPT, Claude, Gemini 등 AI가 생성한 한국어 글의 "번역투", "기계적 표현", "AI 특유 관용구"를 탐지하고 내용은 보존하면서 자연스러운 한글로 개선한다.

### 핵심 원칙

- **의미 불변**: 사실·수치·고유명사·직접 인용 100% 원문 보존
- **외과적 수정**: 탐지된 구간만 최소 수정
- **변경률 제한**: 30% 초과 경고, 50% 초과 강제 중단

### 10대 탐지 카테고리

| 카테고리 | 설명 | 심각도 |
|---------|------|--------|
| A | 번역투 ("~를 통해", "가지고 있다" 등) | S1~S2 |
| B | 영어 인용·용어 과다 | S2 |
| C | 기계적 구조 (첫째/둘째 나열) | S1~S2 |
| D | AI 특유 관용구 ("결론적으로", "시사하는 바") | S1 |
| E | 리듬 균일성 | S2 |
| F | 수식 중복 | S2 |
| G | Hedging 과다 | S2 |
| H | 접속사 남발 | S2 |
| I | 개조식 과의존 | S2 |
| J | 과잉 친절 | S1 |

**심각도 기준**
- S1: 발견 즉시 무조건 제거
- S2: 문맥 판단 후 수정
- S3: 권고 수준 (선택적)

---

## 2. 프로젝트 구조

```
iamnotai_gemini/
├── main.py          # 앱 진입점 + tkinter GUI
├── api_client.py    # OpenRouter API 호출 + JSON 파싱
├── prompts.py       # system/user prompt 정의 + 옵션 addon
├── config.py        # API 키 저장/불러오기 (~/.config/iamnotai/)
├── make_icon.py     # 앱 아이콘 생성 (Pillow 기반)
├── setup.py         # py2app 빌드 설정
├── build_dmg.sh     # DMG 인스톨러 생성 스크립트
├── requirements.txt # 의존성 (py2app)
├── icon.icns        # 앱 아이콘 (macOS 번들용)
├── icon_preview.png # 아이콘 미리보기
└── dist/
    ├── im-not-ai.app      # 빌드된 앱 번들 (27MB)
    └── im-not-ai-1.0.dmg  # 배포용 DMG (13MB)
```

---

## 3. 기술 스택

| 항목 | 내용 |
|------|------|
| 언어 | Python 3.10 |
| GUI | tkinter (표준 라이브러리) |
| AI | OpenRouter API → `google/gemini-2.0-flash-001` |
| HTTP | `urllib.request` (외부 의존성 없음) |
| 패키징 | py2app 0.28.10 |
| 아이콘 | Pillow + iconutil |
| 폰트 | Helvetica Neue (UI), Apple SD Gothic Neo (본문) |

---

## 4. 기능 구현 과정

### 4-1. 핵심 API 모듈 (`api_client.py`)

#### OpenRouter 호출

```python
MODEL = "google/gemini-2.0-flash-001"

def _call_api(api_key, system_prompt, user_prompt) -> str:
    # urllib.request로 POST 요청
    # Authorization: Bearer {api_key}
    # HTTP-Referer, X-Title 헤더 포함
```

> 초기에 모델 ID를 `google/gemini-2.0-flash`로 지정했으나  
> OpenRouter에서 `google/gemini-2.0-flash-001`이 올바른 ID임을 확인하여 수정.

#### JSON 파싱 강화

Gemini가 `reason` 필드에 큰따옴표를 이스케이프 없이 출력하는 문제를 발견:

```
"reason": "~를 통해" 삭제 (번역투 표현 제거)
           ↑ 이 따옴표가 JSON을 깨뜨림
```

**해결**: 상태머신 기반 `_fix_unescaped_quotes()` 함수 구현

```python
def _fix_unescaped_quotes(s: str) -> str:
    """JSON 문자열 값 안의 이스케이프되지 않은 큰따옴표를 수정."""
    # 문자 단위로 파싱하여 문자열 내부의 비이스케이프 따옴표를 \"로 변환
```

**3단계 fallback 파서**:
1. 정상 파싱 시도
2. `{` ~ `}` 범위 추출 후 재시도
3. `_fix_unescaped_quotes` 적용 후 재시도

#### 프롬프트에서 따옴표 사용 금지 지시 추가

```
중요: reason 필드에 원문을 인용할 때 큰따옴표(" ") 대신 꺾쇠(「」)를 사용하세요.
```

### 4-2. 윤문 모드

#### 빠른 윤문 (Fast Mode)

- 단일 API 호출
- 5,000자 이하 권장
- 탐지 + 윤문 + 검증을 한 번에 처리
- 응답: JSON `{rewritten, patterns, grade, change_rate, summary}`

#### 정밀 윤문 (Strict Mode)

3단계 파이프라인:

```
1단계: ai-tell-detector   → 패턴 탐지 (span 단위)
2단계: korean-style-rewriter → 수술적 윤문
3단계: content-fidelity-auditor → 의미 동등성 검증 + 등급 산정
```

### 4-3. 정밀 윤문 옵션 (`prompts.py`)

**옵션 구조체**:
```python
options = {
    "sensitivity": "S1만" | "S1+S2" | "전체",
    "genre":       "일반" | "학술" | "비즈니스" | "SNS",
    "change_limit": "30%" | "50%",
}
```

`build_options_addon(options)` 함수가 시스템 프롬프트 말미에 붙는 지시문을 생성한다.

### 4-4. 설정 저장 (`config.py`)

API 키를 `~/.config/iamnotai/config.json`에 JSON으로 저장.  
환경변수 `OPENROUTER_API_KEY`도 지원 (우선순위 높음).

### 4-5. 총평 생성

```python
def _build_review(data: dict) -> str:
    # 등급 설명, 변경률, S1/S2 건수, 필수 제거 카테고리, 경고, AI 평가 요약
```

**등급 기준**:
- **A**: S1 없음, S2 ≤2건, 개선 70%+
- **B**: S1 없음, S2 ≤4건, 개선 50%+
- **C**: S1 1~2건 또는 과윤문 신호
- **D**: S1 3건+ → 사람 검토 권고

---

## 5. UI 개선 과정

### 5-1. 커스텀 위젯

#### `RoundedButton` — 좌우 둥근 pill 형태 버튼

```python
class RoundedButton(tk.Canvas):
    # tkfont로 텍스트 크기 측정 → Canvas에 pill 모양 그리기
    # hover: _lighten()으로 밝게, disabled: 회색
    # 내부 변수명 _bw/_bh (tkinter의 self._w와 충돌 방지!)
```

> **함정**: tkinter 내부적으로 `self._w`를 위젯 경로명으로 사용한다.  
> `self._w` → `self._bw`로 이름 변경하여 해결.

#### `Chip` — 옵션 선택 토글 칩

선택 상태에 따라 보라색(`#7c6af7`) / 어두운 배경(`#363650`)으로 redraw.

#### `Tooltip` — 마우스 오버 툴팁

```python
class Tooltip:
    DELAY = 500   # ms 대기 후 표시
    # 화면 오른쪽 밖으로 나가지 않도록 위치 자동 보정
```

탐지 범위 chip 3개에 각각 툴팁 연결:
- `S1만` → "심각(S1) 패턴만 처리\n최소한의 수정, 원문 보존 우선"
- `S1+S2` → "심각(S1)과 중간(S2) 패턴 처리\n균형 잡힌 기본 설정"
- `전체` → "S1·S2에 S3(권고) 패턴까지 포함\n가장 꼼꼼한 윤문"

#### `OverlayScrollbar` — 마우스 스크롤 시 나타나는 오버레이 스크롤바

```python
class OverlayScrollbar:
    # Canvas로 오른쪽 끝에 얇은(4px) 보라색 썸 표시
    # 1200ms 후 자동 소멸
    # yview_scroll(delta, "units") 으로 Treeview/Canvas 모두 지원
```

### 5-2. 레이아웃 구조

```
┌─────────────────────────────────────────────────┐
│  헤더: im-not-ai  AI 글투 탐지 · 한국어 윤문기  │
├─────────────────┬───────────────────────────────┤
│  입력 텍스트    │  윤문 결과                     │
│  (50%)          │  (50%)  [복사] [저장]          │
│                 │                                │
│  [지우기]       │                                │
│  [빠른 윤문 ▶] │                                │
│  [정밀 윤문]    │                                │
│  [옵션 ▾]      │                                │
│  ┌─ 옵션패널 ─┐│                                │
│  │탐지범위 chips│                               │
│  │장르 chips  ││                                │
│  │변경상한    ││                                │
│  └───────────┘│                                │
├─────────────────┴───────────────────────────────┤
│  수정 내용  [추가][삭제][변경]  [수정 내용 보기▾]│
│  ┌─ 스크롤 가능 영역 (260px) ──────────────────┐│
│  │  diff (추가=초록/삭제=빨강취소선/변경=주황)  ││
│  │  ─────────────────────────────────────────  ││
│  │  총평: 등급·변경률·S1/S2 건수·AI 평가        ││
│  └─────────────────────────────────────────────┘│
├─────────────────────────────────────────────────┤
│  상태 표시줄                                     │
└─────────────────────────────────────────────────┘
```

**50/50 동일 너비 보장**:

```python
main.columnconfigure(0, weight=1, uniform="col")
main.columnconfigure(1, weight=1, uniform="col")
```

> `uniform="col"` 옵션이 핵심 — weight만으로는 최소 크기 차이로 비대칭이 생긴다.

### 5-3. 폰트

| 용도 | 폰트 |
|------|------|
| UI 레이블·버튼 | Helvetica Neue |
| 한국어 본문 (입력/출력창) | Apple SD Gothic Neo |

### 5-4. 색상 팔레트

```python
BG        = "#1e1e2e"   # 배경
PANEL     = "#2a2a3e"   # 패널
ACCENT    = "#b39ddb"   # 빠른 윤문 버튼 (연보라)
ACCENT2   = "#4fc3f7"   # 정밀 윤문 버튼 (하늘)
BTN_FG    = "#12122a"   # 버튼 텍스트 (어두운 남색, 최대 대비)
TEXT      = "#cdd6f4"   # 본문 텍스트
SUBTEXT   = "#6c7086"   # 보조 텍스트
INPUT_BG  = "#181825"   # 입력창 배경

# diff 색상
DIFF_ADD_FG = "#69ff94"  # 추가 (초록)
DIFF_DEL_FG = "#ff6e6e"  # 삭제 (빨강, 취소선)
DIFF_CHG_FG = "#ffd580"  # 변경 (주황)
```

### 5-5. diff 렌더링

`difflib.SequenceMatcher`로 단어 단위 비교:

```python
for tag, i1, i2, j1, j2 in matcher.get_opcodes():
    if tag == "equal":   → 일반 텍스트
    if tag == "insert":  → diff_add 태그 (초록)
    if tag == "delete":  → diff_del 태그 (빨강 + 취소선)
    if tag == "replace": → 원문은 diff_del, 신문은 diff_chg (주황)
```

### 5-6. 수정 내용 패널 스크롤

내용이 길어 잘리는 문제를 Canvas + OverlayScrollbar로 해결:

```python
# 고정 높이 260px Canvas
self._changes_canvas = tk.Canvas(..., height=260)

# changes_body를 Canvas window로 삽입
self._body_win = self._changes_canvas.create_window(
    (0, 0), window=self.changes_body, anchor="nw")

# Configure 이벤트로 scrollregion + width 동기화
self.changes_body.bind("<Configure>", _on_body_resize)
self._changes_canvas.bind("<Configure>", _on_canvas_resize)
```

### 5-7. 총평 표시 (macOS disabled 색상 문제)

macOS에서 `tk.Text(state="disabled")`는 시스템이 `fg` 색상을 강제로 회색으로 덮어쓴다.

**해결**: `review_text`를 `tk.Text` → `tk.Label`로 교체

```python
self.review_text = tk.Label(
    self.changes_body, text="",
    font=(FONT_KO, 11), fg=TEXT, bg=CHANGES_BG,
    anchor="w", justify="left", wraplength=980,
)
# 결과 반영 시
self.review_text.config(text=review)
```

### 5-8. About 메뉴

macOS 앱 메뉴(`name="apple"`)에 `im-not-ai 정보...` 추가.

다이얼로그 구성:
- 앱 아이콘 미리보기 (있는 경우)
- **im-not-ai** (22pt bold, 보라색)
- **v2.0** (12pt, 회색)
- 구분선
- URL 클릭 시 브라우저 열기 (`subprocess.Popen(["open", url])`)
- 확인 버튼

### 5-9. 정밀 윤문 옵션 패널

`옵션 ▾` 버튼으로 접이식 패널 토글:

```
탐지 범위: [S1만] [S1+S2 ●] [전체]
           ↳ 선택한 항목의 설명이 파란색으로 즉시 표시

장르:      [일반 ●] [학술] [비즈니스] [SNS]

변경 상한: [30% ●] [50%]
```

---

## 6. 버그 수정 내역

### #1 `self._w` tkinter 내부 속성 충돌

**현상**: `RoundedButton` 생성 시 `TypeError: unsupported operand type(s) for -: 'str' and 'int'`

**원인**: tkinter `BaseWidget.__init__`이 `self._w`를 위젯 경로명(문자열)으로 덮어씀

**수정**: `self._w`, `self._h` → `self._bw`, `self._bh`로 rename

---

### #2 OpenRouter 모델 ID 오류

**현상**: `HTTP 400: google/gemini-2.0-flash is not a valid model ID`

**수정**: `"google/gemini-2.0-flash"` → `"google/gemini-2.0-flash-001"`

---

### #3 JSON 파싱 실패 (따옴표 미이스케이프)

**현상**: 긴 텍스트 윤문 시 `json.decoder.JSONDecodeError: Expecting ',' delimiter`

**원인**: Gemini가 `reason` 값 안에 `"` 를 이스케이프 없이 출력

```
"reason": "「~를 통해」 삭제 ("번역투" 제거)"
                              ↑ 여기서 JSON 깨짐
```

**수정**:
1. 상태머신 기반 `_fix_unescaped_quotes()` 파서 추가
2. 시스템 프롬프트에 꺾쇠(`「」`) 사용 지시 추가

---

### #4 `changes_body.pack(before=self.lbl_status)` 실패

**현상**: `수정 내용 보기` 버튼 클릭해도 아무것도 안 보임

**원인**: `before=self.lbl_status`에서 `lbl_status`가 `outer`가 아닌 `self`(루트)의 자식이라 다른 부모를 참조

**수정**: `before=` 파라미터 제거 → `self.changes_body.pack(fill="x")`

---

### #5 총평 텍스트가 보이지 않음

**현상**: 수정 내용 패널을 열어도 총평 영역이 안 보이거나 빈 것처럼 보임

**원인 1**: 창 높이 초과로 총평 영역이 화면 아래로 잘림  
**해결 1**: `changes_body`를 고정 높이 260px Canvas로 래핑, 내부 스크롤 적용

**원인 2**: macOS에서 `tk.Text(state="disabled")` 위젯의 텍스트 색상이 시스템에 의해 강제 회색 처리  
**해결 2**: `tk.Text` → `tk.Label`로 교체

---

### #6 py2app 빌드 후 `libffi.8.dylib` 누락

**현상**: `.app` 실행 시 `Library not loaded: @rpath/libffi.8.dylib`

**원인**: conda 환경의 dylib를 py2app이 자동 탐지하지 못함

**수정**: `setup.py`에 `frameworks` 옵션 명시

```python
"frameworks": [
    "~/pinokio/bin/miniconda/lib/libffi.8.dylib",
    "~/pinokio/bin/miniconda/lib/libtcl8.6.dylib",
    "~/pinokio/bin/miniconda/lib/libtk8.6.dylib",
],
```

---

## 7. 빌드 및 배포

### 7-1. 앱 아이콘 생성 (`make_icon.py`)

Pillow로 1024×1024 PNG 생성 후 `iconutil`로 `.icns` 변환.

**디자인**: 보라 그라디언트 원형 배경 + 흰 붓대 + 황금 잉크 글로우 + 한글 획 3개

```python
# macOS 요구 크기: 16, 32, 64, 128, 256, 512, 1024 + @2x (Retina)
sizes = [16, 32, 64, 128, 256, 512, 1024]
for s in sizes:
    draw_icon(s).save(f"{iconset_dir}/icon_{s}x{s}.png")
    draw_icon(s*2).save(f"{iconset_dir}/icon_{s}x{s}@2x.png")
subprocess.run(["iconutil", "-c", "icns", iconset_dir, "-o", "icon.icns"])
```

### 7-2. `.app` 번들 빌드 (`setup.py`)

```bash
python setup.py py2app
# → dist/im-not-ai.app (27MB)
```

### 7-3. DMG 인스톨러 생성 (`build_dmg.sh`)

```bash
bash build_dmg.sh
# → dist/im-not-ai-1.0.dmg (13MB)
```

**DMG 생성 과정**:
1. 스테이징 디렉토리 생성
2. `.app` 복사 + `/Applications` 심볼릭 링크 추가
3. `hdiutil create` (UDRW 읽기/쓰기 DMG)
4. 마운트 → Finder 레이아웃 설정 (AppleScript)
5. 언마운트 → `hdiutil convert` (UDZO 압축)
6. 임시 파일 정리

---

## 8. 파일 설명

### `main.py`

앱의 전체 GUI와 이벤트 핸들러.

**주요 클래스**:

| 클래스 | 설명 |
|--------|------|
| `Tooltip` | 마우스 오버 500ms 후 팝업, 화면 경계 자동 보정 |
| `RoundedButton` | Canvas 기반 pill 형태 버튼, hover 효과 포함 |
| `Chip` | 옵션 선택 토글 칩, `tk.StringVar` trace로 상태 반영 |
| `OverlayScrollbar` | Treeview/Canvas에 적용되는 얇은 오버레이 스크롤바 |
| `ImNotAIApp` | 메인 앱 클래스 (tk.Tk 상속) |

**`ImNotAIApp` 주요 메서드**:

| 메서드 | 역할 |
|--------|------|
| `_build_ui()` | 전체 레이아웃 구성 |
| `_build_input_panel()` | 입력창 + 버튼 + 옵션 패널 |
| `_build_output_panel()` | 윤문 결과창 + 복사/저장 |
| `_build_changes_panel()` | 수정 내용 접이식 패널 (diff + 총평) |
| `_render_diff()` | difflib로 단어 단위 diff 렌더링 |
| `_build_review()` | 총평 텍스트 생성 |
| `_show_result()` | API 결과를 UI에 반영 |
| `_run_fast()` | 빠른 윤문 실행 (스레드) |
| `_run_strict()` | 정밀 윤문 실행 (스레드, 옵션 적용) |
| `_show_about()` | About 다이얼로그 표시 |

### `api_client.py`

OpenRouter API 호출과 응답 파싱 담당.

**주요 함수**:

| 함수 | 역할 |
|------|------|
| `_fix_unescaped_quotes(s)` | JSON 내 이스케이프 안 된 따옴표 수정 |
| `_extract_json(text)` | 3단계 fallback JSON 추출 |
| `_call_api(...)` | HTTP POST 실행 |
| `humanize_fast(...)` | 빠른 윤문 (단일 호출) |
| `humanize_strict(...)` | 정밀 윤문 (3단계 파이프라인) |

### `prompts.py`

시스템 프롬프트 4종과 옵션 addon 빌더.

| 상수/함수 | 용도 |
|-----------|------|
| `SYSTEM_PROMPT_FAST` | 빠른 윤문용 (탐지+윤문+검증 일괄) |
| `SYSTEM_PROMPT_DETECT` | 정밀 탐지용 |
| `SYSTEM_PROMPT_REWRITE` | 정밀 윤문용 |
| `SYSTEM_PROMPT_VERIFY` | 정밀 품질 검증용 |
| `build_options_addon(options)` | sensitivity/genre/change_limit 지시문 생성 |

---

## 9. 실행 및 빌드 방법

### 개발 모드 실행

```bash
cd iamnotai_gemini

# 의존성 설치 (최초 1회)
pip install Pillow py2app

# 실행
python main.py
```

### API 키 설정

첫 실행 시 다이얼로그가 뜨거나, 환경변수로 설정:

```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
```

또는 `~/.config/iamnotai/config.json`:

```json
{
  "api_key": "sk-or-v1-..."
}
```

### 아이콘 재생성

```bash
python make_icon.py
# → icon.icns, icon_preview.png 생성
```

### `.app` 빌드

```bash
rm -rf build dist
python setup.py py2app
# → dist/im-not-ai.app
```

### DMG 빌드

```bash
bash build_dmg.sh
# → dist/im-not-ai-1.0.dmg
```

### 앱 설치

```bash
open dist/im-not-ai-1.0.dmg
# im-not-ai.app을 Applications 폴더로 드래그
```

또는 직접 복사:

```bash
cp -r dist/im-not-ai.app /Applications/
```

---

## 라이선스

MIT License — 상용 활용, fork, 통합 모두 허용

원본: https://github.com/epoko77-ai/im-not-ai
