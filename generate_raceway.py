"""
Snap-on wall cable raceway for a 5 x Cat6 bundle.  Parametric build123d 0.11 generator.

Two-piece design (like commercial PVC raceway): a base that screws / tapes to the wall and a cover that
snaps over it.  The cover legs wrap OUTSIDE the base walls, so the visible surface is one clean piece and
the long, full-height legs are what flex during snap-on.

    outer size          32 wide x 20 tall (from the wall)
    interior            23.8 wide x 16.4 tall  -> 5 Cat6 stacked 3+2 with room, even 7 mm thick-jacket cable
    snap                two 0.75 mm ramped bumps (base wall outward, cover leg inward), 0.6 mm engagement,
                        0.15 mm lateral / 0.2 mm vertical clearance, flat retention faces
    cover               1.6 top, 1.6 legs, 1 mm chamfer on the top edges
    base                2.0 floor, 1.6 walls 12 tall, countersunk #6 / M3.5 screw holes every 100 mm

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
import os
from build123d import *

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl")

# ------------------------------------------------------------------ profile (mm)
W  = 32.0      # outer width
H  = 20.0      # outer height from the wall
CT = 1.6       # cover top thickness
CL = 1.6       # cover leg thickness
CH = 1.0       # cover top-edge chamfer
BF = 2.0       # base floor thickness
BW = 1.6       # base wall thickness
BH = 12.0      # base wall height
BUMP  = 0.75   # bump protrusion (both bumps)
ENGAGE = 0.60  # how far the bumps overlap once snapped (= leg deflection during snap-on)
LAT   = 0.15   # lateral clearance bump-to-surface
VERT  = 0.20   # vertical clearance between the two retention faces

HW   = W / 2                          # 16.0
LEG_IN = HW - CL                      # 14.4  cover leg inner face
BASE_OUT = LEG_IN - (ENGAGE + 2 * LAT)  # 13.5  base wall outer face
BASE_IN  = BASE_OUT - BW              # 11.9
C_BUMP_Z0, C_BUMP_Z1 = 2.2, 3.9       # cover bump: ramp start, retention face (top)
B_BUMP_Z0 = C_BUMP_Z1 + VERT          # 4.1 base bump retention face (bottom)
B_BUMP_Z1 = B_BUMP_Z0 + 1.9           # 6.0 ramp end
INTERIOR_W, INTERIOR_H = 2 * BASE_IN, (H - CT) - BF

SCREW_D, CSK_D = 4.0, 7.0    # #6 / M3.5 clearance, 90 deg countersink on the inside face of the floor

STRAIGHT = 300.0
HALF = 150.0
ELBOW_COVER_ARM, ELBOW_BASE_ARM = 70.0, 55.0     # measured along the run from the mitre origin
CORNER_COVER_ARM, CORNER_STUB_ARM = 70.0, 60.0   # measured from the wall-corner line

CAP_T, CAP_PLUG = 1.6, 8.0


def cover_pts():
    r = [(HW, 0), (HW, H - CH), (HW - CH, H)]
    l = [(-x, z) for x, z in reversed(r)]
    inner = [(-LEG_IN, 0), (-LEG_IN, C_BUMP_Z0), (-(LEG_IN - BUMP), C_BUMP_Z1), (-LEG_IN, C_BUMP_Z1), (-LEG_IN, H - CT),
             (LEG_IN, H - CT), (LEG_IN, C_BUMP_Z1), (LEG_IN - BUMP, C_BUMP_Z1), (LEG_IN, C_BUMP_Z0), (LEG_IN, 0)]
    return r + l + inner


def base_pts():
    right = [(BASE_OUT, 0), (BASE_OUT, B_BUMP_Z0), (BASE_OUT + BUMP, B_BUMP_Z0), (BASE_OUT, B_BUMP_Z1),
             (BASE_OUT, BH), (BASE_IN, BH), (BASE_IN, BF)]
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
    csk_h = (CSK_D - SCREW_D) / 2
    for y in ys:
        for x in xs:
            thru = Pos(x, y, -1) * Cylinder(SCREW_D / 2, BF + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
            csk = Pos(x, y, BF - csk_h) * Cone(SCREW_D / 2, CSK_D / 2, csk_h, align=(Align.CENTER, Align.CENTER, Align.MIN))
            top = Pos(x, y, BF - 0.01) * Cylinder(CSK_D / 2, 3, align=(Align.CENTER, Align.CENTER, Align.MIN))
            solid = solid - thru - csk - top
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
    return screw_holes(prism(base_pts(), 0, L), ys)


# ------------------------------------------------------------------ flat elbow (bend in the wall plane, about Z)
def _flat_elbow(pts, arm):
    a = prism(pts, -HW, arm)                # arm along +Y; the mitre plane is y = x (inner corner at +x)
    a = keep_side(a, (-1, 1, 0))            # keep y >= x
    b = mirror_plane(a, (1, -1, 0))         # swap x <-> y: the arm along +X
    return a + b


def elbow_flat_cover():
    return _flat_elbow(cover_pts(), ELBOW_COVER_ARM)


def elbow_flat_base():
    e = _flat_elbow(base_pts(), ELBOW_BASE_ARM)
    e = screw_holes(e, [40.0], xs=(0.0,))
    e = screw_holes(e, [0.0], xs=(40.0,))
    return e


# ------------------------------------------------------------------ room corners (bend about X)
# inside corner: room is the quadrant y>0, z>0; arm A on wall z=0 (along +Y), arm B on wall y=0 (along +Z)
def corner_inside_cover():
    a = keep_side(prism(cover_pts(), 0, CORNER_COVER_ARM), (0, 1, -1))    # keep y >= z
    return a + mirror_plane(a, (0, 1, -1))


def corner_inside_base_stub():
    return screw_holes(keep_side(prism(base_pts(), 0, CORNER_STUB_ARM), (0, 1, -1)), [40.0])


# outside corner: wall solid is the quadrant y>0, z<0; arm A on top of it (along +Y), arm B in front (along -Z)
def corner_outside_cover():
    a = keep_side(prism(cover_pts(), -H, CORNER_COVER_ARM), (0, 1, 1))    # keep y >= -z
    return a + mirror_plane(a, (0, 1, 1))


def corner_outside_base_stub():
    return screw_holes(keep_side(prism(base_pts(), -H, CORNER_STUB_ARM), (0, 1, 1)), [40.0])


# ------------------------------------------------------------------ end cap (raceway frame: face at y in [-CAP_T, 0], plug into +Y)
def end_cap():
    outline = cover_pts()[:6]                         # the cover's outer outline (with its 1 mm top chamfers)
    face = prism(outline, -CAP_T, 0)
    face = chamfer(face.faces().sort_by(Axis.Y)[0].edges(), 0.5)          # soften the outside face
    plug_w = INTERIOR_W - 2 * LAT
    plug = Pos(0, 0, BF + LAT) * Box(plug_w, CAP_PLUG, INTERIOR_H - 2 * LAT, align=(Align.CENTER, Align.MIN, Align.MIN))
    plug = chamfer(plug.faces().sort_by(Axis.Y)[-1].edges(), 0.8)         # lead-in on the plug tip
    return face + plug


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
    "end_cap":                  (end_cap, lambda c: to_bed(Rot(-90, 0, 0) * c)),            # face down, plug up
}


def export(name, part):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name + ".stl")
    export_stl(part, path, tolerance=0.02, angular_tolerance=0.1)
    bb = part.bounding_box()
    print(f"{name:28s} {bb.size.X:6.1f} x {bb.size.Y:6.1f} x {bb.size.Z:5.1f} mm   {part.volume/1000:6.1f} cm3  minZ={bb.min.Z:.3f}")


if __name__ == "__main__":
    print(f"interior {INTERIOR_W:.1f} x {INTERIOR_H:.1f} mm, snap engagement {ENGAGE:.2f} mm, base wall outer x={BASE_OUT}")
    for name, (build, orient) in PARTS.items():
        export(name, orient(build()))
