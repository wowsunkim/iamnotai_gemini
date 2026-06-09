#!/usr/bin/env python3
"""im-not-ai: AI 한국어 글 윤문 앱 (OpenRouter / Gemini 2.0 Flash)"""

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox, filedialog, simpledialog
import threading
import difflib

import config
import api_client


# ── 폰트 ──────────────────────────────────────────────────────
# macOS 시스템 폰트: UI는 Helvetica Neue, 한국어 본문은 Apple SD Gothic Neo
FONT_UI    = "Helvetica Neue"
FONT_KO    = "Apple SD Gothic Neo"

# ── 색상 팔레트 ────────────────────────────────────────────────
BG          = "#1e1e2e"
PANEL       = "#2a2a3e"
ACCENT      = "#b39ddb"   # 빠른 윤문 버튼 (연보라)
ACCENT2     = "#4fc3f7"   # 정밀 윤문 버튼 (하늘)
BTN_FG      = "#12122a"   # 버튼 텍스트 (어두운 남색, 대비 최대)
SUCCESS     = "#50fa7b"
WARN        = "#ffb86c"
DANGER      = "#ff5555"
TEXT        = "#cdd6f4"
SUBTEXT     = "#6c7086"
INPUT_BG    = "#181825"
CHIP_SEL    = "#7c6af7"
CHIP_UNSEL  = "#363650"
CHIP_FG_SEL    = "#ffffff"
CHIP_FG_UNSEL  = "#9090b8"

# diff 색상
DIFF_ADD_BG    = "#1a3a20"
DIFF_ADD_FG    = "#69ff94"
DIFF_DEL_BG    = "#3a1a1a"
DIFF_DEL_FG    = "#ff6e6e"
DIFF_CHG_BG    = "#3a2e10"
DIFF_CHG_FG    = "#ffd580"

GRADE_COLOR = {"A": SUCCESS, "B": ACCENT2, "C": WARN, "D": DANGER}


# ── 유틸 ──────────────────────────────────────────────────────

def _lighten(hex_color: str, amount: int = 22) -> str:
    r = min(255, int(hex_color[1:3], 16) + amount)
    g = min(255, int(hex_color[3:5], 16) + amount)
    b = min(255, int(hex_color[5:7], 16) + amount)
    return f"#{r:02x}{g:02x}{b:02x}"


def _pill(canvas: tk.Canvas, w: int, h: int, r: int, color: str):
    """Canvas에 pill(좌우 둥근) 모양을 그린다."""
    canvas.delete("all")
    canvas.create_arc(0,     0,     r*2,   r*2,   start=90,  extent=90,  fill=color, outline=color)
    canvas.create_arc(w-r*2, 0,     w,     r*2,   start=0,   extent=90,  fill=color, outline=color)
    canvas.create_arc(0,     h-r*2, r*2,   h,     start=180, extent=90,  fill=color, outline=color)
    canvas.create_arc(w-r*2, h-r*2, w,     h,     start=270, extent=90,  fill=color, outline=color)
    canvas.create_rectangle(r,  0,  w-r, h,  fill=color, outline=color)
    canvas.create_rectangle(0,  r,  w,   h-r, fill=color, outline=color)


# ── 커스텀 위젯 ───────────────────────────────────────────────

class Tooltip:
    """위젯에 마우스를 올리면 나타나는 툴팁."""

    DELAY  = 500   # ms — 표시까지 대기 시간
    PAD    = 6     # 내부 패딩
    BG     = "#2e2b4a"
    FG     = "#e0d8ff"
    BORDER = "#7c6af7"

    def __init__(self, widget: tk.Widget, text: str):
        self._widget  = widget
        self._text    = text
        self._win     = None
        self._job     = None
        widget.bind("<Enter>",  self._on_enter,  add="+")
        widget.bind("<Leave>",  self._on_leave,  add="+")
        widget.bind("<ButtonPress>", self._on_leave, add="+")

    def _on_enter(self, _event):
        self._job = self._widget.after(self.DELAY, self._show)

    def _on_leave(self, _event):
        if self._job:
            self._widget.after_cancel(self._job)
            self._job = None
        self._hide()

    def _show(self):
        if self._win:
            return
        x, y, _, h = self._widget.bbox("insert") if hasattr(self._widget, "bbox") else (0, 0, 0, 0)
        x = self._widget.winfo_rootx() + self._widget.winfo_width() // 2
        y = self._widget.winfo_rooty() + self._widget.winfo_height() + 4

        self._win = tw = tk.Toplevel(self._widget)
        tw.wm_overrideredirect(True)  # 창 테두리 제거
        tw.wm_attributes("-topmost", True)

        # 배경 프레임 (테두리 역할)
        outer = tk.Frame(tw, bg=self.BORDER, padx=1, pady=1)
        outer.pack()
        inner = tk.Frame(outer, bg=self.BG)
        inner.pack()
        lbl = tk.Label(
            inner, text=self._text,
            font=(FONT_UI, 10),
            fg=self.FG, bg=self.BG,
            justify="left",
            padx=self.PAD + 4, pady=self.PAD,
            wraplength=300,
        )
        lbl.pack()

        tw.update_idletasks()
        tw_w = tw.winfo_width()
        # 화면 오른쪽 밖으로 나가지 않도록 보정
        screen_w = tw.winfo_screenwidth()
        if x + tw_w > screen_w - 10:
            x = screen_w - tw_w - 10
        tw.wm_geometry(f"+{x}+{y}")

    def _hide(self):
        if self._win:
            self._win.destroy()
            self._win = None


