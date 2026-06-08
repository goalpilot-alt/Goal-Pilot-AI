"""Generate Google Play Feature Graphic 1024x500 PNG.
Brand: orange #FF5E00 accent on dark navy #0B1020.
"""
from PIL import Image, ImageDraw, ImageFont
import os

OUT = "/app/screenshots/feature_graphic.png"
W, H = 1024, 500
DARK = (11, 16, 32)        # #0B1020
ORANGE = (255, 94, 0)      # #FF5E00
WHITE = (245, 247, 255)
SUB = (160, 174, 192)

img = Image.new("RGB", (W, H), DARK)
draw = ImageDraw.Draw(img)

# Try to find a system font, fall back to default
def get_font(size, bold=False):
    candidates = [
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf",
        f"/usr/share/fonts/truetype/liberation/LiberationSans-{'Bold' if bold else 'Regular'}.ttf",
    ]
    for c in candidates:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return ImageFont.load_default()

font_brand = get_font(40, bold=True)
font_title = get_font(70, bold=True)
font_tag   = get_font(32)
font_small = get_font(22)

# Left side: text
PAD_L = 50
y = 110

# Brand label (small, orange)
draw.text((PAD_L, 70), "GOALPILOT", fill=ORANGE, font=font_brand)

# Big title
title_lines = ["Turn any goal", "into daily wins."]
for line in title_lines:
    draw.text((PAD_L, y), line, fill=WHITE, font=font_title)
    y += 78

# Tagline
y += 12
draw.text((PAD_L, y), "AI-built plans · streaks · weekly coaching", fill=SUB, font=font_tag)

# Bottom badge / CTA
draw.rounded_rectangle((PAD_L, 410, PAD_L + 260, 460), radius=24, fill=ORANGE)
draw.text((PAD_L + 30, 420), "Free · iOS & Android", fill=DARK, font=font_small)

# Right side decorative: phone mock frame
PHONE_W, PHONE_H = 280, 420
PX = W - PHONE_W - 60
PY = (H - PHONE_H) // 2
# Phone outline
draw.rounded_rectangle((PX - 6, PY - 6, PX + PHONE_W + 6, PY + PHONE_H + 6), radius=36, fill=(35, 42, 60))
draw.rounded_rectangle((PX, PY, PX + PHONE_W, PY + PHONE_H), radius=30, fill=(20, 26, 44))
# Notch
draw.rounded_rectangle((PX + 100, PY + 8, PX + 180, PY + 22), radius=6, fill=(35, 42, 60))
# Mock content inside phone — 3 progress cards
card_y = PY + 50
# Big circular "progress"
cx, cy = PX + PHONE_W // 2, card_y + 60
draw.ellipse((cx-50, cy-50, cx+50, cy+50), outline=ORANGE, width=8)
draw.ellipse((cx-50, cy-50, cx+50, cy+50), outline=(50, 60, 80), width=8)  # base
# Re-draw arc as filled approx
draw.arc((cx-50, cy-50, cx+50, cy+50), start=-90, end=180, fill=ORANGE, width=8)
draw.text((cx-25, cy-14), "67%", fill=WHITE, font=font_brand)

# 3 task lines
for i, label in enumerate(["✓ Morning run", "✓ Read 20 pages", "○ Plan tomorrow"]):
    ly = card_y + 140 + i * 38
    draw.rounded_rectangle((PX + 24, ly, PX + PHONE_W - 24, ly + 30), radius=8, fill=(30, 38, 58))
    draw.text((PX + 36, ly + 6), label, fill=WHITE if i < 2 else SUB, font=font_small)

# Streak flame badge
draw.rounded_rectangle((PX + 24, card_y + 280, PX + PHONE_W - 24, card_y + 320), radius=12, fill=ORANGE)
draw.text((PX + 40, card_y + 287), "🔥 7-day streak", fill=DARK, font=font_small)

img.save(OUT, format="PNG")
print(f"Saved {OUT} ({W}x{H})")
