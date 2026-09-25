"""
Wall entry plate + drywall backing for the Cat6 raceway: takes the run straight into the wall cavity.

The raceway arrives at the plate, the cables ride up a ramp and drop through a hole in the plate face, through a
sleeve that lines the cut drywall edge, and into the stud bay.  The plate looks like a standard single-gang wall
plate with the raceway crossing it, and the full raceway profile (snap ridges included) is integral to the
plate, so a normal cover snaps straight over the joint with no step.

Frame (same convention as generate_raceway): Z = away from the wall, Z=0 is the drywall FACE, the cavity is Z<0.
X across the plate, Y up the plate.

    plate           69.85 x 114.3 (2-3/4 x 4-1/2 in, standard single gang) x 2.4 thick, r6 corners
    drywall cutout  54.8 x 92.1 (2-5/32 x 3-5/8 in -- the Arlington LV1 low-voltage bracket cutout, so a
                    store-bought LV bracket or brush plate fits the same hole if this plate is ever replaced)
    fixing          two M3 x 30 countersunk screws at (0, +/-52.5) through the plate and the drywall into two
                    printed backing bars in the cavity: the board is clamped between plate and bars, so it holds
                    mid-bay with no stud and no anchors.  Fits 1/2 in (12.7) and 5/8 in (15.9) board.
    cable path      25 x 44 mm hole, a 14 mm ramp up to a 45 deg lead-in lip on each run-direction edge.  The lip
                    is a bearing surface, not the bend radius: Cat6's 25 mm static min bend radius is made up
                    over the 44 mm hole and in the bay, which is why the hole is long and the sleeve flares.
    stub            full-height base profile across the plate, at the same ABSOLUTE snap-ridge heights as
                    straight_base, so straight_cover / end_cap / the elbows all mate with it.  Its floor is the
                    2.4 mm plate instead of the 1.2 mm base floor, so the interior is 16.4 mm instead of 17.6.

Parts:
    wallplate_entry_bottom  run arrives along the plate's long axis (vertical run, e.g. up from a baseboard)
    wallplate_entry_side    run arrives along the short axis (horizontal run); flip top-to-bottom for L or R
    wallplate_cover_bottom  matched cover, one closed end, so the run can terminate at the plate with no hacksaw
    wallplate_cover_side    same for the side-entry plate
    wall_sleeve             lines the cut drywall edge; front lip captured in a groove in the plate's back
    wall_backing_bar        x2, cavity side; hooks over the sleeve's protruding wall so it hangs hands-free
    wall_cut_template       trace/drill template: cutout window, both screw holes, raceway-width marks

Run:  <AI_Image_Generator venv python> generate_wallplate.py    -> stl/*.stl in print orientation
"""
import os
from build123d import *
import generate_raceway as g

OUT = g.OUT

# ------------------------------------------------------------------ plate
PLATE_W, PLATE_H = 69.85, 114.3     # 2-3/4 x 4-1/2 in, standard single gang
PLATE_T = 2.4                       # plate face = the stub's floor
PLATE_R = 6.0                       # corner radius
PLATE_CH = 0.6                      # chamfer on the visible front edge

CUT_W, CUT_H = 54.8, 92.1           # drywall cutout (Arlington LV1)

HOLE_ACROSS, HOLE_ALONG = 25.0, 44.0    # cable hole: across the run x along the run
RAMP_L, RAMP_H = 14.0, 2.0              # ramp up to the hole lip on each run-direction edge (keeps 14.4 mm
                                        # clear over the crest, so all 5 cables can also pass straight through)
LIP_CH = 1.4                            # 45 deg lead-in at the crest, where the cable turns into the wall

CS_OFF = 52.5       # clamp screws, from plate centre along the long axis
CS_D = 3.4          # M3 clearance
CS_HEAD = 6.4       # M3 countersunk head + clearance
CS_CSK = 1.5        # countersink depth (leaves 0.9 mm of plate under the head)

# ------------------------------------------------------------------ sleeve (drywall edge liner)
SL_CLR = 0.6        # total clearance in the cutout (0.3 per side)
SL_T = 1.6          # sleeve wall
SL_D = 19.0         # depth into the cavity: protrudes >= 3 mm past 5/8 in board, so the backing
                    # bars hook over it at either board thickness
LIP_W, LIP_T = 3.0, 0.8             # front lip, captured by a groove in the plate's back
LIP_OVER = 0.2                      # how far the lip laps onto the wall's front edge (a coincident face here
                                    # makes the union non-manifold, so the overlap is deliberate)
