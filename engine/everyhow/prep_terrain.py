import json, numpy as np
from PIL import Image, ImageDraw, ImageFilter
Image.MAX_IMAGE_PIXELS = None
src = Image.open('ne/GRAY_50M_SR_W.tif'); W, H = src.size
a = np.asarray(src)
mask = Image.new('L', (W, H), 0); d = ImageDraw.Draw(mask)
for poly in json.load(open('land50.json')):
    for k, ring in enumerate(poly):
        un = [list(ring[0])]
        for lon, lat in ring[1:]:  # unwrap rings that cross the 180th meridian, then draw them on both sides
            while lon - un[-1][0] > 180: lon -= 360
            while lon - un[-1][0] < -180: lon += 360
            un.append([lon, lat])
        for sh in (-360, 0, 360):
            pts = [((lon + sh + 180) / 360 * W, (90 - lat) / 180 * H) for lon, lat in un]
            if max(p[0] for p in pts) < 0 or min(p[0] for p in pts) > W: continue
            d.polygon(pts, fill=0 if k else 255)
gl = mask.filter(ImageFilter.GaussianBlur(18))
A, M, G = a, np.asarray(mask), np.asarray(gl)
img = Image.new('RGB', (W, H))
for y0 in range(0, H, 300):
  a = A[y0:y0+300]; m = M[y0:y0+300].astype(np.float32) / 255; glow = G[y0:y0+300].astype(np.float32) / 255; h = a.shape[0]
  shade = np.clip(a.astype(np.float32) / 205.0, 0, 1.25)               # 1 = flat land, <1 shadowed slopes, >1 lit slopes
  lo, hi = np.array([8, 22, 25]), np.array([84, 124, 112])
  land = lo + (hi - lo) * (np.clip((shade - 0.45) / 0.75, 0, 1) ** 1.25)[..., None]
  # latitude tint: a little warmer/drier towards the tropics, icier near the poles
  lat = np.linspace(90, -90, H)[y0:y0+h, None, None]
  land = land * (1 + 0.10 * np.exp(-((np.abs(lat) - 25) / 12) ** 2) * np.array([1.0, .6, .1]))
  pol = np.clip((np.abs(lat) - 58) / 15, 0, 1); land = land * (1 - .2 * pol) + np.array([90, 110, 115]) * .2 * pol
  ocean = np.array([5, 15, 22]) + np.array([10, 32, 38]) * (glow * (1 - m))[..., None] * 1.6
  out = land * m[..., None] + ocean * (1 - m[..., None])
  img.paste(Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGB'), (0, y0))
img.save('terrain_full.jpg', quality=84, optimize=True, progressive=True)
img.resize((8192, 4096), Image.LANCZOS).save('terrain_8k.jpg', quality=84, optimize=True, progressive=True)
img.resize((1600, 800), Image.LANCZOS).save('terrain_preview.jpg', quality=85)
