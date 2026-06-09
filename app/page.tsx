"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import type { HumanizeResult, Options, Pattern } from "@/lib/types";

// ── 색상 상수 ─────────────────────────────────────────────────
const GRADE_COLOR: Record<string, string> = {
  A: "#50fa7b",
  B: "#4fc3f7",
  C: "#ffb86c",
  D: "#ff5555",
};

// ── diff 유틸 (토큰 단위) ─────────────────────────────────────
type DiffToken = { type: "equal" | "add" | "del" | "chg"; text: string };

function computeDiff(original: string, rewritten: string): DiffToken[] {
  const tokenize = (s: string) => s.match(/\S+|\s+/g) ?? [];
  const orig = tokenize(original);
  const next = tokenize(rewritten);

  // LCS-based diff (simple O(n²) for short texts)
  const m = orig.length, n = next.length;
  const dp: number[][] = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));
  for (let i = m - 1; i >= 0; i--)
    for (let j = n - 1; j >= 0; j--)
      dp[i][j] = orig[i] === next[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);

  const tokens: DiffToken[] = [];
  let i = 0, j = 0;
  while (i < m || j < n) {
    if (i < m && j < n && orig[i] === next[j]) {
      tokens.push({ type: "equal", text: orig[i] });
      i++; j++;
    } else if (j < n && (i >= m || dp[i][j + 1] >= dp[i + 1][j])) {
      tokens.push({ type: "add", text: next[j] });
      j++;
    } else if (i < m && (j >= n || dp[i + 1][j] > dp[i][j + 1])) {
      // check if next token is add → replace
      if (j < n && dp[i + 1][j + 1] >= Math.max(dp[i + 1][j], dp[i][j + 1])) {
        tokens.push({ type: "del", text: orig[i] });
        tokens.push({ type: "add", text: next[j] });
        i++; j++;
      } else {
        tokens.push({ type: "del", text: orig[i] });
        i++;
      }
    } else {
      break;
    }
  }
  return tokens;
}

// ── 컴포넌트: Chip ────────────────────────────────────────────
function Chip<T extends string>({
  value,
  current,
  onSelect,
}: {
  value: T;
  current: T;
  onSelect: (v: T) => void;
}) {
  const selected = value === current;
  return (
    <button
      onClick={() => onSelect(value)}
      style={{
        background: selected ? "#7c6af7" : "#363650",
        color: selected ? "#ffffff" : "#9090b8",
        border: "none",
        borderRadius: 20,
        padding: "3px 12px",
        fontSize: 12,
        cursor: "pointer",
        transition: "background 0.15s",
        fontFamily: "Helvetica Neue, sans-serif",
      }}
    >
      {value}
    </button>
  );
}

// ── 컴포넌트: GradeTag ───────────────────────────────────────
function GradeTag({ grade, changeRate }: { grade: string; changeRate: number }) {
  return (
    <span style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <span style={{ fontWeight: 700, fontSize: 15, color: GRADE_COLOR[grade] ?? "#cdd6f4" }}>
        등급 {grade}
      </span>
      <span style={{ fontSize: 12, color: "#6c7086" }}>변경률 {(changeRate * 100).toFixed(1)}%</span>
    </span>
  );
}

// ── 컴포넌트: DiffView ───────────────────────────────────────
function DiffView({ tokens }: { tokens: DiffToken[] }) {
  return (
    <div
      style={{
        fontFamily: "'Apple SD Gothic Neo','Malgun Gothic','Noto Sans KR',sans-serif",
        fontSize: 13,
        lineHeight: 1.7,
        whiteSpace: "pre-wrap",
        wordBreak: "break-word",
        padding: "10px 12px",
        background: "#1e1e30",
        borderRadius: 6,
        maxHeight: 160,
        overflowY: "auto",
      }}
    >
      {tokens.map((t, i) => {
        if (t.type === "equal") return <span key={i}>{t.text}</span>;
        if (t.type === "add") return <span key={i} className="diff-add">{t.text}</span>;
        if (t.type === "del") return <span key={i} className="diff-del">{t.text}</span>;
        return <span key={i} className="diff-chg">{t.text}</span>;
      })}
    </div>
  );
}

// ── 컴포넌트: PatternRow ──────────────────────────────────────
const SEV_COLOR: Record<string, string> = { S1: "#ff5555", S2: "#ffb86c", S3: "#6c7086" };

