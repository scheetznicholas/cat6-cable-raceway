"""
Fit / mechanism checks, run BEFORE claiming anything fits.  Every check is a solid boolean on the actual
generated parts (raceway frame, not print orientation); a "must be empty" intersection prints its volume.

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
    """base + cover in their assembled (raceway-frame) positions.  `lift` = the direction the cover comes OFF
    (straight/elbow: away from the wall; corner covers: the diagonal, so both arms lift off their walls equally)."""
    print(name)
    ok = True
    d = Vector(*lift).normalized() * (1 / abs(Vector(*lift).normalized().Z))   # scaled so each arm moves 1 mm off its wall
    move = lambda k: Pos(d.X * k, d.Y * k, d.Z * k) * cover
    ok &= report("seated: cover and base do not intersect", (base & cover).volume)
    ok &= report("seated + cover shifted 0.1 sideways: still free (lateral play exists)", (base & (Pos(0.1, 0, 0) * cover)).volume)
    lifted = move(g.VERT + 0.2)
    ok &= report("cover lifted 0.4: bumps collide (cover is retained)", (base & lifted).volume, expect_empty=False)
    # engagement depth: how far the base bump pokes into the (lifted) cover bump, one side only
    inter = (base & lifted) & Pos(0, 30, 0) * Box(50, 10, 100, align=(Align.MIN, Align.MIN, Align.CENTER))   # +X side, one arm only
    depth = inter.bounding_box().size.X if inter.volume > TOL else 0.0
    print(f"        bump overlap measured from the collision: {depth:.2f} mm per side (design {g.ENGAGE:.2f})")
    ok &= abs(depth - g.ENGAGE) < 0.05
    ok &= report("cover raised 6.5 (bumps above each other's ramps): free to start snap", (base & move(6.5)).volume)
    ok &= report("cable bundle box inside the assembled raceway", ((base + cover) & probe_box).volume)
    return ok


def straight():
    base, cover = g.straight_base(), g.straight_cover()
    bundle = Pos(0, 150, g.BF + 0.5) * Box(21.0, 320, 14.0, align=(Align.CENTER, Align.CENTER, Align.MIN))   # 3 x 7 mm  x  2 x 7 mm, sticking out both ends
    ok = snap_checks("straight 300 (5 x 7 mm Cat6 as 3+2)", base, cover, bundle)
    # end cap plugs into the assembled end
    cap = g.end_cap()
    ok &= report("end cap plug clear of base + cover at the run end", ((base + cover) & cap).volume)
    env = g.prism(g.cover_pts()[:6], -g.CAP_T - 1, g.CAP_PLUG + 1)
    ok &= report("end cap stays inside the cover's outer outline", (cap - env).volume)
    ok &= report("end cap face fills the outline (gap < chamfer volume)", (g.prism(g.cover_pts()[:6], -g.CAP_T, 0) - cap).volume - 60, )
    # screw: #6 flat head Ø7 x 90deg sits at/below the floor top; driver Ø6 straight down through the open base
    for y in (50, 150, 250):
        drv = Pos(0, y, g.BF) * Cylinder(3.0, 40, align=(Align.CENTER, Align.CENTER, Align.MIN))
        ok &= report(f"driver access to screw at y={y} (open base)", (base & drv).volume)
    # leg strain estimate (cantilever plate): e = 1.5 t y / L^2
    L = (g.H - g.CT) - g.C_BUMP_Z1
    e = 1.5 * g.CL * g.ENGAGE / L**2
    print(f"        leg flex during snap-on: {g.ENGAGE:.2f} mm over a {L:.1f} mm leg -> {e*100:.2f}% strain "
          f"({'ok' if e < 0.01 else 'HIGH'} for PLA/PETG)")
    return ok & (e < 0.01)


def elbow():
    base, cover = g.elbow_flat_base(), g.elbow_flat_cover()
    # bent bundle: 3-wide x 2-high pack swept around the corner (a 20-wide, 14-tall L, inside radius 8)
    arm = Box(20.0, 60, 14.0, align=(Align.CENTER, Align.MIN, Align.MIN))
    L = (Pos(0, 0, g.BF + 0.5) * arm) + (Pos(0, 0, g.BF + 0.5) * (Rot(0, 0, -90) * arm)) \
        + Pos(0, 0, g.BF + 0.5) * Box(20.0, 20.0, 14.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return snap_checks("flat elbow", base, cover, L)


def corners():
    ok = True
    # inside corner: two stubs (arm A as built, arm B = mirror) under the one-piece cover
    stub = g.corner_inside_base_stub()
    base = stub + g.mirror_plane(stub, (0, 1, -1))
    cover = g.corner_inside_cover()
    bundle = Pos(0, 0, g.BF + 0.5) * Box(21.0, 60, 14.0, align=(Align.CENTER, Align.MIN, Align.MIN))
    bundle = bundle + g.mirror_plane(bundle, (0, 1, -1))
    bundle = bundle & Pos(0, g.BF + 0.5, g.BF + 0.5) * Box(100, 100, 100, align=(Align.CENTER, Align.MIN, Align.MIN))
    ok &= snap_checks("inside corner (cover over two stubs)", base, cover, bundle, lift=(0, 1, 1))
    ok &= report("inside corner: the two base stubs meet at the mitre without overlapping", (stub & g.mirror_plane(stub, (0, 1, -1))).volume)
    # outside corner
    stub = g.corner_outside_base_stub()
    base = stub + g.mirror_plane(stub, (0, 1, 1))
    cover = g.corner_outside_cover()
    bundle = Pos(0, 0, g.BF + 0.5) * Box(21.0, 60, 14.0, align=(Align.CENTER, Align.MIN, Align.MIN))
    bundle = bundle + g.mirror_plane(bundle, (0, 1, 1))     # mirror across y = -z: arm B in front of the wall
    ok &= snap_checks("outside corner (cover over two stubs)", base, cover, bundle, lift=(0, -1, 1))
    ok &= report("outside corner: stubs meet at the mitre without overlapping", (stub & g.mirror_plane(stub, (0, 1, 1))).volume)
    return ok


def printability():
    """Overhang audit on the exported (print-oriented) STLs: faces steeper than 50 deg above the first layer."""
    print("printability (exported STLs)")
    ok = True
    for f in sorted(os.listdir(g.OUT)):
        if not f.endswith(".stl"):
            continue
        m = trimesh.load(os.path.join(g.OUT, f), force="mesh")
        n = m.face_normals
        c = m.triangles_center
        area = m.area_faces
        steep = (n[:, 2] < -math.cos(math.radians(40))) & (c[:, 2] > 0.3)          # > 50 deg overhang, not on the bed
        flat = (n[:, 2] < -0.99) & (c[:, 2] > 0.3)                                  # horizontal undersides (bridges / tiny ledges)
        bed = area[(n[:, 2] < -0.99) & (c[:, 2] <= 0.3)].sum()
        # widest horizontal underside: bridge span estimate = extent of flat faces in the narrower XY direction
        span = 0.0
        if flat.any():
            tri = m.triangles[flat]
            ext = tri.reshape(-1, 3).max(0) - tri.reshape(-1, 3).min(0)
            span = min(ext[0], ext[1])
        bad = area[steep & ~flat].sum()
        print(f"  {f:30s} watertight={m.is_watertight!s:5}  bed contact {bed:7.0f} mm2   steep overhang {bad:6.1f} mm2   "
              f"flat underside {area[flat].sum():7.1f} mm2 (span ~{span:.1f})")
        ok &= m.is_watertight and bad < 5.0
    return ok


if __name__ == "__main__":
    allok = straight() & elbow() & corners() & printability()
    print("ALL PASS" if allok else "SOMETHING FAILED")
