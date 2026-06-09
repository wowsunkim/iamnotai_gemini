import { NextRequest, NextResponse } from "next/server";
import {
  SYSTEM_PROMPT_FAST,
  SYSTEM_PROMPT_DETECT,
  SYSTEM_PROMPT_REWRITE,
  SYSTEM_PROMPT_VERIFY,
  buildOptionsAddon,
  buildFastUserPrompt,
  buildDetectUserPrompt,
  buildRewriteUserPrompt,
  buildVerifyUserPrompt,
} from "@/lib/prompts";
import { Options, Pattern } from "@/lib/types";

const GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta";
const MODEL = "gemini-2.5-flash";

function extractJson(text: string): Record<string, unknown> {
  const stripped = text.trim();
  const m = stripped.match(/```(?:json)?\s*([\s\S]+?)```/);
  const candidate = m ? m[1].trim() : stripped;

  try { return JSON.parse(candidate); } catch { /* continue */ }

  const s = candidate.indexOf("{");
  const e = candidate.lastIndexOf("}") + 1;
  if (s !== -1 && e > s) {
    try { return JSON.parse(candidate.slice(s, e)); } catch { /* continue */ }
  }

  throw new Error(`JSON 추출 실패: ${text.slice(0, 200)}`);
}

async function callGemini(apiKey: string, systemPrompt: string, userPrompt: string): Promise<string> {
  const url = `${GEMINI_BASE_URL}/models/${MODEL}:generateContent?key=${apiKey}`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      system_instruction: { parts: [{ text: systemPrompt }] },
      contents: [{ role: "user", parts: [{ text: userPrompt }] }],
      generationConfig: { temperature: 0.3, maxOutputTokens: 8192 },
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const msg = (err as { error?: { message?: string } }).error?.message ?? res.statusText;
    throw new Error(`HTTP ${res.status}: ${msg}`);
  }

  const data = await res.json();
  return data.candidates[0].content.parts[0].text as string;
}

export async function POST(req: NextRequest) {
  const body = await req.json();
  const { text, mode, options } = body as {
    text: string;
    mode: "fast" | "strict";
    options?: Partial<Options>;
  };

  const apiKey =
    process.env.GEMINI_API_KEY ||
    (req.headers.get("x-api-key") ?? "");

  if (!apiKey) {
    return NextResponse.json({ error: "API 키가 설정되지 않았습니다." }, { status: 400 });
  }

  if (!text?.trim()) {
    return NextResponse.json({ error: "텍스트를 입력해주세요." }, { status: 400 });
  }

  try {
    if (mode === "fast") {
      const addon = buildOptionsAddon(options ?? {});
      const raw = await callGemini(apiKey, SYSTEM_PROMPT_FAST + addon, buildFastUserPrompt(text));
      const result = extractJson(raw);
      return NextResponse.json(result);
    }

    // strict: 3-step pipeline
    const addon = buildOptionsAddon(options ?? {});

    const rawDetect = await callGemini(apiKey, SYSTEM_PROMPT_DETECT + addon, buildDetectUserPrompt(text));
    const detectResult = extractJson(rawDetect);
    const patterns = (detectResult.patterns ?? []) as Pattern[];

    const rawRewrite = await callGemini(apiKey, SYSTEM_PROMPT_REWRITE + addon, buildRewriteUserPrompt(text, patterns));
    const rewriteResult = extractJson(rawRewrite);
    const rewritten = (rewriteResult.rewritten ?? text) as string;

    const rawVerify = await callGemini(apiKey, SYSTEM_PROMPT_VERIFY, buildVerifyUserPrompt(text, rewritten));
    const verifyResult = extractJson(rawVerify);

    return NextResponse.json({
      rewritten,
      patterns,
      grade: verifyResult.grade ?? "C",
      change_rate: verifyResult.change_rate ?? rewriteResult.change_rate ?? 0,
      summary: verifyResult.summary ?? "",
      over_correction: verifyResult.over_correction ?? false,
    });
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