class RoundedButton(tk.Canvas):
    """좌우 둥근 pill 형태의 버튼."""

    def __init__(self, parent, text, command=None,
                 bg=ACCENT, fg=BTN_FG,
                 radius=15, padx=20, pady=8,
                 font=None, **kw):
        if font is None:
            font = (FONT_UI, 11, "bold")
        self._cmd      = command
        self._r        = radius
        self._bg       = bg
        self._fg       = fg
        self._hover    = _lighten(bg, 22)
        self._dis_bg   = "#383850"
        self._dis_fg   = SUBTEXT
        self._disabled = False
        self._text     = text
        self._font     = font

        f  = tkfont.Font(family=font[0], size=font[1],
                         weight=font[2] if len(font) > 2 else "normal")
        tw = int(f.measure(text))
        th = int(f.metrics("linespace"))
        w, h = tw + padx * 2, th + pady * 2
        self._bw, self._bh = w, h

        super().__init__(parent, width=w, height=h,
                         bg=parent.cget("bg"), highlightthickness=0,
                         cursor="hand2", **kw)
        self._redraw(self._bg)
        self.bind("<Button-1>", self._click)
        self.bind("<Enter>",    lambda e: not self._disabled and self._redraw(self._hover))
        self.bind("<Leave>",    lambda e: self._redraw(self._dis_bg if self._disabled else self._bg))

    def _redraw(self, bg: str):
        _pill(self, self._bw, self._bh, self._r, bg)
        self.create_text(self._bw // 2, self._bh // 2,
                         text=self._text,
                         fill=self._dis_fg if self._disabled else self._fg,
                         font=self._font)

    def _click(self, _):
        if not self._disabled and self._cmd:
            self._cmd()

    def config(self, **kw):
        if "state" in kw:
            self._disabled = kw["state"] == "disabled"
            self._redraw(self._dis_bg if self._disabled else self._bg)
        if "text" in kw:
            self._text = kw["text"]
            self._redraw(self._bg)

    configure = config


class Chip(tk.Canvas):
    """옵션 선택용 작은 토글 chip."""

    def __init__(self, parent, text, variable, value,
                 radius=10, padx=10, pady=4,
                 font=None, **kw):
        if font is None:
            font = (FONT_UI, 9)
        self._var   = variable
        self._val   = value
        self._text  = text
        self._font  = font
        self._r     = radius

        f  = tkfont.Font(family=font[0], size=font[1])
        tw = int(f.measure(text))
        th = int(f.metrics("linespace"))
        w, h = tw + padx * 2, th + pady * 2
        self._bw, self._bh = w, h

        super().__init__(parent, width=w, height=h,
                         bg=parent.cget("bg"), highlightthickness=0,
                         cursor="hand2", **kw)
        self._redraw()
        variable.trace_add("write", lambda *_: self._redraw())
        self.bind("<Button-1>", lambda e: variable.set(value))

    def _redraw(self):
        sel = self._var.get() == self._val
        bg  = CHIP_SEL  if sel else CHIP_UNSEL
        fg  = CHIP_FG_SEL if sel else CHIP_FG_UNSEL
        _pill(self, self._bw, self._bh, self._r, bg)
        self.create_text(self._bw // 2, self._bh // 2,
                         text=self._text, fill=fg, font=self._font)


