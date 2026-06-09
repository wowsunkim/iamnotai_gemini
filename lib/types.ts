export interface Pattern {
  category: string;
  severity: "S1" | "S2" | "S3";
  original?: string;
  span?: string;
  corrected?: string;
  reason: string;
  position?: string;
}

export interface HumanizeResult {
  rewritten: string;
  patterns: Pattern[];
  grade: "A" | "B" | "C" | "D";
  change_rate: number;
  summary: string;
  over_correction?: boolean;
}

export interface Options {
  sensitivity: "S1만" | "S1+S2" | "전체";
  genre: "일반" | "학술" | "비즈니스" | "SNS";
  change_limit: "30%" | "50%";
}
