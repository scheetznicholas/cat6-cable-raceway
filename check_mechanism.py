"""
Fit / mechanism checks, run BEFORE claiming anything fits.  Every check is a solid boolean on the actual
generated parts (raceway frame, not print orientation); a "must be empty" intersection prints its volume.

Rev 2 has a designed lateral PRELOAD (the cover legs are sprung outward when seated) and a slight vertical
interference of the hooked retention faces.  The classic no-intersection checks therefore run on the RELAXED
geometry (g.derive(0, 0): the base as the splayed legs see it), and the real geometry gets a separate check that
the only interference is the designed preload sliver in the snap zone.

    <AI_Image_Generator venv python> check_mechanism.py
"""
import math, os
import numpy as np, trimesh
from build123d import *
import generate_raceway as g

TOL = 0.05


def report(label, vol, expect_empty=True):
    ok = vol <= TOL if expect_empty else vol > TOL
    print(f"  [{'OK ' if ok else 'BAD'}] {label:66s} {vol:9.2f} mm3")
    return ok


def snap_checks(name, base, cover, probe_box, lift=(0, 0, 1)):
    """RELAXED geometry.  base + cover in their assembled (raceway-frame) positions.  `lift` = the direction the
    cover comes OFF (straight/elbow: away from the wall; corner covers: the diagonal, so both arms lift equally)."""
    print(name + "  [relaxed geometry: preload 0, faces touching]")
    ok = True
    d = Vector(*lift).normalized() * (1 / abs(Vector(*lift).normalized().Z))   # scaled so each arm moves 1 mm off its wall
    move = lambda k: Pos(d.X * k, d.Y * k, d.Z * k) * cover
    ok &= report("seated: cover and base do not intersect (faces touch, no overlap)", (base & cover).volume)
    lifted = move(0.3)
    ok &= report("cover lifted 0.3: hooks collide (cover is retained)", (base & lifted).volume, expect_empty=False)
    inter = (base & lifted) & Pos(0, 30, 0) * Box(50, 10, 100, align=(Align.MIN, Align.MIN, Align.CENTER))   # +X side, one arm only
    depth = inter.bounding_box().size.X if inter.volume > TOL else 0.0
    print(f"        hook overlap measured from the collision: {depth:.2f} mm per side (design {g.ENGAGE:.2f} relaxed)")
    ok &= abs(depth - g.ENGAGE) < 0.05
    ok &= report("cover raised 6.5 (bumps above each other's ramps): free to start snap", (base & move(6.5)).volume)
    ok &= report("cable bundle box inside the assembled raceway", ((base + cover) & probe_box).volume)
    return ok


def preload_checks(name, base, cover, L):
    """REAL geometry: the seated interference must be only the designed preload sliver at the bumps."""
    print(name + "  [real geometry: preload %.2f, hook %.0f deg, vert %.2f]" % (g.PRELOAD, g.HOOK, g.VERT))
    inter = base & cover
    bb = inter.bounding_box()
    bound = 2 * L * (g.PRELOAD * 1.0 + abs(g.VERT) * g.BUMP)      # generous: 1 mm tall lateral sliver + face overlap
    ok = report(f"seated interference is small (< {bound:.0f} mm3 designed preload sliver)", inter.volume - bound)
    inzone = (bb.min.Z >= g.C_RAMP_Z0 - 0.02) and (bb.max.Z <= g.B_RAMP_Z1 + 0.02)
    print(f"  [{'OK ' if inzone else 'BAD'}] interference confined to the snap zone z {g.C_RAMP_Z0:.2f}..{g.B_RAMP_Z1:.2f}"
          f"   (found z {bb.min.Z:.2f}..{bb.max.Z:.2f})")
    ok &= inzone
    if inter.volume > TOL:
        side = (inter & Box(100, 1000, 100, align=(Align.MIN, Align.CENTER, Align.MIN))).bounding_box().min.X
        atbump = side >= g.LEG_IN - g.BUMP - 0.02
        print(f"  [{'OK ' if atbump else 'BAD'}] interference only outboard of the cover bump tips |x| >= {g.LEG_IN - g.BUMP:.2f}"
              f"   (found |x| >= {side:.2f})")
        ok &= atbump
    return ok