function PatternRow({ p }: { p: Pattern }) {
  return (
    <tr style={{ borderBottom: "1px solid #2a2a3e" }}>
      <td style={{ padding: "5px 8px", color: "#b39ddb", fontSize: 12 }}>{p.category}</td>
      <td style={{ padding: "5px 8px", color: SEV_COLOR[p.severity] ?? "#cdd6f4", fontSize: 12, fontWeight: 700 }}>{p.severity}</td>
      <td style={{ padding: "5px 8px", fontSize: 12, maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
        {(p.original ?? p.span ?? "").slice(0, 50)}
      </td>
      <td style={{ padding: "5px 8px", fontSize: 12, maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
        {(p.corrected ?? "").slice(0, 50)}
      </td>
      <td style={{ padding: "5px 8px", fontSize: 12, color: "#9090b8" }}>{p.reason}</td>
    </tr>
  );
}

// ── 컴포넌트: ApiKeyModal ─────────────────────────────────────
function ApiKeyModal({ onClose, onSave }: { onClose: () => void; onSave: (k: string) => void }) {
  const [val, setVal] = useState(() => typeof window !== "undefined" ? (localStorage.getItem("gemini_api_key") ?? "") : "");

  return (
    <div
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100 }}
      onClick={onClose}
    >
      <div
        style={{ background: "#2a2a3e", borderRadius: 12, padding: 28, width: 440, boxShadow: "0 8px 40px rgba(0,0,0,0.5)" }}
        onClick={e => e.stopPropagation()}
      >
        <h3 style={{ color: "#b39ddb", margin: "0 0 8px", fontSize: 17 }}>Google AI Studio API 키 설정</h3>
        <p style={{ color: "#6c7086", fontSize: 12, margin: "0 0 16px" }}>
          <a href="https://aistudio.google.com" target="_blank" rel="noreferrer" style={{ color: "#4fc3f7" }}>
            aistudio.google.com
          </a>에서 발급받은 API 키를 입력하세요.<br />
          키는 브라우저 로컬스토리지에만 저장되며 서버로 전송됩니다.
        </p>
        <input
          type="password"
          value={val}
          onChange={e => setVal(e.target.value)}
          placeholder="AIza..."
          style={{
            width: "100%",
            background: "#181825",
            color: "#cdd6f4",
            border: "1px solid #363650",
            borderRadius: 8,
            padding: "10px 12px",
            fontSize: 14,
            fontFamily: "monospace",
            outline: "none",
          }}
          onKeyDown={e => e.key === "Enter" && onSave(val)}
          autoFocus
        />
        <div style={{ display: "flex", gap: 10, marginTop: 16, justifyContent: "flex-end" }}>
          <button
            onClick={onClose}
            style={{ background: "#363650", color: "#9090b8", border: "none", borderRadius: 8, padding: "8px 18px", cursor: "pointer", fontSize: 13 }}
          >
            취소
          </button>
          <button
            onClick={() => onSave(val)}
            style={{ background: "#7c6af7", color: "white", border: "none", borderRadius: 8, padding: "8px 18px", cursor: "pointer", fontSize: 13, fontWeight: 700 }}
          >
            저장
          </button>
        </div>
      </div>
    </div>
  );
}

// ── 메인 페이지 ───────────────────────────────────────────────
export default function Home() {
  const [inputText, setInputText] = useState("");
  const [result, setResult] = useState<HumanizeResult | null>(null);
  const [status, setStatus] = useState("");
  const [statusColor, setStatusColor] = useState("#b39ddb");
  const [loading, setLoading] = useState(false);
  const [showDiff, setShowDiff] = useState(false);
  const [showApiModal, setShowApiModal] = useState(false);
  const [apiKey, setApiKey] = useState("");
  const [options, setOptions] = useState<Options>({ sensitivity: "S1+S2", genre: "일반", change_limit: "30%" });
  const [showOpts, setShowOpts] = useState(false);
  const [diffTokens, setDiffTokens] = useState<DiffToken[]>([]);
  const [originalText, setOriginalText] = useState("");
  const [copied, setCopied] = useState(false);
  const outputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const stored = localStorage.getItem("gemini_api_key") ?? "";
    setApiKey(stored);
  }, []);

  const saveApiKey = (k: string) => {
    const trimmed = k.trim();
    setApiKey(trimmed);
    localStorage.setItem("gemini_api_key", trimmed);
    setShowApiModal(false);
    setStatus("API 키가 저장됐습니다.");
    setStatusColor("#50fa7b");
    setTimeout(() => setStatus(""), 2000);
  };

  const showStatus = (msg: string, color = "#b39ddb", duration = 0) => {
    setStatus(msg);
    setStatusColor(color);
    if (duration) setTimeout(() => setStatus(""), duration);
  };

  const run = useCallback(async (mode: "fast" | "strict") => {
    const text = inputText.trim();
    if (!text) {
      showStatus("윤문할 텍스트를 입력해주세요.", "#ff5555", 2500);
      return;
    }

    const key = apiKey || localStorage.getItem("gemini_api_key") || "";

    setLoading(true);
    setOriginalText(text);
    showStatus(mode === "fast" ? "API 호출 중..." : "1/3단계: AI 패턴 탐지 중...");

    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (key) headers["x-api-key"] = key;

      const res = await fetch("/api/humanize", {
        method: "POST",
        headers,
        body: JSON.stringify({ text, mode, options }),
      });

      const data = await res.json();

      if (!res.ok) {
        showStatus(data.error ?? "오류가 발생했습니다.", "#ff5555", 4000);
        return;
      }

      setResult(data as HumanizeResult);
      setDiffTokens(computeDiff(text, data.rewritten));
      setShowDiff(true);
      showStatus("윤문 완료!", "#50fa7b", 3000);
    } catch {
      showStatus("네트워크 오류가 발생했습니다.", "#ff5555", 3000);
    } finally {
      setLoading(false);
    }
  }, [inputText, apiKey, options]);

  const copyResult = () => {
    if (!result?.rewritten) return;
    navigator.clipboard.writeText(result.rewritten);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const charCount = inputText.length;
  const charColor = charCount > 8000 ? "#ffb86c" : charCount > 5000 ? "#b39ddb" : "#cdd6f4";

  const s1 = result ? result.patterns.filter(p => p.severity === "S1").length : 0;
  const s2 = result ? result.patterns.filter(p => p.severity === "S2").length : 0;

  return (
    <div style={{ minHeight: "100vh", background: "#1e1e2e", display: "flex", flexDirection: "column", padding: "0 16px" }}>
      {showApiModal && <ApiKeyModal onClose={() => setShowApiModal(false)} onSave={saveApiKey} />}

      {/* 헤더 */}
      <header style={{ display: "flex", alignItems: "center", padding: "14px 0 8px", gap: 0 }}>
        <span style={{ fontSize: 22, fontWeight: 700, color: "#b39ddb" }}>im-not-ai</span>
        <span style={{ marginLeft: 10, fontSize: 13, color: "#6c7086" }}>AI 글투 탐지 · 한국어 윤문기</span>
        <span style={{ flex: 1 }} />
        <button
          onClick={() => setShowApiModal(true)}
          style={{
            background: "#363650", color: "#cdd6f4", border: "none",
            borderRadius: 10, padding: "5px 14px", cursor: "pointer", fontSize: 12,
          }}
        >
          ⚙ API 키
        </button>
      </header>

      {/* 메인 패널 (좌/우) */}
      <div style={{ display: "flex", gap: 12, flex: 1, minHeight: 0, paddingBottom: 4 }}>
        {/* 입력 패널 */}
        <div style={{ flex: 1, background: "#2a2a3e", borderRadius: 10, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <div style={{ padding: "12px 14px 6px", fontWeight: 700, fontSize: 13, color: "#cdd6f4" }}>입력 텍스트</div>
          <textarea
            value={inputText}
            onChange={e => setInputText(e.target.value)}
            placeholder="AI 글투를 제거하고 싶은 한국어 텍스트를 붙여넣으세요..."
            style={{ flex: 1, padding: "8px 12px", fontSize: 14, lineHeight: 1.8, minHeight: 320 }}
          />
          {/* 버튼 행 */}
          <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "8px 12px 10px", flexWrap: "wrap" }}>
            <span style={{ fontSize: 12, color: charColor }}>{charCount.toLocaleString()}자</span>
            <button
              onClick={() => setInputText("")}
              style={{ background: "#363650", color: "#cdd6f4", border: "none", borderRadius: 8, padding: "4px 10px", cursor: "pointer", fontSize: 12 }}
            >
              지우기
            </button>
            <button
              onClick={() => setShowOpts(v => !v)}
              style={{ background: "#363650", color: "#4fc3f7", border: "none", borderRadius: 8, padding: "4px 10px", cursor: "pointer", fontSize: 12 }}
            >
              옵션 {showOpts ? "▴" : "▾"}
            </button>
            <span style={{ flex: 1 }} />
            <button
              disabled={loading}
              onClick={() => run("strict")}
              style={{
                background: loading ? "#383850" : "#4fc3f7", color: "#12122a",
                border: "none", borderRadius: 20, padding: "7px 18px",
                cursor: loading ? "not-allowed" : "pointer",
                fontSize: 13, fontWeight: 700,
              }}
            >
              정밀 윤문
            </button>
            <button
              disabled={loading}
              onClick={() => run("fast")}
              style={{
                background: loading ? "#383850" : "#b39ddb", color: "#12122a",
                border: "none", borderRadius: 20, padding: "7px 18px",
                cursor: loading ? "not-allowed" : "pointer",
                fontSize: 13, fontWeight: 700,
              }}
            >
              빠른 윤문 ▶
            </button>
          </div>

          {/* 옵션 패널 */}
          {showOpts && (
            <div style={{ background: "#242438", padding: "10px 14px 14px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                <span style={{ fontSize: 11, color: "#6c7086", width: 60 }}>탐지 범위</span>
                {(["S1만", "S1+S2", "전체"] as Options["sensitivity"][]).map(v => (
                  <Chip key={v} value={v} current={options.sensitivity} onSelect={v => setOptions(o => ({ ...o, sensitivity: v }))} />
                ))}
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                <span style={{ fontSize: 11, color: "#6c7086", width: 60 }}>장르</span>
                {(["일반", "학술", "비즈니스", "SNS"] as Options["genre"][]).map(v => (
                  <Chip key={v} value={v} current={options.genre} onSelect={v => setOptions(o => ({ ...o, genre: v }))} />
                ))}
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 11, color: "#6c7086", width: 60 }}>변경 상한</span>
                {(["30%", "50%"] as Options["change_limit"][]).map(v => (
                  <Chip key={v} value={v} current={options.change_limit} onSelect={v => setOptions(o => ({ ...o, change_limit: v }))} />
                ))}
              </div>
            </div>
          )}
        </div>

        {/* 출력 패널 */}
        <div style={{ flex: 1, background: "#2a2a3e", borderRadius: 10, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <div style={{ padding: "12px 14px 6px", display: "flex", alignItems: "center" }}>
            <span style={{ fontWeight: 700, fontSize: 13, color: "#cdd6f4" }}>윤문 결과</span>
            <span style={{ flex: 1 }} />
            {result && <GradeTag grade={result.grade} changeRate={result.change_rate} />}
          </div>
          <textarea
            ref={outputRef}
            readOnly
            value={result?.rewritten ?? ""}
            placeholder="윤문 결과가 여기에 표시됩니다..."
            style={{ flex: 1, padding: "8px 12px", fontSize: 14, lineHeight: 1.8, minHeight: 320, color: result ? "#cdd6f4" : "#6c7086" }}
          />
          <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "8px 12px 10px" }}>
            <span style={{ fontSize: 12, color: "#6c7086" }}>
              {result ? `${result.rewritten.length.toLocaleString()}자` : ""}
            </span>
            <span style={{ flex: 1 }} />
            <button
              onClick={copyResult}
              disabled={!result}
              style={{
                background: "#363650", color: copied ? "#50fa7b" : "#cdd6f4",
                border: "none", borderRadius: 8, padding: "4px 12px",
                cursor: result ? "pointer" : "not-allowed", fontSize: 12,
              }}
            >
              {copied ? "복사됨!" : "복사"}
            </button>
          </div>
        </div>
      </div>

      {/* 수정 내용 패널 */}
      <div style={{ background: "#2a2a3e", borderRadius: 10, marginBottom: 6 }}>
        <div style={{ display: "flex", alignItems: "center", padding: "8px 14px" }}>
          <span style={{ fontWeight: 700, fontSize: 12, color: "#cdd6f4" }}>수정 내용</span>
          {result && (
            <span style={{ marginLeft: 10, fontSize: 11, color: "#6c7086" }}>
              S1: {s1}건 · S2: {s2}건 · 총 {result.patterns.length}건
            </span>
          )}
          {/* diff 범례 */}
          <span style={{ marginLeft: 12, fontSize: 10, background: "#1a3a20", color: "#69ff94", padding: "1px 6px", borderRadius: 4 }}> 추가 </span>
          <span style={{ marginLeft: 4, fontSize: 10, background: "#3a1a1a", color: "#ff6e6e", padding: "1px 6px", borderRadius: 4, textDecoration: "line-through" }}> 삭제 </span>
          <span style={{ marginLeft: 4, fontSize: 10, background: "#3a2e10", color: "#ffd580", padding: "1px 6px", borderRadius: 4 }}> 변경 </span>
          <span style={{ flex: 1 }} />
          {result && (
            <button
              onClick={() => setShowDiff(v => !v)}
              style={{ background: "#363650", color: "#4fc3f7", border: "none", borderRadius: 8, padding: "3px 10px", cursor: "pointer", fontSize: 11 }}
            >
              {showDiff ? "수정 내용 닫기 ▴" : "수정 내용 보기 ▾"}
            </button>
          )}
        </div>

        {showDiff && result && (
          <div style={{ borderTop: "1px solid #363650" }}>
            {/* Diff */}
            <div style={{ padding: "8px 12px 6px" }}>
              <DiffView tokens={diffTokens} />
            </div>

            {/* 총평 */}
            <div style={{ padding: "6px 14px 10px", borderTop: "1px solid #2a2a45" }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: "#cdd6f4", marginBottom: 4 }}>총평</div>
              <div style={{ fontSize: 13, color: "#cdd6f4", lineHeight: 1.7, whiteSpace: "pre-wrap", fontFamily: "'Apple SD Gothic Neo','Malgun Gothic',sans-serif" }}>
                {buildReview(result, s1, s2)}
              </div>
            </div>

            {/* 탐지 패턴 테이블 */}
            {result.patterns.length > 0 && (
              <div style={{ padding: "6px 12px 12px", overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid #363650" }}>
                      {["카테고리", "심각도", "원문 구절", "수정 구절", "이유"].map(h => (
                        <th key={h} style={{ padding: "4px 8px", textAlign: "left", color: "#6c7086", fontWeight: 700 }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.patterns.map((p, i) => <PatternRow key={i} p={p} />)}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 상태 표시줄 */}
      <div style={{ textAlign: "center", padding: "4px 0 10px", minHeight: 24, fontSize: 13, color: statusColor, transition: "color 0.2s" }}>
        {loading ? (
          <span>{status || "처리 중..."} <span style={{ display: "inline-block", animation: "spin 1s linear infinite" }}>⟳</span></span>
        ) : status}
      </div>

      <style>{`@keyframes spin { from { transform:rotate(0deg) } to { transform:rotate(360deg) } }`}</style>
    </div>
  );
}

function buildReview(data: HumanizeResult, s1: number, s2: number): string {
  const grade = data.grade;
  const gradeDesc: Record<string, string> = {
    A: "AI 글투가 거의 없는 자연스러운 글로 개선됐습니다.",
    B: "주요 AI 패턴이 제거됐으며 전반적으로 자연스럽습니다.",
    C: "일부 AI 특유 표현이 남아있어 추가 검토를 권장합니다.",
    D: "AI 패턴이 다수 남아있어 사람의 직접 검수가 필요합니다.",
  };
  const lines = [
    `■ 등급: ${grade}  (${gradeDesc[grade] ?? ""})`,
    `■ 변경률: ${(data.change_rate * 100).toFixed(1)}%  (S1 ${s1}건 · S2 ${s2}건 · 총 ${data.patterns.length}건 수정)`,
  ];
  if (s1 > 0) {
    const cats = [...new Set(data.patterns.filter(p => p.severity === "S1").map(p => p.category))].sort();
    lines.push(`■ 필수 제거(S1): 카테고리 ${cats.join(", ")} 패턴 삭제됨`);
  }
  if (data.change_rate > 0.3) lines.push("⚠ 변경률이 30%를 넘었습니다. 원문 의도가 유지됐는지 확인하세요.");
  if (data.summary) lines.push(`■ AI 평가: ${data.summary}`);
  return lines.join("\n");
}
