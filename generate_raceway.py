"""
Snap-on wall cable raceway for a 5 x Cat6 bundle.  Parametric build123d 0.11 generator.

Two-piece design (like commercial PVC raceway): a base that screws / tapes to the wall and a cover that
snaps over it.  The cover legs wrap OUTSIDE the base walls, so the visible surface is one clean piece and
the long, full-height legs are what flex during snap-on.

    outer size          32 wide x 20 tall (from the wall)
    interior            25.9 wide x 17.6 tall  -> 5 Cat6 stacked 3+2 with room, even 7 mm thick-jacket cable
    snap (rev 2)        0.75 mm ridges on both parts with HOOKED retention faces (20 deg undercut) and a
                        0.10 mm lateral preload: the legs are sprung against the base when seated and the hook
                        turns that spring force into a pull toward the wall, so the cover sits tight with no
                        rattle (rev 1 had 0.15 lateral / 0.2 vertical clearance and flat faces -> felt loose).
                        Snap-on deflection 0.85 mm, resting preload deflection ~0.24 mm (0.2 % strain: no creep).
    cover               1.2 top, 1.2 legs, 0.8 mm chamfer on the top edges
    base                1.2 floor with 2.0 mm pads at the countersunk #6 / M3.5 screw holes (every 100 mm),
                        1.2 walls 10 tall, floor lightening windows between the screw pads (FLOOR_WINDOWS)
    filament (rev 2)    ~39 % less than rev 1 (thinner sheets, shorter base walls, windowed floor, hollow caps)

Pieces (raceway frame: X across the width, Y along the run, Z = away from the wall, Z=0 is the wall):
    straight_base_300 / straight_cover_300      the run (print as many as needed)
    straight_base_150                           half-length base so cover joints never sit on base joints
    elbow_flat_base / elbow_flat_cover          90 deg bend within the SAME wall (e.g. baseboard run turning up)
    corner_inside_cover  + corner_inside_base_stub x2      run goes around an inside (concave) room corner
    corner_outside_cover + corner_outside_base_stub x2     run goes around an outside (convex) corner
    end_cap                                     plugs the open end of a run
Corner base stubs are separate on purpose: each is screwed to its own wall; only the cover needs to be one piece.

Run:  <AI_Image_Generator venv python> generate_raceway.py      -> stl/*.stl in print orientation
"""
import math, os
from build123d import *

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl")

# ------------------------------------------------------------------ profile (mm)
W  = 32.0      # outer width
H  = 20.0      # outer height from the wall
CT = 1.2       # cover top thickness
CL = 1.2       # cover leg thickness
CH = 0.8       # cover top-edge chamfer
BF = 1.2       # base floor thickness
BW = 1.2       # base wall thickness
BH = 10.0      # base wall height
PAD_T, PAD_D = 2.0, 13.0   # thicker floor pad under each screw head (countersink needs the depth)
BUMP    = 0.75  # bump protrusion (both bumps)
PRELOAD = 0.10  # each leg is sprung outward this much when seated (bump tips sit this far inside their mating faces)
HOOK    = 20.0  # retention-face undercut angle (deg from horizontal); the hook pulls the seated cover to the wall
VERT    = -0.05 # vertical interference of the two retention faces when seated (negative = slight interference,
                #  it costs |VERT|/tan(HOOK) extra leg deflection and guarantees the hook is loaded, not rattling)
RAMP    = 0.85  # rise of each snap-on ramp over the bump depth (~48 deg -> easy press-on)
FLOOR_WINDOWS = True   # lightening windows in the base floor (leaves 4.5 mm rails + 10 mm ribs / screw pads)
RAIL, RIB, WIN_MAX = 4.5, 10.0, 45.0

SCREW_D, CSK_D = 4.0, 7.0    # #6 / M3.5 clearance, 90 deg countersink on the inside face of the floor

STRAIGHT = 300.0
HALF = 150.0
ELBOW_COVER_ARM, ELBOW_BASE_ARM = 70.0, 55.0     # measured along the run from the mitre origin
CORNER_COVER_ARM, CORNER_STUB_ARM = 70.0, 60.0   # measured from the wall-corner line

