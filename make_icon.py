"""
im-not-ai 아이콘 생성기
콘셉트: 어두운 보라 원형 배경 + 흰 붓/펜 + 빛나는 글자 획
"""
import math
from PIL import Image, ImageDraw, ImageFilter

SIZE = 1024


def lerp(a, b, t):
    return a + (b - a) * t


def draw_icon(size=SIZE) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2
    r = size // 2

    # ── 배경 원: 방사형 그라디언트 (보라 → 남색) ──────────────
    bg = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bg_draw = ImageDraw.Draw(bg)

    steps = 180
    for i in range(steps, 0, -1):
        t = i / steps
        ri = int(r * t)
        # 중앙: #6b4fa8 (보라)  가장자리: #1a1535 (어두운 남보라)
        col = (
            int(lerp(0x1a, 0x6b, t)),
            int(lerp(0x15, 0x4f, t)),
            int(lerp(0x35, 0xa8, t)),
            255,
        )
        bg_draw.ellipse(
            [cx - ri, cy - ri, cx + ri, cy + ri],
            fill=col,
        )
    img.paste(bg, (0, 0), bg)

    # ── 미묘한 내부 광채 (위쪽 하이라이트) ───────────────────
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse(
        [int(cx - r * 0.6), int(cy - r * 0.75),
         int(cx + r * 0.6), int(cy + r * 0.05)],
        fill=(255, 255, 255, 28),
    )
    glow = glow.filter(ImageFilter.GaussianBlur(radius=size * 0.08))
    img = Image.alpha_composite(img, glow)

    # ── 붓 모양 그리기 ────────────────────────────────────────
    # 붓대 (오른쪽 위 → 왼쪽 아래 대각선)
    draw = ImageDraw.Draw(img)

    sc = size / SIZE  # 크기 스케일
    lw_base = max(2, int(22 * sc))

    def pt(x, y):
        return (int(x * sc), int(y * sc))

    # 붓대
    draw.line([pt(720, 155), pt(310, 565)],
              fill=(255, 255, 255, 230), width=int(30 * sc))

    # 붓대 끝 캡 (원형)
    cap_r = int(16 * sc)
    for cx2, cy2, col in [
        (720, 155, (230, 200, 255, 200)),   # 위 끝
    ]:
        draw.ellipse(
            [pt(cx2 - cap_r, cy2 - cap_r),
             pt(cx2 + cap_r, cy2 + cap_r)],
            fill=col,
        )

    # 붓털 (아래 뾰족한 삼각형)
    brush_tip = [
        pt(310, 565),   # 연결점
        pt(268, 620),
        pt(290, 710),
        pt(335, 650),
        pt(310, 565),
    ]
    draw.polygon(brush_tip, fill=(255, 240, 200, 240))

    # 붓 옆면 (약간 두께감)
    draw.line([pt(268, 620), pt(290, 710)],
              fill=(255, 220, 160, 200), width=int(4 * sc))

    # ── 붓 끝 광채 (황금빛 잉크) ─────────────────────────────
    ink_glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ig_draw = ImageDraw.Draw(ink_glow)
    for rg, alpha in [(90, 70), (60, 110), (35, 160)]:
        rg = int(rg * sc)
        tip_x, tip_y = int(290 * sc), int(710 * sc)
        ig_draw.ellipse(
            [tip_x - rg, tip_y - rg, tip_x + rg, tip_y + rg],
            fill=(255, 210, 80, alpha),
        )
    ink_glow = ink_glow.filter(ImageFilter.GaussianBlur(radius=int(18 * sc)))
    img = Image.alpha_composite(img, ink_glow)

    # ── 붓이 쓴 획 3개 (한글 획 느낌) ────────────────────────
    draw = ImageDraw.Draw(img)

    strokes = [
        # (시작x, 시작y, 끝x, 끝y, 굵기, 불투명도)
        (420, 430, 650, 430, 18, 200),   # 가로획
        (530, 340, 530, 540, 18, 200),   # 세로획
        (430, 530, 640, 630, 14, 160),   # 사선획 (아래)
    ]
    for x1, y1, x2, y2, lw, alpha in strokes:
        # 획 끝부분 살짝 뭉툭하게
        draw.line(
            [pt(x1, y1), pt(x2, y2)],
            fill=(255, 255, 255, alpha),
            width=int(lw * sc),
        )
        # 획 끝 둥글게
        for ex, ey in [(x1, y1), (x2, y2)]:
            er = int(lw * sc // 2)
            draw.ellipse(
                [pt(ex - lw // 2, ey - lw // 2),
                 pt(ex + lw // 2, ey + lw // 2)],
                fill=(255, 255, 255, alpha),
            )

    # ── 획 글로우 (은은한 흰빛) ───────────────────────────────
    stroke_glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sg_draw = ImageDraw.Draw(stroke_glow)
    for x1, y1, x2, y2, lw, _ in strokes:
        sg_draw.line(
            [pt(x1, y1), pt(x2, y2)],
            fill=(200, 180, 255, 90),
            width=int((lw + 14) * sc),
        )
    stroke_glow = stroke_glow.filter(ImageFilter.GaussianBlur(radius=int(12 * sc)))
    img = Image.alpha_composite(img, stroke_glow)

    # ── 원형 테두리 (미묘한 선) ───────────────────────────────
    draw = ImageDraw.Draw(img)
    border_w = max(2, int(6 * sc))
    draw.ellipse(
        [border_w, border_w, size - border_w, size - border_w],
        outline=(180, 140, 255, 100),
        width=border_w,
    )

    return img


def make_icns(output_path: str):
    """macOS .icns 파일 생성"""
    import os
    import subprocess

    iconset_dir = output_path.replace(".icns", ".iconset")
    os.makedirs(iconset_dir, exist_ok=True)

    # macOS 요구 크기 목록
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    for s in sizes:
        icon = draw_icon(s)
        icon.save(f"{iconset_dir}/icon_{s}x{s}.png")
        # @2x (Retina)
        if s <= 512:
            icon2 = draw_icon(s * 2)
            icon2.save(f"{iconset_dir}/icon_{s}x{s}@2x.png")

    subprocess.run(
        ["iconutil", "-c", "icns", iconset_dir, "-o", output_path],
        check=True,
    )
    import shutil
    shutil.rmtree(iconset_dir)
    print(f"✅ 아이콘 생성 완료: {output_path}")


if __name__ == "__main__":
    import os
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    make_icns("icon.icns")
    # 미리보기용 PNG
    draw_icon(512).save("icon_preview.png")
    print("🖼  미리보기: icon_preview.png")