def straight_relaxed():
    base, cover = g.straight_base(), g.straight_cover()
    bundle = Pos(0, 150, g.PAD_T + 0.3) * Box(21.0, 320, 14.0, align=(Align.CENTER, Align.CENTER, Align.MIN))   # 3 x 7 mm  x  2 x 7 mm, sticking out both ends
    ok = snap_checks("straight 300 (5 x 7 mm Cat6 as 3+2)", base, cover, bundle)
    # end cap plugs into the assembled end
    cap = g.end_cap()
    ok &= report("end cap plug clear of base + cover at the run end", ((base + cover) & cap).volume)
    env = g.prism(g.cover_pts()[:6], -g.CAP_T - 1, g.CAP_PLUG + 1)
    ok &= report("end cap stays inside the cover's outer outline", (cap - env).volume)
    ok &= report("end cap face fills the outline (gap < chamfer volume)", (g.prism(g.cover_pts()[:6], -g.CAP_T, 0) - cap).volume - 60, )
    # screw: #6 flat head Ø7 x 90deg sits at/below the pad top; driver Ø6 straight down through the open base
    for y in (50, 150, 250):
        drv = Pos(0, y, g.PAD_T) * Cylinder(3.0, 40, align=(Align.CENTER, Align.CENTER, Align.MIN))
        ok &= report(f"driver access to screw at y={y} (open base)", (base & drv).volume)
        head = Pos(0, y, g.PAD_T - 1.5) * Cone(2.0, 3.5, 1.5, align=(Align.CENTER, Align.CENTER, Align.MIN))
        ok &= report(f"#6 flat head seats fully in the pad countersink at y={y}", (base & head).volume)
    # every floor window / screw pad stays clear of the walls and the ends
    bb = base.bounding_box()
    ok &= report("base floor solid at both ends (end-cap plug seats on it)",
                 (Pos(0, 0, 0.05) * Box(g.INTERIOR_W - 0.2, 9, g.BF - 0.1, align=(Align.CENTER, Align.MIN, Align.MIN)) - base).volume
                 + (Pos(0, 300 - 9, 0.05) * Box(g.INTERIOR_W - 0.2, 9, g.BF - 0.1, align=(Align.CENTER, Align.MIN, Align.MIN)) - base).volume)
    return ok


def strain():
    L = (g.H - g.CT) - g.C_ROOT_Z
    snap = g.ENGAGE                                              # deflection from free while the bumps pass
    rest = g.PRELOAD + abs(min(g.VERT, 0)) / math.tan(math.radians(g.HOOK))
    e_snap = 1.5 * g.CL * snap / L**2
    e_rest = 1.5 * g.CL * rest / L**2
    print(f"leg strain (cantilever {L:.1f} mm, {g.CL} thick): snap-on {snap:.2f} mm -> {e_snap*100:.2f}% "
          f"({'ok' if e_snap < 0.01 else 'HIGH'} for PLA/PETG); resting preload {rest:.2f} mm -> {e_rest*100:.2f}% "
          f"({'ok, no creep' if e_rest < 0.003 else 'HIGH: PLA will creep'})")
    return e_snap < 0.01 and e_rest < 0.003