GR_CLR_W, GR_CLR_T = 0.4, 0.15      # groove clearance around the lip

# ------------------------------------------------------------------ backing bar (cavity side)
BAR_L, BAR_H, BAR_T = 50.0, 14.0, 4.0
BAR_RIB = 2.0       # how far the hook ribs reach forward past the drywall's back face
BAR_RIB_T = 1.6
NUT_AF, NUT_T = 5.7, 2.6            # M3 hex nut across flats + thickness, pocket
NUT_BUMP = 0.3                      # retention pips so the nut stays put during install

TPL_T = 1.6         # cut template sheet
TPL_MARGIN = 20.0

SL_OUT_W, SL_OUT_H = CUT_W - SL_CLR, CUT_H - SL_CLR         # 54.2 x 91.5
DRYWALL = {"1/2 in": 12.7, "5/8 in": 15.9}                  # board thicknesses the bars must handle
INT_W, INT_H = 2 * g.BASE_IN, (g.H - g.CT) - PLATE_T        # stub interior over the plate


def stub_pts(floor_t=PLATE_T):
    """generate_raceway.base_pts() with a thicker floor: identical outer profile and absolute ridge heights."""
    old = g.BF
    g.BF = floor_t
    try:
        return g.base_pts()
    finally:
        g.BF = old


def prism_x(pts, x0, x1):
    """Extrude a (y, z) profile along X from x0 to x1."""
    face = Polygon(*pts, align=None)
    solid = extrude(face, amount=x1 - x0)               # profile in XY (as y,z), length along +Z
    solid = Pos(x1, 0, 0) * (Rot(0, 90, 0) * (Rot(0, 0, 90) * solid))   # (x,y,z)_face -> (-z, x, y)
    bb = solid.bounding_box()
    assert abs(bb.min.X - x0) < 1e-6 and abs(bb.max.X - x1) < 1e-6, bb
    return solid


def slab():
    """The visible plate: rounded rectangle, PLATE_T thick, front edge chamfered."""
    s = extrude(RectangleRounded(PLATE_W, PLATE_H, PLATE_R), amount=PLATE_T)
    return chamfer(s.faces().sort_by(Axis.Z)[-1].edges(), PLATE_CH)


def stub_half(L):
    """The stub stops CT short of the far plate edge so the matched cover's closed end wall lands on the plate
    face there instead of on top of the stub walls."""
    return L / 2 - g.CT


def ramp_len(L):
    """RAMP_L, shortened if the run is too short for it: the ramp must land back on the plate floor at least
    1 mm before the stub's end, or the adjoining base would butt against a step instead of the floor."""
    return min(RAMP_L, stub_half(L) - HOLE_ALONG / 2 - 1.0)


def ramps(L):
    """A ramp on each run-direction edge of the hole, full stub width, rising RAMP_H over ramp_len to the lip."""
    y0, y1 = HOLE_ALONG / 2, HOLE_ALONG / 2 + ramp_len(L)
    tri = [(y0, PLATE_T), (y0, PLATE_T + RAMP_H), (y1, PLATE_T)]
    up = prism_x(tri, -g.BASE_IN, g.BASE_IN)      # full stub width; re-read in case derive() changed
    return up + mirror(up, about=Plane.XZ)


