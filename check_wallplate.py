"""
Fit / mechanism checks for the wall entry plate + drywall backing, run BEFORE claiming anything fits.
Same rules as check_mechanism.py: every check is a solid boolean on the actual generated parts in the
assembled (wall) frame, and a "must be empty" intersection prints its volume.

    <AI_Image_Generator venv python> check_wallplate.py      (check_wallplate.log = last run)
"""
import math, os
import numpy as np, trimesh
from build123d import *
import generate_raceway as g
import generate_wallplate as w
import check_mechanism as cm

TOL = 0.05
report = cm.report
CTR = (Align.CENTER, Align.CENTER, Align.MIN)


def V(s):
    """Volume, tolerant of the empty compounds that a boolean can return."""
    try:
        return 0.0 if s is None else s.volume
    except Exception:
        return 0.0


def X(a, b):
    """Intersection volume."""
    return 0.0 if V(a) <= 0 or V(b) <= 0 else V(a & b)


def D(a, b):
    """Volume of a - b."""
    if V(a) <= 0:
        return 0.0
    return V(a) if V(b) <= 0 else V(a - b)


def big(z0, h=400.0):
    return Pos(0, 0, z0) * Box(400, 400, h, align=CTR)


def board(t):
    """A slab of drywall t thick, front face at z=0, with the cutout removed."""
    return (Pos(0, 0, -t) * Box(400, 400, t, align=CTR)) - \
           (Pos(0, 0, -t - 1) * Box(w.CUT_W, w.CUT_H, t + 2, align=CTR))


def place_cover(along_x):
    """The matched cover seated on its plate, in the wall frame."""
    L = w.PLATE_W if along_x else w.PLATE_H
    c = w.wallplate_cover(along_x)
    if along_x:
        return Pos(L / 2, 0, 0) * (Rot(0, 0, 90) * c)               # same rotation the plate's stub gets
    return Pos(0, -L / 2, 0) * c