class OverlayScrollbar:
    """마우스 스크롤 시 잠깐 나타났다 사라지는 얇은 오버레이 스크롤바."""

    THUMB_W = 4       # 썸 너비 px
    COLOR   = "#7c6af7"
    DELAY   = 1200    # ms — 이 시간 후 숨김

    def __init__(self, container: tk.Widget, treeview: tk.Widget):
        self._tree = treeview   # Treeview 또는 Canvas 모두 가능
        self._job  = None
        self._frac = (0.0, 1.0)

        # 컨테이너 오른쪽 끝에 얇은 Canvas 오버레이
        self._cv = tk.Canvas(
            container,
            width=self.THUMB_W + 4,
            bg=INPUT_BG,
            highlightthickness=0,
        )
        self._cv.place(relx=1.0, rely=0.0, anchor="ne",
                       width=self.THUMB_W + 4, relheight=1.0)

        treeview.configure(yscrollcommand=self._on_yscroll)
        treeview.bind("<MouseWheel>", self._on_wheel, add="+")

    # ── 내부 메서드 ───────────────────────────────────────────

    def _on_yscroll(self, first: str, last: str):
        self._frac = (float(first), float(last))
        self._draw()
        self._schedule_hide()

    def _draw(self):
        first, last = self._frac
        self._cv.delete("all")
        if last - first >= 1.0:
            return                        # 전체 보임 → 썸 숨김

        self._cv.update_idletasks()
        h = self._cv.winfo_height()
        if h <= 4:
            return

        y1 = max(2,   int(first * h))
        y2 = min(h-2, int(last  * h))
        r  = self.THUMB_W // 2
        x1, x2 = 2, 2 + self.THUMB_W

        # 위 반원
        self._cv.create_arc(x1, y1,     x2, y1+r*2,
                             start=0, extent=180,
                             fill=self.COLOR, outline=self.COLOR)
        # 아래 반원
        self._cv.create_arc(x1, y2-r*2, x2, y2,
                             start=180, extent=180,
                             fill=self.COLOR, outline=self.COLOR)
        # 사이 직선
        if y2 - r*2 > y1 + r*2:
            self._cv.create_rectangle(x1, y1+r, x2, y2-r,
                                       fill=self.COLOR, outline=self.COLOR)

    def _hide(self):
        self._cv.delete("all")
        self._job = None

    def _schedule_hide(self):
        if self._job:
            self._cv.after_cancel(self._job)
        self._job = self._cv.after(self.DELAY, self._hide)

    def _on_wheel(self, event):
        delta = -1 if event.delta > 0 else 1
        self._tree.yview_scroll(delta, "units")
        return "break"


# ── 메인 앱 ──────────────────────────────────────────────────

class ImNotAIApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("im-not-ai  —  AI 글 윤문기")
        self.geometry("900x900")
        self.minsize(800, 800)
        self.configure(bg=BG)

        self._api_key      = config.load_api_key()
        self._result_data: dict = {}
        self._opts_visible = False
        self._original_text = ""

        # 정밀 윤문 옵션
        self._sensitivity  = tk.StringVar(value="S1+S2")
        self._genre        = tk.StringVar(value="일반")
        self._change_limit = tk.StringVar(value="30%")

        self._build_ui()
        self._build_menu()
        self._apply_theme()
        self._bind_shortcuts()
        if not self._api_key:
            self.after(300, self._prompt_api_key)

    # ── UI 구성 ─────────────────────────────────────────────────

    def _build_ui(self):
        hdr = tk.Frame(self, bg=BG)
        hdr.pack(fill="x", padx=16, pady=(12, 0))
        tk.Label(hdr, text="im-not-ai",
                 font=(FONT_UI, 20, "bold"), fg="#b39ddb", bg=BG).pack(side="left")
        tk.Label(hdr, text="  AI 글투 탐지 · 한국어 윤문기",
                 font=(FONT_UI, 13), fg=SUBTEXT, bg=BG).pack(side="left", pady=4)
        RoundedButton(hdr, "⚙  API 키", command=self._prompt_api_key,
                      bg="#363650", fg=TEXT,
                      radius=12, padx=12, pady=5,
                      font=(FONT_UI, 10)).pack(side="right", padx=4)

        main = tk.Frame(self, bg=BG)
        main.pack(fill="both", expand=True, padx=16, pady=10)

        # uniform="col" 로 두 컬럼을 항상 동일 너비로 강제
        main.columnconfigure(0, weight=1, uniform="col")
        main.columnconfigure(1, weight=1, uniform="col")
        main.rowconfigure(0, weight=1)

        left = tk.Frame(main, bg=PANEL)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self._build_input_panel(left)

        right = tk.Frame(main, bg=PANEL)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self._build_output_panel(right)

        self._build_changes_panel(main)

        # 상태 표시줄 (하단 고정)
        self.lbl_status = tk.Label(self, text="",
                                    font=(FONT_UI, 11), fg=ACCENT, bg=BG)
        self.lbl_status.pack(pady=(0, 6))

    def _build_input_panel(self, parent):
        tk.Label(parent, text="입력 텍스트",
                 font=(FONT_UI, 12, "bold"), fg=TEXT, bg=PANEL
                 ).pack(anchor="w", padx=12, pady=(10, 4))

        self.input_text = tk.Text(
            parent, font=(FONT_KO, 12),
            bg=INPUT_BG, fg=TEXT, insertbackground=TEXT,
            relief="flat", wrap="word",
            selectbackground=CHIP_SEL, selectforeground="white",
        )
        self.input_text.pack(fill="both", expand=True, padx=10, pady=(0, 4))
        self.input_text.bind("<<Modified>>", self._on_input_modified)

        btn_row = tk.Frame(parent, bg=PANEL)
        btn_row.pack(fill="x", padx=10, pady=(2, 0))

        self.lbl_chars = tk.Label(btn_row, text="0자",
                                   font=(FONT_UI, 10), fg=SUBTEXT, bg=PANEL)
        self.lbl_chars.pack(side="left")
        tk.Label(btn_row, text=" ", bg=PANEL).pack(side="left", padx=2)
        RoundedButton(btn_row, "지우기", command=self._clear_input,
                      bg="#363650", fg=TEXT,
                      radius=10, padx=10, pady=4,
                      font=(FONT_UI, 10)).pack(side="left")

        self.btn_opts = RoundedButton(
            btn_row, "옵션 ▾", command=self._toggle_opts,
            bg="#363650", fg=ACCENT2,
            radius=10, padx=10, pady=4,
            font=(FONT_UI, 10),
        )
        self.btn_opts.pack(side="right", padx=(4, 0))

        self.btn_strict = RoundedButton(
            btn_row, "정밀 윤문", command=self._run_strict,
            bg=ACCENT2, fg=BTN_FG,
            radius=15, padx=18, pady=8,
            font=(FONT_UI, 11, "bold"),
        )
        self.btn_strict.pack(side="right", padx=(4, 0))

        self.btn_fast = RoundedButton(
            btn_row, "빠른 윤문 ▶", command=self._run_fast,
            bg=ACCENT, fg=BTN_FG,
            radius=15, padx=18, pady=8,
            font=(FONT_UI, 11, "bold"),
        )
        self.btn_fast.pack(side="right", padx=(4, 0))

        self.opts_frame = tk.Frame(parent, bg="#242438")
        self._build_opts_content(self.opts_frame)
        tk.Frame(parent, bg=PANEL, height=8).pack()

    def _build_opts_content(self, parent):
        SENS_DESC = {
            "S1만":  "가장 심각한 패턴만 제거 — 최소한의 수정, 원문 보존 우선",
            "S1+S2": "심각(S1) + 중간(S2) 패턴 처리 — 균형 잡힌 기본 설정",
            "전체":  "S1·S2에 S3 권고 패턴까지 포함 — 가장 꼼꼼한 윤문",
        }

        def row(label_text):
            f = tk.Frame(parent, bg="#242438")
            f.pack(fill="x", padx=12, pady=(6, 2))
            tk.Label(f, text=label_text,
                     font=(FONT_UI, 9), fg=SUBTEXT, bg="#242438",
                     width=8, anchor="w").pack(side="left")
            return f

        SENS_TOOLTIP = {
            "S1만":  "심각(S1) 패턴만 처리\n최소한의 수정, 원문 보존 우선",
            "S1+S2": "심각(S1)과 중간(S2) 패턴 처리\n균형 잡힌 기본 설정",
            "전체":  "S1·S2에 S3(권고) 패턴까지 포함\n가장 꼼꼼한 윤문",
        }

        # 탐지 범위 + 설명 레이블
        r1 = row("탐지 범위")
        for val in ["S1만", "S1+S2", "전체"]:
            chip = Chip(r1, val, self._sensitivity, val)
            chip.pack(side="left", padx=3)
            Tooltip(chip, SENS_TOOLTIP[val])

        self.lbl_sens_desc = tk.Label(
            parent, text=SENS_DESC[self._sensitivity.get()],
            font=(FONT_UI, 9), fg="#a0c8ff", bg="#242438",
            anchor="w", padx=20,
        )
        self.lbl_sens_desc.pack(fill="x")

        def _update_desc(*_):
            self.lbl_sens_desc.config(text=SENS_DESC.get(self._sensitivity.get(), ""))
        self._sensitivity.trace_add("write", _update_desc)

        r2 = row("장르")
        for val in ["일반", "학술", "비즈니스", "SNS"]:
            Chip(r2, val, self._genre, val).pack(side="left", padx=3)

        r3 = row("변경 상한")
        for val in ["30%", "50%"]:
            Chip(r3, val, self._change_limit, val).pack(side="left", padx=3)

        tk.Frame(parent, bg="#242438", height=6).pack()

    def _toggle_opts(self):
        self._opts_visible = not self._opts_visible
        if self._opts_visible:
            self.opts_frame.pack(fill="x", padx=10, pady=(0, 4))
            self.btn_opts.config(text="옵션 ▴")
        else:
            self.opts_frame.pack_forget()
            self.btn_opts.config(text="옵션 ▾")

    def _build_output_panel(self, parent):
        hdr = tk.Frame(parent, bg=PANEL)
        hdr.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(hdr, text="윤문 결과",
                 font=(FONT_UI, 12, "bold"), fg=TEXT, bg=PANEL).pack(side="left")
        self.lbl_grade = tk.Label(hdr, text="",
                                   font=(FONT_UI, 13, "bold"), fg=SUCCESS, bg=PANEL)
        self.lbl_grade.pack(side="right", padx=(0, 4))
        self.lbl_change = tk.Label(hdr, text="",
                                    font=(FONT_UI, 10), fg=SUBTEXT, bg=PANEL)
        self.lbl_change.pack(side="right", padx=8)

        self.output_text = tk.Text(
            parent, font=(FONT_KO, 12),
            bg=INPUT_BG, fg=TEXT, insertbackground=TEXT,
            relief="flat", wrap="word",
            selectbackground=CHIP_SEL, selectforeground="white",
            state="disabled",
        )
        self.output_text.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        bot = tk.Frame(parent, bg=PANEL)
        bot.pack(fill="x", padx=10, pady=(0, 10))
        self.lbl_output_chars = tk.Label(bot, text="",
                                          font=(FONT_UI, 10), fg=SUBTEXT, bg=PANEL)
        self.lbl_output_chars.pack(side="left")
        RoundedButton(bot, "저장", command=self._save_result,
                      bg="#363650", fg=TEXT,
                      radius=10, padx=10, pady=4,
                      font=(FONT_UI, 10)).pack(side="right", padx=4)
        RoundedButton(bot, "복사", command=self._copy_result,
                      bg="#363650", fg=TEXT,
                      radius=10, padx=10, pady=4,
                      font=(FONT_UI, 10)).pack(side="right")

    def _build_changes_panel(self, main_frame):
        """수정 내용 패널 (diff + 총평, 접이식)."""
        CHANGES_BG = "#1e1e30"
        self._changes_visible = False

        outer = tk.Frame(main_frame, bg=BG)
        outer.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 0))

        # 헤더 (토글 버튼 포함)
        hdr = tk.Frame(outer, bg=PANEL)
        hdr.pack(fill="x")

        tk.Label(hdr, text="수정 내용",
                 font=(FONT_UI, 11, "bold"), fg=TEXT, bg=PANEL).pack(side="left", padx=(12, 0), pady=6)

        self.lbl_changes_count = tk.Label(hdr, text="",
                                           font=(FONT_UI, 10), fg=SUBTEXT, bg=PANEL)
        self.lbl_changes_count.pack(side="left", padx=8)

        # diff 범례
        for bg, fg, label in [
            (DIFF_ADD_BG, DIFF_ADD_FG, " 추가 "),
            (DIFF_DEL_BG, DIFF_DEL_FG, " 삭제 "),
            (DIFF_CHG_BG, DIFF_CHG_FG, " 변경 "),
        ]:
            tk.Label(hdr, text=label, font=(FONT_UI, 8), fg=fg, bg=bg,
                     relief="flat").pack(side="left", padx=(0, 4))

        self.btn_changes_toggle = RoundedButton(
            hdr, "수정 내용 보기 ▾", command=self._toggle_changes,
            bg="#363650", fg=ACCENT2,
            radius=10, padx=10, pady=3,
            font=(FONT_UI, 9),
        )
        self.btn_changes_toggle.pack(side="right", padx=8, pady=4)

        # ── 접이식 본문: 고정 레이아웃 (스크롤 없음) ─────────────────
        # 초기엔 숨김 — _toggle_changes로 제어
        self._changes_wrap = tk.Frame(outer, bg=CHANGES_BG)

        # diff 텍스트 (고정 6줄)
        self.diff_text = tk.Text(
            self._changes_wrap, font=(FONT_KO, 11),
            bg=CHANGES_BG, fg=TEXT, insertbackground=TEXT,
            relief="flat", wrap="word", height=6,
            state="disabled",
        )
        self.diff_text.pack(fill="x", padx=10, pady=(6, 4))

        self.diff_text.tag_configure("diff_add",
                                      background=DIFF_ADD_BG, foreground=DIFF_ADD_FG)
        self.diff_text.tag_configure("diff_del",
                                      background=DIFF_DEL_BG, foreground=DIFF_DEL_FG,
                                      overstrike=True)
        self.diff_text.tag_configure("diff_chg",
                                      background=DIFF_CHG_BG, foreground=DIFF_CHG_FG)

        # 총평
        tk.Frame(self._changes_wrap, bg="#2a2a45", height=1).pack(
            fill="x", padx=10, pady=(4, 6))
        tk.Label(self._changes_wrap, text="총평",
                 font=(FONT_UI, 10, "bold"), fg=TEXT, bg=CHANGES_BG,
                 anchor="w").pack(fill="x", padx=12)
        self.review_text = tk.Label(
            self._changes_wrap,
            text="",
            font=(FONT_KO, 11),
            fg=TEXT, bg=CHANGES_BG,
            anchor="w", justify="left",
            wraplength=980,
        )
        self.review_text.pack(fill="x", padx=14, pady=(4, 14))

        # 더미 위젯 (_show_result 참조용)
        self.changes_body = self._changes_wrap
        self.lbl_pattern_count = tk.Label(self._changes_wrap, text="")
        self.tree = ttk.Treeview(self._changes_wrap,
                                  columns=("카테고리","심각도","원문 구절","수정 구절","이유"),
                                  show="headings")

    def _toggle_changes(self):
        self._changes_visible = not self._changes_visible
        if self._changes_visible:
            self._changes_wrap.pack(fill="x")
            self.btn_changes_toggle.config(text="수정 내용 닫기 ▴")
        else:
            self._changes_wrap.pack_forget()
            self.btn_changes_toggle.config(text="수정 내용 보기 ▾")
        self.update_idletasks()

    # ── 메뉴 & 단축키 ────────────────────────────────────────────

    def _build_menu(self):
        menubar = tk.Menu(self)

        # macOS 앱 메뉴 (앱 이름 메뉴)
        app_menu = tk.Menu(menubar, name="apple", tearoff=False)
        app_menu.add_command(label="im-not-ai 정보...", command=self._show_about)
        app_menu.add_separator()
        menubar.add_cascade(menu=app_menu)

        edit_menu = tk.Menu(menubar, tearoff=False)
        edit_menu.add_command(label="잘라내기",  accelerator="Command+X",
                              command=self._cmd_cut)
        edit_menu.add_command(label="복사",      accelerator="Command+C",
                              command=self._cmd_copy)
        edit_menu.add_command(label="붙여넣기",  accelerator="Command+V",
                              command=self._cmd_paste)
        edit_menu.add_command(label="모두 선택", accelerator="Command+A",
                              command=self._cmd_select_all)
        menubar.add_cascade(label="편집", menu=edit_menu)
        self.config(menu=menubar)

    def _show_about(self):
        win = tk.Toplevel(self)
        win.title("im-not-ai 정보")
        win.resizable(False, False)
        win.configure(bg=BG)
        win.geometry("380x210")
        win.transient(self)
        win.grab_set()
        # Esc 또는 클릭으로 닫기
        win.bind("<Escape>", lambda e: win.destroy())
        win.bind("<Return>",  lambda e: win.destroy())

        # 아이콘
        try:
            ico = tk.PhotoImage(file="icon_preview.png")
            ico_small = ico.subsample(4, 4)
            tk.Label(win, image=ico_small, bg=BG).pack(pady=(22, 4))
            win._ico = ico_small
        except Exception:
            tk.Frame(win, bg=BG, height=16).pack()

        # 앱 이름
        tk.Label(win, text="im-not-ai",
                 font=(FONT_UI, 22, "bold"), fg="#b39ddb", bg=BG).pack()

        # 버전
        tk.Label(win, text="v2.0",
                 font=(FONT_UI, 12), fg=SUBTEXT, bg=BG).pack(pady=(2, 10))

        # 구분선
        tk.Frame(win, bg=SUBTEXT, height=1).pack(fill="x", padx=40, pady=(0, 12))

        # 출처 레이블
        tk.Label(win, text="출처",
                 font=(FONT_UI, 9), fg=SUBTEXT, bg=BG).pack()

        # URL — 클릭 시 브라우저
        url = "https://github.com/epoko77-ai/im-not-ai"
        lbl_url = tk.Label(win, text=url,
                           font=(FONT_UI, 10), fg=ACCENT2, bg=BG,
                           cursor="hand2")
        lbl_url.pack(pady=(2, 18))
        lbl_url.bind("<Button-1>", lambda e: self._open_url(url))
        # hover 밑줄 효과
        lbl_url.bind("<Enter>", lambda e: lbl_url.config(font=(FONT_UI, 10, "underline")))
        lbl_url.bind("<Leave>", lambda e: lbl_url.config(font=(FONT_UI, 10)))

    @staticmethod
    def _open_url(url: str):
        import subprocess
        subprocess.Popen(["open", url])

    def _bind_shortcuts(self):
        # Cmd+V: 위젯 레벨 바인딩을 두지 않고 tkinter Aqua 네이티브 처리에 위임.
        # 위젯 레벨에 Cmd+V를 등록하면 macOS 시스템 핸들러를 막아 붙여넣기가 깨짐.
        for w in (self.input_text, self.output_text, self.diff_text):
            for seq in ("<Command-c>", "<Command-Key-c>"):
                w.bind(seq, self._cmd_copy)
            for seq in ("<Command-x>", "<Command-Key-x>"):
                w.bind(seq, self._cmd_cut)
            for seq in ("<Command-a>", "<Command-Key-a>"):
                w.bind(seq, self._cmd_select_all)
        # 윈도우 레벨 fallback — 포커스가 Text 밖에 있을 때만 실질적으로 동작
        for seq in ("<Command-v>", "<Command-Key-v>"):
            self.bind(seq, self._cmd_paste)
        for seq in ("<Command-c>", "<Command-Key-c>"):
            self.bind(seq, self._cmd_copy)
        for seq in ("<Command-x>", "<Command-Key-x>"):
            self.bind(seq, self._cmd_cut)
        for seq in ("<Command-a>", "<Command-Key-a>"):
            self.bind(seq, self._cmd_select_all)

    # ── 클립보드 조작 ────────────────────────────────────────────

    def _resolve_widget(self, event):
        w = event.widget if (event and hasattr(event, "widget")) else None
        if isinstance(w, tk.Text):
            return w
        return self.focus_get()

    def _clipboard_get(self) -> str:
        try:
            return self.clipboard_get()
        except tk.TclError:
            return ""

    def _clipboard_set(self, text: str):
        self.clipboard_clear()
        self.clipboard_append(text)

    def _cmd_paste(self, event=None):
        w = self._resolve_widget(event)
        if not (isinstance(w, tk.Text) and str(w.cget("state")) == "normal"):
            return "break"
        txt = self._clipboard_get()
        if txt:
            try:
                w.delete(tk.SEL_FIRST, tk.SEL_LAST)
            except tk.TclError:
                pass
            w.insert(tk.INSERT, txt)
        return "break"

    def _cmd_copy(self, event=None):
        w = self._resolve_widget(event)
        if isinstance(w, tk.Text):
            try:
                sel = w.get(tk.SEL_FIRST, tk.SEL_LAST)
                self._clipboard_set(sel)
            except tk.TclError:
                pass
        return "break"

    def _cmd_cut(self, event=None):
        w = self._resolve_widget(event)
        if isinstance(w, tk.Text) and str(w.cget("state")) == "normal":
            try:
                sel = w.get(tk.SEL_FIRST, tk.SEL_LAST)
                self._clipboard_set(sel)
                w.delete(tk.SEL_FIRST, tk.SEL_LAST)
            except tk.TclError:
                pass
        return "break"

    def _cmd_select_all(self, event=None):
        w = self._resolve_widget(event)
        if isinstance(w, tk.Text):
            w.tag_add("sel", "1.0", "end-1c")
        return "break"

    def _apply_theme(self):
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("Treeview",
                        background=INPUT_BG, foreground=TEXT,
                        fieldbackground=INPUT_BG, rowheight=24,
                        font=(FONT_KO, 10))
        style.configure("Treeview.Heading",
                        background=PANEL, foreground=SUBTEXT,
                        font=(FONT_UI, 10, "bold"), relief="flat")
        style.map("Treeview", background=[("selected", CHIP_SEL)])

    # ── diff 렌더링 ──────────────────────────────────────────────

    def _render_diff(self, original: str, rewritten: str):
        """원문과 윤문본의 차이를 색상으로 표시해 output_text에 삽입한다."""
        import re

        def tokenize(text):
            # 공백 포함 단어 단위 분리
            return re.findall(r'\S+|\s+', text)

        orig_tokens  = tokenize(original)
        new_tokens   = tokenize(rewritten)

        matcher = difflib.SequenceMatcher(None, orig_tokens, new_tokens, autojunk=False)

        self.diff_text.config(state="normal")
        self.diff_text.delete("1.0", "end")

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            orig_chunk = "".join(orig_tokens[i1:i2])
            new_chunk  = "".join(new_tokens[j1:j2])

            if tag == "equal":
                self.diff_text.insert("end", new_chunk)
            elif tag == "insert":
                self.diff_text.insert("end", new_chunk, "diff_add")
            elif tag == "delete":
                self.diff_text.insert("end", orig_chunk, "diff_del")
            elif tag == "replace":
                self.diff_text.insert("end", orig_chunk, "diff_del")
                self.diff_text.insert("end", new_chunk, "diff_chg")

        self.diff_text.config(state="disabled")

    # ── 총평 생성 ────────────────────────────────────────────────

    def _build_review(self, data: dict) -> str:
        grade       = data.get("grade", "?")
        change_rate = data.get("change_rate", 0.0)
        patterns    = data.get("patterns", [])
        summary     = data.get("summary", "")
        s1 = sum(1 for p in patterns if p.get("severity") == "S1")
        s2 = sum(1 for p in patterns if p.get("severity") == "S2")

        grade_desc = {
            "A": "AI 글투가 거의 없는 자연스러운 글로 개선됐습니다.",
            "B": "주요 AI 패턴이 제거됐으며 전반적으로 자연스럽습니다.",
            "C": "일부 AI 특유 표현이 남아있어 추가 검토를 권장합니다.",
            "D": "AI 패턴이 다수 남아있어 사람의 직접 검수가 필요합니다.",
        }.get(grade, "")

        lines = [f"■ 등급: {grade}  ({grade_desc})"]
        lines.append(f"■ 변경률: {change_rate:.1%}  (S1 {s1}건 · S2 {s2}건 · 총 {len(patterns)}건 수정)")

        if s1 > 0:
            s1_cats = [p.get("category","") for p in patterns if p.get("severity") == "S1"]
            lines.append(f"■ 필수 제거(S1): 카테고리 {', '.join(sorted(set(s1_cats)))} 패턴 삭제됨")

        if change_rate > 0.3:
            lines.append("⚠ 변경률이 30%를 넘었습니다. 원문 의도가 유지됐는지 확인하세요.")

        if summary:
            lines.append(f"■ AI 평가: {summary}")

        return "\n".join(lines)

    # ── 이벤트 핸들러 ───────────────────────────────────────────

    def _on_input_modified(self, _=None):
        self.after_idle(self._update_char_count)
        self.input_text.edit_modified(False)

    def _update_char_count(self, _=None):
        n = len(self.input_text.get("1.0", "end-1c"))
        color = WARN if n > 8000 else (ACCENT if n > 5000 else TEXT)
        self.lbl_chars.config(text=f"{n:,}자", fg=color)

    def _clear_input(self):
        self.input_text.delete("1.0", "end")
        self._update_char_count()

    def _copy_result(self):
        text = self.output_text.get("1.0", "end-1c")
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.lbl_status.config(text="결과가 클립보드에 복사됐습니다.", fg=SUCCESS)
            self.after(2000, lambda: self.lbl_status.config(text=""))

    def _save_result(self):
        text = self.output_text.get("1.0", "end-1c")
        if not text:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("텍스트", "*.txt"), ("모든 파일", "*")],
        )
        if path:
            review = self._build_review(self._result_data) if self._result_data else ""
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
                if review:
                    f.write(f"\n\n---\n{review}\n")
            self.lbl_status.config(text=f"저장 완료: {path}", fg=SUCCESS)
            self.after(3000, lambda: self.lbl_status.config(text=""))

    def _prompt_api_key(self):
        key = simpledialog.askstring(
            "OpenRouter API 키 설정",
            "OpenRouter API 키를 입력하세요:\n(https://openrouter.ai 에서 발급)",
            initialvalue=self._api_key, parent=self,
        )
        if key is not None:
            key = key.strip()
            self._api_key = key
            config.save_api_key(key)
            self.lbl_status.config(text="API 키가 저장됐습니다.", fg=SUCCESS)
            self.after(2000, lambda: self.lbl_status.config(text=""))

    def _set_busy(self, busy: bool):
        state = "disabled" if busy else "normal"
        self.btn_fast.config(state=state)
        self.btn_strict.config(state=state)

    def _show_result(self, data: dict):
        self._result_data = data
        rewritten   = data.get("rewritten", "")
        patterns    = data.get("patterns", [])
        grade       = data.get("grade", "?")
        change_rate = data.get("change_rate", 0.0)

        # ── 윤문 결과: 깨끗한 텍스트만 표시 ─────────────────────
        self.output_text.config(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.insert("1.0", rewritten)
        self.output_text.tag_add("body", "1.0", "end")
        self.output_text.tag_configure("body", foreground=TEXT)
        self.output_text.config(state="disabled")

        n = len(rewritten)
        self.lbl_output_chars.config(text=f"{n:,}자")

        self.lbl_grade.config(text=f"등급 {grade}", fg=GRADE_COLOR.get(grade, TEXT))
        self.lbl_change.config(text=f"변경률 {change_rate:.1%}")

        # ── 수정 내용 패널: diff + 총평 ───────────────────────────
        self._render_diff(self._original_text, rewritten)

        review = self._build_review(data)
        self.review_text.config(text=review)

        # 결과 도착 시 수정 내용 패널 자동 열기
        if not self._changes_visible:
            self._toggle_changes()

        # ── 탐지 패턴 트리 ────────────────────────────────────────
        for row in self.tree.get_children():
            self.tree.delete(row)

        sev_color = {"S1": DANGER, "S2": WARN, "S3": SUBTEXT}
        for p in patterns:
            sev = p.get("severity", "")
            self.tree.insert("", "end",
                             values=(
                                 p.get("category", ""),
                                 sev,
                                 p.get("original", p.get("span", ""))[:50],
                                 p.get("corrected", "")[:50],
                                 p.get("reason", ""),
                             ),
                             tags=(sev,))
            self.tree.tag_configure(sev, foreground=sev_color.get(sev, TEXT))

        s1 = sum(1 for p in patterns if p.get("severity") == "S1")
        s2 = sum(1 for p in patterns if p.get("severity") == "S2")
        count_text = f"S1: {s1}건 · S2: {s2}건 · 총 {len(patterns)}건"
        self.lbl_pattern_count.config(text=count_text)
        self.lbl_changes_count.config(text=count_text)
        self.lbl_status.config(text="윤문 완료!", fg=SUCCESS)
        self.after(3000, lambda: self.lbl_status.config(text=""))

    def _get_options(self) -> dict:
        return {
            "sensitivity":  self._sensitivity.get(),
            "genre":        self._genre.get(),
            "change_limit": self._change_limit.get(),
        }

    def _run_in_thread(self, fn, **extra):
        if not self._api_key:
            messagebox.showerror("API 키 없음", "OpenRouter API 키를 먼저 설정해주세요.")
            self._prompt_api_key()
            return
        text = self.input_text.get("1.0", "end-1c").strip()
        if not text:
            messagebox.showwarning("입력 없음", "윤문할 텍스트를 입력해주세요.")
            return
        self._original_text = text

        self._set_busy(True)
        self.lbl_status.config(text="처리 중...", fg=ACCENT)

        def task():
            try:
                result = fn(self._api_key, text,
                            on_progress=self._on_progress, **extra)
                self.after(0, self._show_result, result)
            except api_client.APIError as e:
                self.after(0, lambda: messagebox.showerror("API 오류", str(e)))
                self.after(0, lambda: self.lbl_status.config(text=""))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("오류", f"예상치 못한 오류:\n{e}"))
                self.after(0, lambda: self.lbl_status.config(text=""))
            finally:
                self.after(0, lambda: self._set_busy(False))

        threading.Thread(target=task, daemon=True).start()

    def _on_progress(self, msg: str):
        self.after(0, lambda: self.lbl_status.config(text=msg, fg=ACCENT))

    def _run_fast(self):
        self._run_in_thread(api_client.humanize_fast)

    def _run_strict(self):
        self._run_in_thread(api_client.humanize_strict, options=self._get_options())


if __name__ == "__main__":
    app = ImNotAIApp()
    app.mainloop()
