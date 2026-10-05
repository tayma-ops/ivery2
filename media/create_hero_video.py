"""Render the site's original looping healthcare motion graphic."""
from pathlib import Path
import math
import numpy as np
from PIL import Image, ImageDraw
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parent
ROOT.mkdir(exist_ok=True)
W, H, FPS, SECONDS = 1280, 720, 24, 8
y, x = np.mgrid[0:H, 0:W]


def frame(t):
    phase = 2 * math.pi * t / SECONDS
    glow = np.exp(-(((x - (410 + 100 * math.sin(phase))) / 550) ** 2
                    + ((y - (330 + 60 * math.cos(phase))) / 480) ** 2))
    rgb = np.zeros((H, W, 3), dtype=np.uint8)
    for c, (base, strength) in enumerate([(5, 12), (42, 70), (35, 53)]):
        rgb[:, :, c] = base + strength * glow
    im = Image.fromarray(rgb)
    d = ImageDraw.Draw(im)
    # A fine grid and orbit lines give the scene depth without distracting from copy.
    for gx in range(0, W, 80):
        d.line((gx, 0, gx, H), fill=(18, 71, 59))
    for gy in range(0, H, 80):
        d.line((0, gy, W, gy), fill=(18, 71, 59))
    for radius in (220, 300, 380):
        d.ellipse((390-radius, 355-radius, 390+radius, 355+radius),
                  outline=(28, 104, 78), width=2)
    for i in range(22):
        a = phase + i * 2.399
        r = 190 + (i % 5) * 35
        px, py = 390 + math.cos(a) * r, 355 + math.sin(a) * r * .75
        size = 2 + i % 3
        d.ellipse((px-size, py-size, px+size, py+size), fill=(76, 175, 128))
    # Main calendar card, floating smoothly in a seamless loop.
    cx, cy = 410, 350 + 14 * math.sin(phase)
    box = (cx-147, cy-155, cx+147, cy+155)
    d.rounded_rectangle((box[0]+12, box[1]+18, box[2]+12, box[3]+18),
                        radius=32, fill=(6, 47, 37))
    d.rounded_rectangle(box, radius=32, fill=(222, 249, 235), outline=(130, 227, 170), width=3)
    d.rounded_rectangle((cx-147, cy-155, cx+147, cy-65), radius=32, fill=(36, 169, 99))
    d.rectangle((cx-147, cy-110, cx+147, cy-65), fill=(36, 169, 99))
    for dx in (-83, 83):
        d.rounded_rectangle((cx+dx-9, cy-174, cx+dx+9, cy-126), radius=9, fill=(167, 240, 197))
    for row in range(3):
        for col in range(4):
            px, py = cx-91+col*60, cy-27+row*55
            d.rounded_rectangle((px-13, py-12, px+13, py+12), radius=6, fill=(165, 218, 189))
    d.ellipse((cx+36, cy+49, cx+148, cy+161), fill=(20, 151, 84), outline=(222, 249, 235), width=5)
    d.line([(cx+65, cy+106), (cx+84, cy+125), (cx+121, cy+85)], fill=(239, 255, 245), width=10)
    # A healthcare cross and heart in smaller satellite cards.
    for sx, sy, kind in [(165, 214, 'cross'), (674, 452, 'heart')]:
        sy += 18 * math.sin(phase + (0 if kind == 'cross' else math.pi))
        d.rounded_rectangle((sx-63, sy-63, sx+63, sy+63), radius=26,
                            fill=(13, 91, 66), outline=(66, 164, 113), width=2)
        if kind == 'cross':
            d.rounded_rectangle((sx-11, sy-35, sx+11, sy+35), radius=6, fill=(143, 235, 179))
            d.rounded_rectangle((sx-35, sy-11, sx+35, sy+11), radius=6, fill=(143, 235, 179))
        else:
            points = []
            scale = 2.2 * (1 + .035 * math.sin(phase * 2))
            for a in np.linspace(0, 2*math.pi, 100):
                hx = 16 * math.sin(a)**3
                hy = 13*math.cos(a)-5*math.cos(2*a)-2*math.cos(3*a)-math.cos(4*a)
                points.append((sx+hx*scale, sy-hy*scale))
            d.polygon(points, fill=(143, 235, 179))
    # Subtle pulse line across the bottom.
    pulse = [(0, 610), (240, 610), (263, 595), (282, 631), (308, 568),
             (333, 648), (358, 600), (382, 610), (W, 610)]
    d.line(pulse, fill=(56, 143, 103), width=3)
    return im


writer = imageio_ffmpeg.write_frames(
    str(ROOT / 'hero-video.mp4'), (W, H), fps=FPS,
    codec='libx264', pix_fmt_out='yuv420p', quality=7,
    output_params=['-movflags', '+faststart', '-an'],
)
writer.send(None)
try:
    for n in range(FPS * SECONDS):
        img = frame(n/FPS)
        if n == 0:
            img.save(ROOT / 'hero-poster.jpg', quality=90)
        writer.send(img.tobytes())
finally:
    writer.close()
print('Created hero-video.mp4 and hero-poster.jpg')