CAP_T, CAP_PLUG, CAP_WALL, CAP_CLR = 1.2, 8.0, 1.2, 0.10


def derive(preload=None, vert=None):
    """(Re)compute the derived profile numbers.  check_mechanism.py calls derive(0, 0) to get the 'relaxed'
    geometry (= the legs after they have splayed by PRELOAD), where the classic no-intersection checks apply."""
    global HW, LEG_IN, GAP, BASE_OUT, BASE_IN, INTERIOR_W, INTERIOR_H, ENGAGE
    global C_ROOT_Z, C_TIP_Z, C_RAMP_Z0, B_ROOT_Z, B_TIP_Z, B_RAMP_Z1, HOOK_RISE
    p = PRELOAD if preload is None else preload
    v = VERT if vert is None else vert
    HW = W / 2                              # 16.0
    LEG_IN = HW - CL                        # 14.8  cover leg inner face
    GAP = BUMP - p                          # 0.65  leg inner face to base wall outer face (free state)
    BASE_OUT = LEG_IN - GAP                 # 14.15 base wall outer face
    BASE_IN = BASE_OUT - BW                 # 12.95
    INTERIOR_W, INTERIOR_H = 2 * BASE_IN, (H - CT) - BF
    ENGAGE = 2 * BUMP - GAP                 # bump overlap once snapped = snap-on leg deflection from free (0.85)
    HOOK_RISE = BUMP * math.tan(math.radians(HOOK))
    # cover bump: ramp up the leg to the tip, then the hooked retention face back to the leg (root higher than tip)
    C_ROOT_Z = 4.0
    C_TIP_Z = C_ROOT_Z - HOOK_RISE
    C_RAMP_Z0 = C_TIP_Z - RAMP
    # base bump: retention face parallel to the cover's, VERT above it when seated; then the ramp back to the wall
    B_ROOT_Z = C_ROOT_Z - GAP * math.tan(math.radians(HOOK)) + v
    B_TIP_Z = B_ROOT_Z + HOOK_RISE
    B_RAMP_Z1 = B_TIP_Z + RAMP


derive()


def cover_pts():
    r = [(HW, 0), (HW, H - CH), (HW - CH, H)]
    l = [(-x, z) for x, z in reversed(r)]
    right_in = [(LEG_IN, H - CT), (LEG_IN, C_ROOT_Z), (LEG_IN - BUMP, C_TIP_Z), (LEG_IN, C_RAMP_Z0), (LEG_IN, 0)]
    left_in = [(-x, z) for x, z in reversed(right_in)]
    return r + l + left_in + right_in


def base_pts():
    right = [(BASE_OUT, 0), (BASE_OUT, B_ROOT_Z), (BASE_OUT + BUMP, B_TIP_Z), (BASE_OUT, B_RAMP_Z1),
             (BASE_OUT, BH - 0.5), (BASE_OUT - 0.5, BH),            # chamfered top outer corner = cover lead-in
             (BASE_IN, BH), (BASE_IN, BF)]
    left = [(-x, z) for x, z in reversed(right)]
    return right + left


def prism(pts, y0, y1):
    """Extrude an (x, z) profile along Y from y0 to y1 (Z up = away from the wall)."""
    face = Polygon(*pts, align=None)
    solid = extrude(face, amount=y1 - y0)            # profile in XY, length along +Z
    solid = Pos(0, y1, 0) * (Rot(90, 0, 0) * solid)  # (x, y, z) -> (x, -z, y): height -> Z, length -> -Y, then shift
    bb = solid.bounding_box()
    assert abs(bb.min.Y - y0) < 1e-6 and abs(bb.max.Y - y1) < 1e-6 and bb.min.Z > -1e-6, bb
    return solid


