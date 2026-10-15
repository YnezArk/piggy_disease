# -*- coding: utf-8 -*-
"""make_assets.py — 烘焙 PPT 背景与渐变素材（配合 pptxgenjs 生成器）
产出 assets/:
  bg_cover.png   封面背景（深蓝渐变+科技节点+声波剪影）
  bg_content.png 内容页背景（更克制的底纹）
  pill.png       栏目标题胶囊（蓝色渐变+辉光）
  banner.png     底部总结条（横向蓝色渐变+辉光）
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
os.makedirs(OUT, exist_ok=True)
RNG = np.random.default_rng(42)

W, H = 2400, 1350
TOP = np.array([15, 44, 96])      # #0F2C60
BOT = np.array([7, 21, 49])       # #071531


def vgrad(w, h, top, bot):
    t = np.linspace(0, 1, h)[:, None, None]
    img = top[None, None, :] * (1 - t) + bot[None, None, :] * t
    return np.repeat(img, w, axis=1).astype(np.float64)


def radial(w, h, cx, cy, radius, color, strength):
    """soft radial glow (screen add)"""
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / radius
    a = np.clip(1 - d, 0, 1) ** 2 * strength
    return a[:, :, None] * np.array(color)[None, None, :]


def add_noise(arr, sigma=3.0):
    return np.clip(arr + RNG.normal(0, sigma, arr.shape), 0, 255)


def vignette(arr, strength=0.35):
    h, w = arr.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy = w / 2, h / 2
    d = np.sqrt(((xx - cx) / cx) ** 2 + ((yy - cy) / cy) ** 2)
    m = np.clip(1 - strength * np.clip(d - 0.45, 0, 1.6) ** 1.5, 0, 1)
    return arr * m[:, :, None]


def draw_grid(draw, w, h, step=150, color=(70, 110, 190, 16), lw=1):
    for x in range(0, w, step):
        draw.line([(x, 0), (x, h)], fill=color, width=lw)
    for y in range(0, h, step):
        draw.line([(0, y), (w, y)], fill=color, width=lw)


def draw_nodes(img, region, n=26, seed=1):
    """tech node-graph decoration: dots + faint connecting lines"""
    rng = np.random.default_rng(seed)
    x0, y0, x1, y1 = region
    pts = [(rng.integers(x0, x1), rng.integers(y0, y1)) for _ in range(n)]
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i, p in enumerate(pts):
        # connect to 1-2 nearest
        dists = sorted(((np.hypot(p[0]-q[0], p[1]-q[1]), q) for j, q in enumerate(pts) if j != i))
        for _, q in dists[:rng.integers(1, 3)]:
            d.line([p, q], fill=(80, 140, 230, 46), width=2)
    for i, p in enumerate(pts):
        r = int(rng.integers(5, 12))
        col = (90, 160, 255, 150) if i % 7 else (70, 214, 255, 190)
        if i % 11 == 3:
            col = (245, 196, 78, 180)
        d.ellipse([p[0]-r, p[1]-r, p[0]+r, p[1]+r], fill=col)
    return Image.alpha_composite(img.convert("RGBA"), layer)


def draw_wave(img, baseline_y, w, n_bars=110, max_h=150, alpha=110, seed=7, x0=0, x1=None):
    """audio waveform silhouette"""
    rng = np.random.default_rng(seed)
    x1 = x1 or w
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    xs = np.linspace(x0 + 20, x1 - 20, n_bars)
    # smooth pseudo-random envelope
    env = rng.uniform(0.25, 1.0, n_bars)
    k = np.array([0.25, 0.5, 0.25])
    env = np.convolve(env, k, mode="same")
    env = env / env.max()
    for x, e in zip(xs, env):
        bh = int(12 + e * max_h)
        accent = rng.random() < 0.08
        col = (70, 200, 255, alpha + 60) if accent else (60, 130, 230, alpha)
        d.rounded_rectangle([x - 5, baseline_y - bh, x + 5, baseline_y], radius=5, fill=col)
    return Image.alpha_composite(img.convert("RGBA"), layer)


def compose_base(glow_params, grid_alpha, seed_offset=0):
    base = vgrad(W, H, TOP, BOT)
    for (cx, cy, r, col, s) in glow_params:
        base = base + radial(W, H, cx, cy, r, col, s)
    base = vignette(base)
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw_grid(ImageDraw.Draw(layer), W, H, step=150, color=(80, 120, 200, grid_alpha))
    img = Image.alpha_composite(img, layer)
    return img


def save(img, name, jpg=False):
    out = add_noise(np.array(img.convert("RGB")).astype(np.float64), 2.5)
    im = Image.fromarray(out.astype(np.uint8))
    if jpg:
        im = im.resize((2160, 1215), Image.LANCZOS)
        im.save(os.path.join(OUT, name.replace(".png", ".jpg")), quality=86, optimize=True)
        print("saved", name.replace(".png", ".jpg"))
    else:
        im.save(os.path.join(OUT, name), optimize=True)
        print("saved", name)


# ── bg_cover ─────────────────────────────────────────────
img = compose_base(
    glow_params=[
        (900, 380, 1500, (30, 92, 190), 0.55),   # main top area glow
        (2050, 1050, 1100, (23, 72, 156), 0.5),  # bottom-right glow
        (520, 1150, 700, (16, 120, 150), 0.22),  # cyan hint left-bottom
    ],
    grid_alpha=14,
)
img = draw_nodes(img, (1350, 120, 2380, 950), n=30, seed=11)
img = draw_wave(img, H - 26, W, n_bars=130, max_h=190, alpha=95, seed=5)
save(img, "bg_cover.png", jpg=True)

# ── bg_content ───────────────────────────────────────────
img = compose_base(
    glow_params=[
        (1250, 250, 1700, (24, 74, 158), 0.4),
        (2250, 1250, 900, (16, 52, 120), 0.35),
    ],
    grid_alpha=10,
)
img = draw_nodes(img, (1750, 950, 2390, 1340), n=14, seed=23)
img = draw_wave(img, H - 18, W, n_bars=150, max_h=70, alpha=55, seed=9)
save(img, "bg_content.png", jpg=True)


# ── pill.png （栏目标题胶囊, 1200×200）────────────────────
def rounded_mask(w, h, r):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=255)
    return m


def hgrad_h(w, h, left, right):
    t = np.linspace(0, 1, w)[None, :, None]
    return np.repeat(left[None, None, :] * (1 - t) + right[None, None, :] * t, h, axis=0)


pw, ph, pr = 1200, 200, 36
pill = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
# horizontal + vertical blend: bright blue, lighter at left-top
grad = hgrad_h(pw, ph, np.array([60, 130, 250]), np.array([22, 100, 226])).astype(np.float64)
vt = np.linspace(0, 1, ph)[:, None, None]
grad = grad * (1 - 0.25 * vt) + np.array([120, 180, 255])[None, None, :] * (0.25 * (1 - vt))
grad = np.clip(grad, 0, 255)
grad = np.array(Image.fromarray(grad.astype(np.uint8)).filter(ImageFilter.GaussianBlur(1)))
pill_img = Image.fromarray(grad.astype(np.uint8)).convert("RGBA")
pill_img.putalpha(rounded_mask(pw, ph, pr))
# glow copy
glow = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
gg = hgrad_h(pw, ph, np.array([70, 140, 255]), np.array([40, 120, 240])).astype(np.uint8)
glow_img = Image.fromarray(gg).convert("RGBA")
glow_img.putalpha(rounded_mask(pw, ph, pr).point(lambda v: int(v * 0.55)))
glow_img = glow_img.filter(ImageFilter.GaussianBlur(14))
canvas = Image.new("RGBA", (pw + 60, ph + 60), (0, 0, 0, 0))
canvas.alpha_composite(glow_img, (30, 30))
canvas.alpha_composite(pill_img, (30, 30))
# top highlight line
dc = ImageDraw.Draw(canvas)
dc.rounded_rectangle([31, 31, 30 + pw - 2, 30 + ph - 2], radius=pr, outline=(150, 200, 255, 110), width=3)
dc.line([(90, 44), (pw - 60, 44)], fill=(210, 235, 255, 130), width=3)
canvas.save(os.path.join(OUT, "pill.png"))
print("saved pill.png")

# ── banner.png （底部总结条, 2400×150）───────────────────
bw, bh, br = 2400, 150, 30
grad = hgrad_h(bw, bh, np.array([24, 88, 208]), np.array([70, 160, 255])).astype(np.float64)
# richer middle
mid = radial(bw, bh, bw * 0.62, bh * 0.5, bw * 0.55, (110, 190, 255), 0.5)
grad = grad + mid
vt = np.linspace(0, 1, bh)[:, None, None]
grad = grad * (1 - 0.22 * vt) + np.array([130, 195, 255])[None, None, :] * (0.22 * (1 - vt))
grad = np.clip(grad, 0, 255).astype(np.uint8)
ban = Image.fromarray(grad).convert("RGBA")
ban.putalpha(rounded_mask(bw, bh, br))
glow_img = Image.fromarray(grad).convert("RGBA")
glow_img.putalpha(rounded_mask(bw, bh, br).point(lambda v: int(v * 0.5)))
glow_img = glow_img.filter(ImageFilter.GaussianBlur(16))
canvas = Image.new("RGBA", (bw + 80, bh + 80), (0, 0, 0, 0))
canvas.alpha_composite(glow_img, (40, 40))
canvas.alpha_composite(ban, (40, 40))
dc = ImageDraw.Draw(canvas)
dc.rounded_rectangle([41, 41, 40 + bw - 2, 40 + bh - 2], radius=br, outline=(160, 205, 255, 120), width=3)
dc.line([(120, 56), (bw - 80, 56)], fill=(225, 240, 255, 120), width=4)
canvas.save(os.path.join(OUT, "banner.png"))
print("saved banner.png")

# ── small accents: 声波小图标条 & 圆点 glow（可选微素材）────
dot = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
dd = ImageDraw.Draw(dot)
dd.ellipse([18, 18, 78, 78], fill=(90, 170, 255, 255))
glowd = Image.new("RGBA", (140, 140), (0, 0, 0, 0))
gd = ImageDraw.Draw(glowd)
gd.ellipse([16, 16, 124, 124], fill=(90, 170, 255, 160))
glowd = glowd.filter(ImageFilter.GaussianBlur(18))
canvas = Image.new("RGBA", (140, 140), (0, 0, 0, 0))
canvas.alpha_composite(glowd)
canvas.alpha_composite(dot, (22, 22))
canvas.save(os.path.join(OUT, "dot_blue.png"))
print("saved dot_blue.png")
print("ALL ASSETS DONE ->", OUT)