def elbow_relaxed():
    base, cover = g.elbow_flat_base(), g.elbow_flat_cover()
    # bent bundle: 3-wide x 2-high pack swept around the corner (a 20-wide, 14-tall L, inside radius 8)
    arm = Box(20.0, 60, 14.0, align=(Align.CENTER, Align.MIN, Align.MIN))
    L = (Pos(0, 0, g.PAD_T + 0.3) * arm) + (Pos(0, 0, g.PAD_T + 0.3) * (Rot(0, 0, -90) * arm)) \
        + Pos(0, 0, g.PAD_T + 0.3) * Box(20.0, 20.0, 14.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return snap_checks("flat elbow", base, cover, L)


def corners_relaxed():
    ok = True
    # inside corner: two stubs (arm A as built, arm B = mirror) under the one-piece cover
    stub = g.corner_inside_base_stub()
    base = stub + g.mirror_plane(stub, (0, 1, -1))
    cover = g.corner_inside_cover()
    bundle = Pos(0, 0, g.PAD_T + 0.3) * Box(21.0, 60, 14.0, align=(Align.CENTER, Align.MIN, Align.MIN))
    bundle = bundle + g.mirror_plane(bundle, (0, 1, -1))
    bundle = bundle & Pos(0, g.PAD_T + 0.3, g.PAD_T + 0.3) * Box(100, 100, 100, align=(Align.CENTER, Align.MIN, Align.MIN))
    ok &= snap_checks("inside corner (cover over two stubs)", base, cover, bundle, lift=(0, 1, 1))
    ok &= report("inside corner: the two base stubs meet at the mitre without overlapping", (stub & g.mirror_plane(stub, (0, 1, -1))).volume)
    # outside corner
    stub = g.corner_outside_base_stub()
    base = stub + g.mirror_plane(stub, (0, 1, 1))
    cover = g.corner_outside_cover()
    bundle = Pos(0, 0, g.PAD_T + 0.3) * Box(21.0, 60, 14.0, align=(Align.CENTER, Align.MIN, Align.MIN))
    bundle = bundle + g.mirror_plane(bundle, (0, 1, 1))     # mirror across y = -z: arm B in front of the wall
    ok &= snap_checks("outside corner (cover over two stubs)", base, cover, bundle, lift=(0, -1, 1))
    ok &= report("outside corner: stubs meet at the mitre without overlapping", (stub & g.mirror_plane(stub, (0, 1, 1))).volume)
    return ok


def real_geometry():
    # the profile is identical on every piece, so the straight stands in for all of them
    ok = preload_checks("straight 300", g.straight_base(), g.straight_cover(), 300)
    # real geometry: the cover bump tip is inboard of the base wall, so lowering the cover onto the base must meet the
    # wall's chamfered top corner with the cover RAMP (not a flat face): the ramp starts below the tip
    ok &= report("cover ramp reaches below the bump tip (lead-in exists)", -(g.C_TIP_Z - g.C_RAMP_Z0) + 0.5)
    return ok


def printability():
    """Overhang audit on the exported (print-oriented) STLs.  Downward faces are classed as: bed contact, flat
    underside (bridges / 90 deg ledges), hook ledge (within HOOK+1 deg of horizontal: the 0.75 mm retention
    faces, same 2-line cantilever as rev 1's flat ledges) or steep overhang (50..69 deg from vertical = bad)."""
    print("printability (exported STLs)")
    ok = True
    ledge_cos = math.cos(math.radians(g.HOOK + 1))
    for f in sorted(os.listdir(g.OUT)):
        if not f.endswith(".stl"):
            continue
        m = trimesh.load(os.path.join(g.OUT, f), force="mesh")
        n = m.face_normals
        c = m.triangles_center
        area = m.area_faces
        down = c[:, 2] > 0.3
        flat = (n[:, 2] < -0.99) & down
        ledge = (n[:, 2] < -ledge_cos) & ~flat & down
        steep = (n[:, 2] < -math.cos(math.radians(40))) & ~flat & ~ledge & down
        bed = area[(n[:, 2] < -0.99) & (c[:, 2] <= 0.3)].sum()
        span = 0.0
        if flat.any():
            tri = m.triangles[flat]
            ext = tri.reshape(-1, 3).max(0) - tri.reshape(-1, 3).min(0)
            span = min(ext[0], ext[1])
        bad = area[steep].sum()
        print(f"  {f:30s} watertight={m.is_watertight!s:5}  bed {bed:6.0f} mm2   steep overhang {bad:6.1f} mm2   "
              f"hook ledge {area[ledge].sum():6.1f} mm2   flat underside {area[flat].sum():7.1f} mm2 (span ~{span:.1f})")
        ok &= m.is_watertight and bad < 5.0
    return ok


if __name__ == "__main__":
    g.derive(0, 0)
    allok = straight_relaxed() & elbow_relaxed() & corners_relaxed()
    g.derive()
    allok &= real_geometry() & strain() & printability()
    print("ALL PASS" if allok else "SOMETHING FAILED")