def screw_holes(solid, ys, xs=(0.0,)):
    """Thickened pad + countersunk through hole at each (x, y) on the floor."""
    csk_h = (CSK_D - SCREW_D) / 2
    for y in ys:
        for x in xs:
            pad = Pos(x, y, 0) * Cylinder(PAD_D / 2, PAD_T, align=(Align.CENTER, Align.CENTER, Align.MIN))   # dia 13 < floor 25.9
            solid = solid + pad
            thru = Pos(x, y, -1) * Cylinder(SCREW_D / 2, PAD_T + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
            csk = Pos(x, y, PAD_T - csk_h) * Cone(SCREW_D / 2, CSK_D / 2, csk_h, align=(Align.CENTER, Align.CENTER, Align.MIN))
            top = Pos(x, y, PAD_T - 0.01) * Cylinder(CSK_D / 2, 3, align=(Align.CENTER, Align.CENTER, Align.MIN))
            solid = solid - thru - csk - top
    return solid


def window_spans(y0, y1, screw_ys, m0=RIB, m1=RIB):
    """Floor windows along Y between solid bands: [y0, y0+m0], [y1-m1, y1] and RIB-wide bands around each screw."""
    solid = [(y0, y0 + m0), (y1 - m1, y1)] + [(y - RIB, y + RIB) for y in screw_ys]
    solid.sort()
    spans = []
    for (a0, a1), (b0, b1) in zip(solid, solid[1:]):
        s = b0 - a1
        if s < 12:
            continue
        n = max(1, math.ceil((s + RIB) / (WIN_MAX + RIB)))
        wl = (s - (n - 1) * RIB) / n
        if wl < 12:
            continue
        spans += [(a1 + i * (wl + RIB), a1 + i * (wl + RIB) + wl) for i in range(n)]
    return spans


def floor_windows(solid, spans):
    if not FLOOR_WINDOWS:
        return solid
    w = INTERIOR_W - 2 * RAIL
    for a, b in spans:
        solid = solid - Pos(0, a, -1) * Box(w, b - a, BF + 2, align=(Align.CENTER, Align.MIN, Align.MIN))
    return solid


def _plane(normal):
    n = Vector(*normal).normalized()
    x_dir = Vector(1, 0, 0) if abs(n.X) < 0.9 else Vector(0, 1, 0)
    x_dir = (x_dir - n * x_dir.dot(n)).normalized()
    return Plane(origin=(0, 0, 0), x_dir=x_dir, z_dir=n)


def keep_side(solid, normal):
    """Keep the half of `solid` on the side of the plane through the origin that `normal` points to."""
    return split(solid, bisect_by=_plane(normal), keep=Keep.TOP)


def mirror_plane(solid, normal):
    return mirror(solid, about=_plane(normal))


# ------------------------------------------------------------------ straights
def straight_cover(L=STRAIGHT):
    return prism(cover_pts(), 0, L)


def straight_base(L=STRAIGHT):
    n = max(int(L // 100), 1)
    ys = [L / 2 + (i - (n - 1) / 2) * 100 for i in range(n)]
    b = floor_windows(prism(base_pts(), 0, L), window_spans(0, L, ys))
    return screw_holes(b, ys)


# ------------------------------------------------------------------ flat elbow (bend in the wall plane, about Z)
def _flat_elbow(pts, arm, windows=()):
    a = prism(pts, -HW, arm)                # arm along +Y; the mitre plane is y = x (inner corner at +x)
    a = floor_windows(a, windows)
    a = keep_side(a, (-1, 1, 0))            # keep y >= x
    b = mirror_plane(a, (1, -1, 0))         # swap x <-> y: the arm along +X
    return a + b


def elbow_flat_cover():
    return _flat_elbow(cover_pts(), ELBOW_COVER_ARM)


def elbow_flat_base():
    e = _flat_elbow(base_pts(), ELBOW_BASE_ARM, window_spans(HW + 2, ELBOW_BASE_ARM, [40.0], m0=0))
    e = screw_holes(e, [40.0], xs=(0.0,))
    e = screw_holes(e, [0.0], xs=(40.0,))
    return e


# ------------------------------------------------------------------ room corners (bend about X)
# inside corner: room is the quadrant y>0, z>0; arm A on wall z=0 (along +Y), arm B on wall y=0 (along +Z)
def corner_inside_cover():
    a = keep_side(prism(cover_pts(), 0, CORNER_COVER_ARM), (0, 1, -1))    # keep y >= z
    return a + mirror_plane(a, (0, 1, -1))


def corner_inside_base_stub():
    s = floor_windows(prism(base_pts(), 0, CORNER_STUB_ARM), window_spans(0, CORNER_STUB_ARM, [40.0]))
    return screw_holes(keep_side(s, (0, 1, -1)), [40.0])


# outside corner: wall solid is the quadrant y>0, z<0; arm A on top of it (along +Y), arm B in front (along -Z)
def corner_outside_cover():
    a = keep_side(prism(cover_pts(), -H, CORNER_COVER_ARM), (0, 1, 1))    # keep y >= -z
    return a + mirror_plane(a, (0, 1, 1))


def corner_outside_base_stub():
    s = floor_windows(prism(base_pts(), -H, CORNER_STUB_ARM), window_spans(0, CORNER_STUB_ARM, [40.0]))
    return screw_holes(keep_side(s, (0, 1, 1)), [40.0])


# ------------------------------------------------------------------ end cap (raceway frame: face at y in [-CAP_T, 0], plug into +Y)
def end_cap():
    outline = cover_pts()[:6]                         # the cover's outer outline (with its top chamfers)
    face = prism(outline, -CAP_T, 0)
    face = chamfer(face.faces().sort_by(Axis.Y)[0].edges(), 0.5)          # soften the outside face
    plug_w, plug_h = INTERIOR_W - 2 * CAP_CLR, INTERIOR_H - 2 * CAP_CLR
    plug = Pos(0, 0, BF + CAP_CLR) * Box(plug_w, CAP_PLUG, plug_h, align=(Align.CENTER, Align.MIN, Align.MIN))
    plug = chamfer(plug.faces().sort_by(Axis.Y)[-1].edges(), 0.6)         # lead-in on the plug tip
    hollow = Pos(0, 0, BF + CAP_CLR + CAP_WALL) * Box(plug_w - 2 * CAP_WALL, CAP_PLUG + 1, plug_h - 2 * CAP_WALL,
                                                      align=(Align.CENTER, Align.MIN, Align.MIN))
    return face + plug - hollow                       # hollow tube plug, open toward the raceway


# ------------------------------------------------------------------ print orientation + export
def flip_cover(c):
    """Cover printed top-face down: rotate 180 deg about Y, then lift so the top sits on z=0."""
    return Pos(0, 0, H) * (Rot(0, 180, 0) * c)


def to_bed(part):
    bb = part.bounding_box()
    return Pos(0, 0, -bb.min.Z) * part


PARTS = {
    # name: (builder, print-orientation transform)
    "straight_base_300":        (straight_base, to_bed),
    "straight_cover_300":       (straight_cover, flip_cover),
    "straight_base_150":        (lambda: straight_base(HALF), to_bed),
    "elbow_flat_base":          (elbow_flat_base, to_bed),
    "elbow_flat_cover":         (elbow_flat_cover, flip_cover),
    "corner_inside_cover":      (corner_inside_cover, to_bed),                       # stands on arm A's leg edges, arm B vertical
    "corner_inside_base_stub":  (corner_inside_base_stub, to_bed),
    "corner_outside_cover":     (corner_outside_cover, lambda c: to_bed(flip_cover(c))),   # arm A top down, arm B vertical
    "corner_outside_base_stub": (corner_outside_base_stub, to_bed),
    "end_cap":                  (end_cap, lambda c: to_bed(Rot(90, 0, 0) * c)),             # face down on the bed, hollow plug up
}


def export(name, part):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name + ".stl")
    export_stl(part, path, tolerance=0.02, angular_tolerance=0.1)
    bb = part.bounding_box()
    print(f"{name:28s} {bb.size.X:6.1f} x {bb.size.Y:6.1f} x {bb.size.Z:5.1f} mm   {part.volume/1000:6.1f} cm3  minZ={bb.min.Z:.3f}")


if __name__ == "__main__":
    print(f"interior {INTERIOR_W:.1f} x {INTERIOR_H:.1f} mm, snap engagement {ENGAGE:.2f} mm, preload {PRELOAD:.2f}, "
          f"base wall outer x={BASE_OUT}")
    for name, (build, orient) in PARTS.items():
        export(name, orient(build()))
