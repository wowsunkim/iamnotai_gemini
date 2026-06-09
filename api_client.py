import json
import re
import urllib.request
import urllib.error
from typing import Callable

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MODEL = "google/gemini-2.5-flash"


class APIError(Exception):
    pass


def _fix_unescaped_quotes(s: str) -> str:
    """JSON 문자열 값 안의 이스케이프되지 않은 큰따옴표를 수정한다."""
    out = []
    in_str = False
    i = 0
    while i < len(s):
        c = s[i]
        if not in_str:
            out.append(c)
            if c == '"':
                in_str = True
        elif c == '\\':        # 이스케이프 시퀀스 그대로 통과
            out.append(c)
            if i + 1 < len(s):
                out.append(s[i + 1])
            i += 2
            continue
        elif c == '"':
            # 다음 의미 있는 문자가 : , } ] 이면 문자열 종료
            j = i + 1
            while j < len(s) and s[j] in ' \t\r\n':
                j += 1
            if j >= len(s) or s[j] in ':,}]':
                out.append(c)
                in_str = False
            else:
                out.append('\\"')   # 내부 따옴표 이스케이프
        else:
            out.append(c)
        i += 1
    return ''.join(out)


def _extract_json(text: str) -> dict:
    text = text.strip()

    # 마크다운 코드블록 제거
    m = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    candidate = m.group(1).strip() if m else text

    # 1차: 그대로 파싱
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    # 2차: { } 범위 추출
    s, e = candidate.find("{"), candidate.rfind("}") + 1
    if s != -1 and e > s:
        try:
            return json.loads(candidate[s:e])
        except json.JSONDecodeError:
            pass

    # 3차: 이스케이프 안 된 따옴표 수정 후 재시도
    try:
        return json.loads(_fix_unescaped_quotes(candidate[s:e] if s != -1 else candidate))
    except json.JSONDecodeError:
        pass

    raise json.JSONDecodeError("JSON 추출 실패", text, 0)


def _call_api(api_key: str, system_prompt: str, user_prompt: str,
              on_progress: Callable[[str], None] = None) -> str:
    url = f"{OPENROUTER_BASE_URL}/chat/completions"
    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 8192,
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/epoko77-ai/im-not-ai",
            "X-Title": "im-not-ai",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        try:
            error_data = json.loads(error_body)
            msg = error_data.get("error", {}).get("message", error_body)
        except Exception:
            msg = error_body
        raise APIError(f"HTTP {e.code}: {msg}")
    except urllib.error.URLError as e:
        raise APIError(f"네트워크 오류: {e.reason}")


def humanize_fast(api_key: str, text: str,
                  on_progress: Callable[[str], None] = None,
                  options: dict = None) -> dict:
    from prompts import SYSTEM_PROMPT_FAST, build_fast_user_prompt, build_options_addon
    if on_progress:
        on_progress("API 호출 중...")
    system = SYSTEM_PROMPT_FAST + build_options_addon(options or {})
    raw = _call_api(api_key, system, build_fast_user_prompt(text), on_progress)
    try:
        return _extract_json(raw)
    except json.JSONDecodeError:
        raise APIError(f"응답 파싱 실패: {raw[:200]}")


def humanize_strict(api_key: str, text: str,
                    on_progress: Callable[[str], None] = None,
                    options: dict = None) -> dict:
    from prompts import (
        SYSTEM_PROMPT_DETECT, SYSTEM_PROMPT_REWRITE, SYSTEM_PROMPT_VERIFY,
        build_detect_user_prompt, build_rewrite_user_prompt, build_verify_user_prompt,
        build_options_addon,
    )
    addon = build_options_addon(options or {})

    # Step 1: Detect
    if on_progress:
        on_progress("1/3단계: AI 패턴 탐지 중...")
    raw_detect = _call_api(api_key, SYSTEM_PROMPT_DETECT + addon,
                           build_detect_user_prompt(text))
    try:
        detect_result = _extract_json(raw_detect)
    except json.JSONDecodeError:
        raise APIError(f"탐지 응답 파싱 실패: {raw_detect[:200]}")

    patterns = detect_result.get("patterns", [])

    # Step 2: Rewrite
    if on_progress:
        on_progress("2/3단계: 윤문 처리 중...")
    raw_rewrite = _call_api(
        api_key, SYSTEM_PROMPT_REWRITE + addon,
        build_rewrite_user_prompt(text, patterns)
    )
    try:
        rewrite_result = _extract_json(raw_rewrite)
    except json.JSONDecodeError:
        raise APIError(f"윤문 응답 파싱 실패: {raw_rewrite[:200]}")

    rewritten = rewrite_result.get("rewritten", text)

    # Step 3: Verify
    if on_progress:
        on_progress("3/3단계: 품질 검증 중...")
    raw_verify = _call_api(
        api_key, SYSTEM_PROMPT_VERIFY,
        build_verify_user_prompt(text, rewritten)
    )
    try:
        verify_result = _extract_json(raw_verify)
    except json.JSONDecodeError:
        raise APIError(f"검증 응답 파싱 실패: {raw_verify[:200]}")

    return {
        "rewritten": rewritten,
        "patterns": patterns,
        "grade": verify_result.get("grade", "C"),
        "change_rate": verify_result.get("change_rate", rewrite_result.get("change_rate", 0.0)),
        "summary": verify_result.get("summary", ""),
        "over_correction": verify_result.get("over_correction", False),
    }
