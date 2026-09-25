"""Render the wall-entry assembly: an exploded view and a cut-away section through the cable path.

    <AI_Image_Generator venv python> render_wallentry.py   -> previews/wallentry_exploded.png, _section.png
"""
import math, os
import numpy as np, trimesh
from PIL import Image, ImageDraw
from build123d import *
import generate_raceway as g
import generate_wallplate as w
import check_wallplate as c

HERE = os.path.dirname(os.path.abspath(__file__))
PREV = os.path.join(HERE, "previews")
T = w.DRYWALL["5/8 in"]

COLORS = {
    "board": (208, 200, 188),
    "plate": (90, 150, 230),
    "cover": (120, 180, 245),
    "sleeve": (250, 180, 80),
    "bar": (230, 110, 110),
    "cable": (70, 180, 130),
}


def to_mesh(part):
    """build123d solid -> trimesh via a temp STL (keeps this script dependency-free)."""
    p = os.path.join(PREV, "_tmp.stl")
    export_stl(part, p, tolerance=0.03, angular_tolerance=0.2)
    m = trimesh.load(p, force="mesh")
    os.remove(p)
    return m


def render(items, out, az=35, el=25, size=1500, title="", elev_light=(-0.4, -0.7, 0.6)):
    """Painter's-algorithm render of [(mesh, colour), ...] in one shared frame."""
    a, e = math.radians(az), math.radians(el)
    Rz = np.array([[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, math.cos(e), -math.sin(e)], [0, math.sin(e), math.cos(e)]])
    R = Rx @ Rz
    light = np.array(elev_light, dtype=float)
    light /= np.linalg.norm(light)
    tris, cols, depth = [], [], []
    for m, col in items:
        v = m.vertices @ R.T
        t = v[m.faces]
        n = m.face_normals @ R.T
        shade = np.clip(n @ light, 0, 1) * 0.72 + 0.28
        tris.append(t)
        cols.append((np.array(col)[None, :] * shade[:, None]).astype(int))
        depth.append(t[:, :, 1].mean(axis=1))
    tris = np.concatenate(tris)
    cols = np.concatenate(cols)
    depth = np.concatenate(depth)
    xs, ys = tris[:, :, 0], -tris[:, :, 2]
    pad = 50
    sc = (size - 2 * pad) / max(xs.max() - xs.min(), ys.max() - ys.min())
    ox, oy = pad - xs.min() * sc, pad - ys.min() * sc
    img = Image.new("RGB", (int((xs.max() - xs.min()) * sc + 2 * pad),
                            int((ys.max() - ys.min()) * sc + 2 * pad)), (247, 247, 247))
    d = ImageDraw.Draw(img)
    for i in np.argsort(-depth):
        col = tuple(int(x) for x in cols[i])
        d.polygon([(xs[i, k] * sc + ox, ys[i, k] * sc + oy) for k in range(3)], fill=col, outline=col)
    if title:
        d.text((14, 12), title, fill=(20, 20, 20))
    img.save(out)
    print("wrote", out, img.size)


def board_piece():
    """A patch of 5/8 in drywall with the cutout and the two screw holes."""
    b = c.board(T) & Pos(0, 0, -T) * Box(150, 190, T, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for s in (+1, -1):
        b -= Pos(0, s * w.CS_OFF, -T - 1) * Cylinder(w.CS_D / 2, T + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return b


def cable_run():
    """One Cat6 (6.5 mm OD) coming up the raceway, over the ramp, through the hole and down the bay.  The turn
    is drawn on a ~25 mm radius: Cat6's static minimum (4 x OD), which is why the hole is 44 mm long."""
    R = 3.25
    pts = [(0, -70, 5.7), (0, -40, 5.7), (0, -28, 6.6), (0, -22, 7.7), (0, -14, 5.0),
           (0, -6, -2.0), (0, 2, -14.0), (0, 8, -28.0), (0, 10, -46.0), (0, 10, -62.0)]
    segs = [Pos(*pts[0]) * Sphere(R)]
    for p0, p1 in zip(pts, pts[1:]):
        v = Vector(*p1) - Vector(*p0)
        axis = Vector(0, 0, 1).cross(v)
        cosang = max(-1.0, min(1.0, v.Z / v.length))
        ang = math.degrees(math.acos(cosang))
        if axis.length > 1e-9:
            loc = Location(p0, tuple(axis.normalized()), ang)
        else:                                    # parallel to Z: 0 or 180 deg, cross product is degenerate
            loc = Location(p0, (1, 0, 0), 0 if v.Z > 0 else 180)
        segs.append(loc * Cylinder(R, v.length, align=(Align.CENTER, Align.CENTER, Align.MIN)))
        segs.append(Pos(*p1) * Sphere(R))
    out = segs[0]
    for seg in segs[1:]:
        out += seg
    return out


if __name__ == "__main__":
    os.makedirs(PREV, exist_ok=True)
    plate = w.wallplate_entry(False)
    cover = c.place_cover(False)
    sleeve = w.wall_sleeve()
    bars = [Pos(0, 0, -T) * w.wall_backing_bar(),
            Pos(0, 0, -T) * (Rot(0, 0, 180) * w.wall_backing_bar())]

    # ---- exploded: pull each part out along its assembly direction
    items = [(to_mesh(board_piece()), COLORS["board"]),
             (to_mesh(Pos(0, 0, -46) * sleeve), COLORS["sleeve"]),
             (to_mesh(Pos(0, 0, 16) * plate), COLORS["plate"]),
             (to_mesh(Pos(0, 0, 40) * cover), COLORS["cover"]),
             (to_mesh(Pos(0, 0, -78) * bars[0]), COLORS["bar"]),
             (to_mesh(Pos(0, 0, -78) * bars[1]), COLORS["bar"])]
    render(items, os.path.join(PREV, "wallentry_exploded.png"), az=38, el=22,
           title="wall entry, exploded: cover / plate / 5-8 in board / sleeve / 2 backing bars")

    # ---- section: cut everything at x=0 and look along +X to show the cable path
    half = Pos(0, 0, -200) * Box(200, 400, 400, align=(Align.MIN, Align.CENTER, Align.MIN))
    asm = [(board_piece(), "board"), (sleeve, "sleeve"), (plate, "plate"), (cover, "cover"),
           (bars[0], "bar"), (bars[1], "bar"), (cable_run(), "cable")]
    items = []
    for part, key in asm:
        cutp = part - half
        if cutp is not None and cutp.volume > 0.01:
            items.append((to_mesh(cutp), COLORS[key]))
    render(items, os.path.join(PREV, "wallentry_section.png"), az=-88, el=8,
           title="section on the run centreline: cable up the raceway, over the ramp, through the sleeve, into the bay")
