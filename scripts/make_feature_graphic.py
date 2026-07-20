"""1024x500 feature graphic for Google Play — orange on dark navy."""
from PIL import Image, ImageDraw, ImageFont
import os
OUT = '/app/frontend/store-assets/feature_graphic.png'
os.makedirs('/app/frontend/store-assets', exist_ok=True)
W, H = 1024, 500
DARK = (11, 16, 32)
ORANGE = (255, 94, 0)
WHITE = (245, 247, 255)
SUB = (160, 174, 192)
img = Image.new('RGB', (W, H), DARK)
draw = ImageDraw.Draw(img)

def fnt(size, bold=False):
    for p in [f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf"]:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

draw.text((50, 70), 'GOALPILOT', fill=ORANGE, font=fnt(40, True))
draw.text((50, 110), 'Turn any goal', fill=WHITE, font=fnt(70, True))
draw.text((50, 188), 'into daily wins.', fill=WHITE, font=fnt(70, True))
draw.text((50, 290), 'AI-built plans · streaks · weekly coaching', fill=SUB, font=fnt(32))
draw.rounded_rectangle((50, 410, 310, 460), radius=24, fill=ORANGE)
draw.text((80, 420), 'Free · iOS & Android', fill=DARK, font=fnt(22))

PW, PH = 280, 420
PX, PY = W - PW - 60, (H - PH) // 2
draw.rounded_rectangle((PX-6, PY-6, PX+PW+6, PY+PH+6), radius=36, fill=(35, 42, 60))
draw.rounded_rectangle((PX, PY, PX+PW, PY+PH), radius=30, fill=(20, 26, 44))
draw.rounded_rectangle((PX+100, PY+8, PX+180, PY+22), radius=6, fill=(35, 42, 60))

cx, cy = PX + PW // 2, PY + 110
draw.ellipse((cx-50, cy-50, cx+50, cy+50), outline=(50, 60, 80), width=8)
draw.arc((cx-50, cy-50, cx+50, cy+50), start=-90, end=180, fill=ORANGE, width=8)
draw.text((cx-25, cy-14), '67%', fill=WHITE, font=fnt(28, True))

for i, label in enumerate(['\u2713 Morning run', '\u2713 Read 20 pages', '\u25cb Plan tomorrow']):
    ly = PY + 190 + i * 38
    draw.rounded_rectangle((PX+24, ly, PX+PW-24, ly+30), radius=8, fill=(30, 38, 58))
    draw.text((PX+36, ly+6), label, fill=WHITE if i < 2 else SUB, font=fnt(20))

draw.rounded_rectangle((PX+24, PY+340, PX+PW-24, PY+380), radius=12, fill=ORANGE)
draw.text((PX+40, PY+347), '7-day streak', fill=DARK, font=fnt(20, True))
img.save(OUT, 'PNG')
print(f'Saved {OUT}')
