"""Render STL previews (iso / top / underside) into previews/ and print mesh sanity stats."""
import os, math, numpy as np, trimesh
from PIL import Image, ImageDraw

def render(mesh, out, az=35, el=25, size=1100, title=""):
    m = mesh.copy()
    m.apply_translation(-m.bounding_box.centroid)
    a, e = math.radians(az), math.radians(el)
    Rz = np.array([[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, math.cos(e), -math.sin(e)], [0, math.sin(e), math.cos(e)]])
    R = Rx @ Rz
    v = m.vertices @ R.T
    tri = v[m.faces]
    order = np.argsort(-tri[:, :, 1].mean(axis=1))
    n = m.face_normals @ R.T
    light = np.array([-0.4, -0.7, 0.6]); light /= np.linalg.norm(light)
    shade = np.clip(n @ light, 0, 1) * 0.75 + 0.25
    xs, ys = tri[:, :, 0], -tri[:, :, 2]
    pad = 40
    sc = (size - 2 * pad) / max(xs.max() - xs.min(), ys.max() - ys.min())
    ox, oy = pad - xs.min() * sc, pad - ys.min() * sc
    img = Image.new("RGB", (int((xs.max()-xs.min())*sc+2*pad), int((ys.max()-ys.min())*sc+2*pad)), (245, 245, 245))
    d = ImageDraw.Draw(img)
    for i in order:
        col = tuple(int(c * shade[i]) for c in (90, 150, 230))
        pts = [(xs[i, k] * sc + ox, ys[i, k] * sc + oy) for k in range(3)]
        d.polygon(pts, fill=col, outline=col)
    if title: d.text((10, 10), title, fill=(0, 0, 0))
    img.save(out)

here = os.path.dirname(os.path.abspath(__file__))
prev = os.path.join(here, "previews"); os.makedirs(prev, exist_ok=True)
src = os.path.join(here, "stl")
for f in sorted(os.listdir(src)):
    if not f.endswith(".stl"): continue
    m = trimesh.load(os.path.join(src, f), force="mesh")
    bb = m.bounds
    print(f"{f:34s} watertight={m.is_watertight} vol={m.volume/1000:6.1f}cm3 bbox={np.round(bb[1]-bb[0],1)} faces={len(m.faces)}")
    name = f[:-4]
    render(m, os.path.join(prev, name + "_iso.png"), az=35, el=35, title=name)
    render(m, os.path.join(prev, name + "_top.png"), az=0, el=89, title=name + " (top, looking at the wall)")
    render(m, os.path.join(prev, name + "_under.png"), az=35, el=-60, title=name + " (wall side)")