def bundle(along_x, z0, length=None, offset=0.0):
    """5 x Cat6 as a 3+2 pack, 21 x 14, lying along the run above z0."""
    if length is None:
        length = (w.PLATE_W if along_x else w.PLATE_H) - 2 * g.CT      # the cover's closed end stops it
    b = Pos(0, offset, z0) * Box(21.0, length, 14.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return Rot(0, 0, 90) * b if along_x else b


# ------------------------------------------------------------------ the cover on the plate
def seat_checks(name, base, cover, along_x):
    print(name + "  [relaxed geometry: preload 0, faces touching]")
    ok = True
    ok &= report("seated: cover and plate do not intersect (faces touch, no overlap)", X(base, cover))
    ok &= report("cover lifted 0.3: hooks collide (cover is retained)",
                 X(base, Pos(0, 0, 0.3) * cover), expect_empty=False)
    ok &= report("cover raised 6.5: free to start the snap", X(base, Pos(0, 0, 6.5) * cover))
    # the trimmed legs must stop exactly at the plate face: material just above it, none below it
    ok &= report("cover legs land on the plate face (material just above it)",
                 X(cover, Pos(0, 0, w.PLATE_T) * Box(400, 400, 0.4, align=CTR)), expect_empty=False)
    ok &= report("cover legs do not foul the plate (nothing below the plate face)",
                 X(cover, big(-400 + w.PLATE_T)))
    ok &= report("5-cable bundle clears the ramp crest (cables passing straight through)",
                 X(base + cover, bundle(along_x, w.PLATE_T + w.RAMP_H)))
    L = w.PLATE_W if along_x else w.PLATE_H
    f0, f1 = w.HOLE_ALONG / 2 + w.ramp_len(L), w.stub_half(L)
    if f1 - f0 >= 10:
        ok &= report("5-cable bundle clears the plate floor away from the ramps",
                     X(base + cover, bundle(along_x, w.PLATE_T, f1 - f0, (f0 + f1) / 2)))
    else:
        print(f"        (no flat floor to check: ramps run to within {f1 - f0:.1f} mm of the plate edge)")
    return ok


def profile_match():
    """The stub must present the straight base's outer profile at the same ABSOLUTE heights, or the cover
    would not be flush / interchangeable where the run meets the plate."""
    print("stub profile vs straight_base")
    stub, base = g.prism(w.stub_pts(), -10, 10), g.prism(g.base_pts(), -10, 10)
    above = big(w.PLATE_T)
    ok = report("stub outer profile identical to straight_base above the plate face",
                X(D2(stub, base), above) + X(D2(base, stub), above))
    ok &= report("stub floor is the plate (solid right up to the interior floor)",
                 D(Pos(0, 0, 0.1) * Box(2 * g.BASE_IN - 0.2, 10, w.PLATE_T - 0.2, align=CTR), stub))
    return ok


def D2(a, b):
    """a - b as a solid (or None when empty), for feeding into another boolean."""
    if V(a) <= 0 or V(b) <= 0:
        return a if V(a) > 0 else None
    r = a - b
    return r if V(r) > 0 else None


def end_wall(along_x):
    """The run terminates at the plate with the matched cover's own closed end wall.  (The kit's end_cap does
    NOT fit here: its plug is cut for the 1.2 mm base floor, and the plate's floor is PLATE_T.)"""
    L = w.PLATE_W if along_x else w.PLATE_H
    cover = place_cover(along_x)
    outline = g.prism(g.cover_pts()[:6], w.stub_half(L), L / 2)
    if along_x:
        outline = Rot(0, 0, 90) * outline
    ok = report("matched cover's end wall fills the profile above the plate face",
                D(X2(outline, big(w.PLATE_T)), cover))
    cap = Pos(0, L / 2, 0) * (Rot(0, 0, 180) * g.end_cap())
    print(f"        (kit end_cap fouls the plate's thicker floor by {X(w.wallplate_entry(False), cap):.0f} mm3 "
          f"-- by design, the plate uses the closed-end cover instead)")
    return ok


# ------------------------------------------------------------------ wall side
def wall_checks():
    print("plate / sleeve / drywall")
    ok = True
    plate = w.wallplate_entry(False)
    sleeve = w.wall_sleeve()
    cut = Pos(0, 0, -200) * Box(w.CUT_W, w.CUT_H, 400, align=CTR)          # the void in the board
    hole = Pos(0, 0, -200) * Box(w.HOLE_ACROSS, w.HOLE_ALONG, 400, align=CTR)
    # THE cable path: the hole must actually be open through the finished plate.  (The first draft cut it from
    # the channel and then unioned the face slab back over it, and a "plate covers the cutout" check that did
    # not subtract the hole footprint happily passed on the solid plate.  Both are now checked explicitly.)
    ok &= report("cable hole is open right through the plate", X(plate, hole))
    ok &= report("nothing blocks the path from the channel, through the plate and sleeve, into the bay",
                 X(plate + sleeve, Pos(0, 0, -w.SL_D) * Box(w.HOLE_ACROSS - 1, w.HOLE_ALONG - 1,
                                                            w.SL_D + w.PLATE_T + w.RAMP_H, align=CTR)))
    zp = w.LIP_T + w.GR_CLR_T + 0.05        # above the lip groove, which the sleeve's lip fills
    ok &= report("plate covers the cutout everywhere EXCEPT the cable hole",
                 D(D2(Pos(0, 0, zp) * Box(w.CUT_W, w.CUT_H, 0.2, align=CTR), hole), plate))
    bore0 = Pos(0, 0, -200) * Box(w.SL_OUT_W - 2 * w.SL_T, w.SL_OUT_H - 2 * w.SL_T, 400, align=CTR)
    ok &= report("no cut gypsum is left uncovered (the ring from the bore out to the cut edge)",
                 D(D2(Pos(0, 0, 0.1) * Box(w.CUT_W, w.CUT_H, 0.2, align=CTR), bore0), plate + sleeve))
    m = min(w.PLATE_W - w.CUT_W, w.PLATE_H - w.CUT_H) / 2
    print(f"  [{'OK ' if m >= 5 else 'BAD'}] plate overlaps the cut edge by {m:.1f} mm on the tight axis")
    ok &= m >= 5.0
    ok &= report("sleeve body passes into the cutout (0.3 mm per side)",
                 D(X2(sleeve, Pos(0, 0, -w.SL_D) * Box(400, 400, w.SL_D, align=CTR)), cut))
    lip = X2(sleeve, Box(400, 400, w.LIP_T, align=CTR))
    ok &= report("sleeve lip is wider than the cutout (cannot fall into the cavity)", D(lip, cut),
                 expect_empty=False)
    ok &= report("sleeve lip sits inside the plate's groove (no interference)", X(sleeve, plate))
    ok &= report("sleeve lip is captured by the groove (groove deeper and wider than the lip)",
                 D(lip, w.lip_groove()))
    bore = Pos(0, 0, -200) * Box(w.SL_OUT_W - 2 * w.SL_T, w.SL_OUT_H - 2 * w.SL_T, 400, align=CTR)
    ok &= report("cable hole is inside the sleeve bore (cables never touch cut gypsum)", D(hole, bore))
    for s in (+1, -1):
        sc = Pos(0, s * w.CS_OFF, -200) * Cylinder(w.CS_HEAD / 2, 400, align=CTR)
        ok &= report(f"clamp screw at y={s * w.CS_OFF:+.1f} passes through intact board, not the cutout",
                     X(sc, cut))
        ok &= report(f"clamp screw at y={s * w.CS_OFF:+.1f} clears the sleeve and its groove",
                     X(sc, sleeve + w.lip_groove()))
    head = Pos(0, w.CS_OFF, w.PLATE_T - w.CS_CSK) * Cone(1.7, 3.0, w.CS_CSK, align=CTR)   # real M3 csk, 90 deg
    ok &= report("M3 countersunk head seats flush in the plate", X(plate, head))
    left = w.PLATE_T - w.CS_CSK
    print(f"  [{'OK ' if left >= 0.8 else 'BAD'}] plate left under the countersink: {left:.2f} mm")
    ok &= left >= 0.8
    ok &= report("driver access to the clamp screw down the open stub",
                 X(plate, Pos(0, w.CS_OFF, w.PLATE_T) * Cylinder(2.5, 40, align=CTR)))
    side_hole = Pos(0, 0, -200) * Box(w.HOLE_ALONG, w.HOLE_ACROSS, 400, align=CTR)   # rotated with the run
    ok &= report("side-entry plate: cable hole is open right through it too",
                 X(w.wallplate_entry(True), side_hole))
    ok &= report("side-entry plate: its hole is inside the sleeve bore as well", D(side_hole, bore))
    return ok


def X2(a, b):
    """a & b as a solid (or None when empty)."""
    if V(a) <= 0 or V(b) <= 0:
        return None
    r = a & b
    return r if V(r) > 0 else None


def bar_checks():
    ok = True
    sleeve = w.wall_sleeve()
    bar0 = w.wall_backing_bar()
    bb = bar0.bounding_box()
    fits = bb.size.X < w.CUT_W - 1 and bb.size.Y < w.CUT_H - 1
    print(f"  [{'OK ' if fits else 'BAD'}] backing bar {bb.size.X:.1f} x {bb.size.Y:.1f} passes through the "
          f"{w.CUT_W} x {w.CUT_H} cutout")
    ok &= fits
    nut = Pos(0, w.CS_OFF, -w.BAR_T) * extrude(RegularPolygon(5.5 / 2, 6, major_radius=False), amount=2.4)
    inter = X(nut, bar0)
    print(f"  [{'OK ' if 0.2 < inter < 6 else 'BAD'}] real M3 nut (5.5 AF x 2.4) seats in the pocket, gripped "
          f"by the pips: {inter:.2f} mm3 designed interference")
    ok &= 0.2 < inter < 6
    for label, t in w.DRYWALL.items():
        print(f"backing bar on {label} board ({t} mm)")
        bar = Pos(0, 0, -t) * bar0
        bd = board(t)
        ok &= report(f"{label}: bar does not intersect the board", X(bar, bd))
        ok &= report(f"{label}: bar does not intersect the sleeve (hook slot clears the wall)", X(bar, sleeve))
        ok &= report(f"{label}: bar can be hooked on from behind (3 mm back: clear of sleeve and board)",
                     X(Pos(0, 0, -3) * bar, sleeve + bd))
        ok &= report(f"{label}: rib stops the bar sliding 1 mm away from the cutout",
                     X(Pos(0, 1, 0) * bar, sleeve), expect_empty=False)
        ok &= report(f"{label}: keyed - 4 deg rotation about the screw collides with the sleeve",
                     X(Pos(0, w.CS_OFF, 0) * Rot(0, 0, 4) * Pos(0, -w.CS_OFF, 0) * bar, sleeve),
                     expect_empty=False)
        area = X(Pos(0, 0, 0.2) * bar, bd) / 0.2
        print(f"  [{'OK ' if area > 400 else 'BAD'}] {label}: bar clamps {area:.0f} mm2 of intact board "
              f"({2 * area:.0f} mm2 for the pair)")
        ok &= area > 400
        need = w.PLATE_T + t + w.BAR_T + 2.4
        print(f"  [{'OK ' if need <= 28 else 'BAD'}] {label}: screw must reach {need:.1f} mm -> an M3 x 30 "
              f"ends {30 - need:.1f} mm past the nut")
        ok &= need <= 28
        pr = w.SL_D - t
        print(f"  [{'OK ' if pr >= w.BAR_RIB + 0.5 else 'BAD'}] {label}: sleeve protrudes {pr:.1f} mm past the "
              f"board's back face (hook ribs are {w.BAR_RIB} deep)")
        ok &= pr >= w.BAR_RIB + 0.5
    return ok


def printability():
    """Overhang audit on the exported STLs for the new parts (same classes as check_mechanism)."""
    print("printability (exported STLs)")
    ok = True
    for name in w.PARTS:
        m = trimesh.load(os.path.join(g.OUT, name + ".stl"), force="mesh")
        n, c, area = m.face_normals, m.triangles_center, m.area_faces
        down = c[:, 2] > 0.3
        flat = (n[:, 2] < -0.99) & down
        ledge = (n[:, 2] < -math.cos(math.radians(g.HOOK + 1))) & ~flat & down
        steep = (n[:, 2] < -math.cos(math.radians(40))) & ~flat & ~ledge & down
        bed = area[(n[:, 2] < -0.99) & (c[:, 2] <= 0.3)].sum()
        span = 0.0
        if flat.any():
            tri = m.triangles[flat].reshape(-1, 3)
            ext = tri.max(0) - tri.min(0)
            span = min(ext[0], ext[1])
        bad = area[steep].sum()
        print(f"  {name:24s} watertight={m.is_watertight!s:5}  bed {bed:6.0f} mm2   steep overhang {bad:6.1f} "
              f"mm2   hook ledge {area[ledge].sum():6.1f} mm2   flat underside {area[flat].sum():7.1f} mm2 "
              f"(span ~{span:.1f})")
        ok &= m.is_watertight and bad < 5.0
    return ok


if __name__ == "__main__":
    g.derive(0, 0)
    allok = profile_match()
    for ax, nm in ((False, "bottom-entry plate + matched cover"), (True, "side-entry plate + matched cover")):
        allok &= seat_checks(nm, w.wallplate_entry(ax), place_cover(ax), ax)
    allok &= end_wall(False) & end_wall(True)
    g.derive()
    allok &= cm.preload_checks("bottom-entry plate", w.wallplate_entry(False), place_cover(False), w.PLATE_H)
    allok &= wall_checks() & bar_checks() & printability()
    print("ALL PASS" if allok else "SOMETHING FAILED")
