import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "im-not-ai — AI 글투 탐지·한국어 윤문기",
  description: "AI가 생성한 한국어 글에서 AI 글투를 탐지하고 자연스러운 한국어로 윤문합니다.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