def cable_hole():
    """Through hole, a 45 deg lead-in at the ramp crest, and a flare on the cavity side."""
    top = PLATE_T + RAMP_H
    thru = Pos(0, 0, -1) * Box(HOLE_ACROSS, HOLE_ALONG, top + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    lead = loft([Plane.XY.offset(top - LIP_CH) * Rectangle(HOLE_ACROSS, HOLE_ALONG),
                 Plane.XY.offset(top) * Rectangle(HOLE_ACROSS + 2 * LIP_CH, HOLE_ALONG + 2 * LIP_CH)])
    f = 0.9
    flare = loft([Plane.XY.offset(f) * Rectangle(HOLE_ACROSS, HOLE_ALONG),
                  Plane.XY * Rectangle(HOLE_ACROSS + 2 * f, HOLE_ALONG + 2 * f)])
    return thru + lead + flare


def lip_groove():
    """Groove in the plate's back that captures the sleeve's front lip."""
    o_w, o_h = SL_OUT_W + 2 * LIP_W + GR_CLR_W, SL_OUT_H + 2 * LIP_W + GR_CLR_W   # clearance outboard only:
    i_w, i_h = SL_OUT_W - 2 * LIP_OVER, SL_OUT_H - 2 * LIP_OVER   # inboard: level with the lip, over the
    #                                          sleeve's own wall, so no cut gypsum is ever left uncovered
    d = LIP_T + GR_CLR_T
    return extrude(Rectangle(o_w, o_h), amount=d) - extrude(Rectangle(i_w, i_h), amount=d)


def clamp_screws(top=PLATE_T):
    """Two countersunk M3 holes on the plate's long axis, outside the cutout, into the backing bars."""
    parts = []
    for s in (+1, -1):
        y = s * CS_OFF
        parts.append(Pos(0, y, -1) * Cylinder(CS_D / 2, top + 2, align=(Align.CENTER, Align.CENTER, Align.MIN)))
        parts.append(Pos(0, y, top - CS_CSK) * Cone(CS_D / 2, CS_HEAD / 2, CS_CSK,
                                                    align=(Align.CENTER, Align.CENTER, Align.MIN)))
        parts.append(Pos(0, y, top - 0.01) * Cylinder(CS_HEAD / 2, 4, align=(Align.CENTER, Align.CENTER, Align.MIN)))
    out = parts[0]
    for p in parts[1:]:
        out += p
    return out


def wallplate_entry(along_x=False):
    """along_x=False: the run crosses the plate vertically (bottom entry).  True: horizontally (side entry)."""
    L = PLATE_W if along_x else PLATE_H
    run = g.prism(stub_pts(), -L / 2, stub_half(L)) + ramps(L)
    run = run & (Pos(0, 0, -1) * Box(g.W, L, g.H + 2, align=(Align.CENTER, Align.CENTER, Align.MIN)))  # clip ramps
    hole = cable_hole()
    if along_x:
        run, hole = Rot(0, 0, 90) * run, Rot(0, 0, 90) * hole
    # the hole is cut LAST, from the finished union: cutting it from the channel alone and then adding the
    # face slab would fill it straight back in (that bug shipped in the first draft of this file)
    return slab() + run - hole - lip_groove() - clamp_screws()


def wallplate_cover(along_x=False):
    """Straight cover, plate length + one closed end wall, so the run can terminate at the plate.

    The legs are trimmed to land on the plate's 2.4 mm face instead of the wall: a full-length cover's legs
    reach z=0 and would foul the plate, holding the cover off its snap ridges.  The trim is below the snap
    ramp (C_RAMP_Z0), so the snap itself is untouched and the cover top stays at the same z as the whole run."""
    L = PLATE_W if along_x else PLATE_H
    body = g.prism(g.cover_pts(), 0, L - g.CT)
    end = g.prism(g.cover_pts()[:6], L - g.CT, L)     # closed end at the FAR end: the run arrives at y=0
    assert PLATE_T < g.C_RAMP_Z0, f"leg trim {PLATE_T} would eat into the snap ramp at {g.C_RAMP_Z0:.2f}"
    trim = Pos(0, 0, -1) * Box(g.W + 2, L + 2, PLATE_T + 1, align=(Align.CENTER, Align.MIN, Align.MIN))
    return (body + end) - trim


def wall_sleeve():
    body = extrude(Rectangle(SL_OUT_W, SL_OUT_H), amount=-SL_D)
    bore = Pos(0, 0, 1) * extrude(Rectangle(SL_OUT_W - 2 * SL_T, SL_OUT_H - 2 * SL_T), amount=-SL_D - 2)
    # lip: an annulus OUTBOARD of the wall, in front of the board face (z 0..LIP_T), received by the plate's
    # groove.  The wall's own front edge stays at z=0, flush with the board, so the plate beds down on it.
    lip = extrude(Rectangle(SL_OUT_W + 2 * LIP_W, SL_OUT_H + 2 * LIP_W), amount=LIP_T) -         extrude(Rectangle(SL_OUT_W - 2 * LIP_OVER, SL_OUT_H - 2 * LIP_OVER), amount=LIP_T)
    f = 1.0                                                      # flare the cavity end so it can't catch a jacket
    bw, bh = SL_OUT_W - 2 * SL_T, SL_OUT_H - 2 * SL_T
    flare = loft([Plane.XY.offset(-SL_D + f) * Rectangle(bw, bh),
                  Plane.XY.offset(-SL_D) * Rectangle(bw + 2 * f, bh + 2 * f)])
    return (body + lip) - bore - flare


def wall_backing_bar():
    """Cavity-side clamp bar, built at the +Y screw position.  Hooks over the sleeve's protruding wall (so it
    keyed against rotation, and stopped from sliding away from the cutout, by one rib that reaches forward
    into the sleeve's bore.  There is no room for a second rib on the gypsum side -- the sleeve fills the
    cutout to within 0.3 mm -- so the bar is carried during install by its screw, which is threaded a few
    turns into the captive nut BEFORE the bar goes through the hole.

    Built in INSTALLED convention for a wall of thickness 0: the bar's front face (against the board's back) is
    z=0, the body is behind it at z<0, the hook ribs reach forward to z=+BAR_RIB.  Installed at board thickness
    t, the bar is at Pos(0, 0, -t).  The nut pocket opens on the cavity face so the screw pulls the bar forward."""
    y0 = CUT_H / 2                                    # cut drywall edge = bar's front lower corner
    si = SL_OUT_H / 2 - SL_T                          # sleeve wall inner face
    b = Pos(0, y0, 0) * Box(BAR_L, BAR_H, BAR_T, align=(Align.CENTER, Align.MIN, Align.MAX))
    b += Pos(0, si - 0.2, 0) * Box(BAR_L * 0.6, BAR_RIB_T, BAR_RIB, align=(Align.CENTER, Align.MAX, Align.MIN))
    pocket = Pos(0, CS_OFF, -BAR_T - 1) * extrude(RegularPolygon(NUT_AF / 2, 6, major_radius=False),
                                                  amount=NUT_T + 1)
    b = b - pocket
    b = b - Pos(0, CS_OFF, -BAR_T - 1) * Cylinder(CS_D / 2, BAR_T + 2 + BAR_RIB,
                                                  align=(Align.CENTER, Align.CENTER, Align.MIN))
    for k in range(3):                                # three pips that pinch the nut's flats
        pip = Rot(0, 0, 60 * k) * Pos(NUT_AF / 2 - NUT_BUMP / 3, 0, 0) * \
            Cylinder(NUT_BUMP, NUT_T - 0.8, align=(Align.CENTER, Align.CENTER, Align.MIN))
        b += Pos(0, CS_OFF, -BAR_T + 0.4) * pip
    return b


def wall_cut_template():
    """Sheet you hold on the wall: trace the window, punch the two screw holes, line the slots up with the run."""
    sheet = extrude(RectangleRounded(PLATE_W + 2 * TPL_MARGIN, PLATE_H + 2 * TPL_MARGIN, 4), amount=TPL_T)
    sheet -= extrude(Rectangle(CUT_W, CUT_H), amount=TPL_T)
    band = extrude(Rectangle(CUT_W + 26, CUT_H + 26), amount=TPL_T)      # keep marks outside this, near the edge
    for s in (+1, -1):
        sheet -= Pos(0, s * CS_OFF, 0) * Cylinder(CS_D / 2, TPL_T, align=(Align.CENTER, Align.CENTER, Align.MIN))
        mark = Pos(s * g.HW, 0, 0) * Box(1.6, PLATE_H + 2 * TPL_MARGIN, TPL_T,
                                         align=(Align.CENTER, Align.CENTER, Align.MIN))
        sheet -= (mark - band)
    sheet -= Pos(0, (PLATE_H + 2 * TPL_MARGIN) / 2, 0) * Box(3, 12, TPL_T, align=(Align.CENTER, Align.MAX, Align.MIN))
    return sheet


# ------------------------------------------------------------------ print orientation + export
def plate_to_bed(p):
    """Plate back-face down: the stub, ramps and lip all print upward, support-free."""
    return p


def sleeve_to_bed(s):
    """Sleeve lip-down on the bed, tube standing up: the lip is the bed contact, nothing overhangs."""
    return g.to_bed(Rot(180, 0, 0) * s)


PARTS = {
    "wallplate_entry_bottom": (lambda: wallplate_entry(False), plate_to_bed),
    "wallplate_entry_side":   (lambda: wallplate_entry(True), plate_to_bed),
    "wallplate_cover_bottom": (lambda: wallplate_cover(False), g.flip_cover),
    "wallplate_cover_side":   (lambda: wallplate_cover(True), g.flip_cover),
    "wall_sleeve":            (wall_sleeve, sleeve_to_bed),
    "wall_backing_bar":       (wall_backing_bar, lambda b: g.to_bed(Pos(0, -CUT_H / 2, 0) * b)),
    "wall_cut_template":      (wall_cut_template, lambda t: t),
}

if __name__ == "__main__":
    print(f"plate {PLATE_W} x {PLATE_H} x {PLATE_T}, cutout {CUT_W} x {CUT_H}, "
          f"stub interior {INT_W:.1f} x {INT_H:.1f} mm, hole {HOLE_ACROSS} x {HOLE_ALONG}")
    for name, (build, orient) in PARTS.items():
        g.export(name, orient(build()))
