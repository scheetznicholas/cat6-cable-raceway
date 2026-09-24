# Cat6 Cable Raceway (5-cable bundle, snap-on cover)

Printable wall raceway for a bundle of five Cat6 cables: straights, a flat 90° elbow, inside/outside
room-corner pieces and end caps.  Bambu H2S project files included.

| | |
|---|---|
| outer size | 32 wide × 20 tall |
| interior | 25.9 × 17.6 mm — 5 Cat6 stacked 3+2 with room, even 7 mm thick-jacket cable |
| cover | one-piece snap-over, 1.2 mm top and legs, 0.8 mm chamfered edges |
| base | 1.2 mm floor with lightening windows and 2 mm screw pads, 10 mm walls, countersunk #6 / M3.5 screw holes every 100 mm (or foam tape on the rails) |
| snap | 0.75 mm ridges on both parts with 20° hooked retention faces and 0.1 mm lateral preload: the sprung legs pull the cover tight to the wall, no rattle. 0.85 mm engagement, 0.70 % leg strain during snap-on, 0.20 % resting |
| filament | rev 2 (2026-09-24) uses ~36 % less than rev 1: 232 cm³ / ~290 g PLA per project, 38 cm³ per 300 mm of run |

## Files

- `CableRaceway_H2S_PLA.3mf` — Bambu PLA Basic, 0.20 mm, 3 walls, 15 % gyroid (all sections are solid walls anyway), no supports (2 plates)
- `CableRaceway_H2S_PETG.3mf` — same layout in Bambu PETG HF (tougher snap legs if the cover will come off a lot)
- `stl/` — every part, already in print orientation
- `generate_raceway.py` — build123d generator (all dimensions are parameters at the top)
- `check_mechanism.py` — solid-boolean fit checks: cover seats on the relaxed geometry without interference, the
  hooks retain it when lifted, the snap starts freely, the real geometry interferes only by the designed preload
  sliver at the ridges, a 21 × 14 mm cable bundle clears every piece, screw heads seat, end cap fits, leg strain,
  overhang audit of every STL (`check_mechanism.log` = last run, ALL PASS)
- `make_3mf.py` — builds the 3MF via the Bambu Studio CLI (`--petg` for the PETG version)

## What's in one project (per print of both plates)

| part | qty | what it is |
|---|---|---|
| straight_base_300 / straight_cover_300 | 4 + 4 | 1.2 m of run |
| straight_base_150 | 1 | half base so cover joints never sit over base joints |
| elbow_flat_base / elbow_flat_cover | 2 + 2 | 90° bend within the same wall (baseboard run turning up to a jack) |
| corner_inside_cover + corner_inside_base_stub | 1 + 2 | run goes around an inside (concave) room corner |
| corner_outside_cover + corner_outside_base_stub | 1 + 2 | run goes around an outside (convex) corner |
| end_cap | 2 | plugs an open end |

Need more run: duplicate plate 1 in Bambu Studio (or `Ctrl+D` the straights).  Don't need a corner type: delete it.

## Install

1. Start the base run with the 150 mm piece, then 300s.  Screw through the floor holes (#6 wood screws or
   drywall anchors) or use foam tape on the floor.  Butt base pieces end to end; the joints are hidden.
2. Flat elbow: the base is an L with a screw hole in each arm; the straight bases butt against its 55 mm arms
   and its 70 mm cover overlaps the joint.
3. Room corner: screw one stub to each wall with their mitred ends meeting at the corner, then the one-piece
   corner cover presses straight into the corner (both arms snap at once).  Straight base/cover continue from
   the stub ends.
4. Lay the cables in, then press each cover on: it has a lead-in ramp and clicks when seated.  The legs are
   sprung against the base and the ridges are hooked, so the cover is pulled tight to the wall and won't rattle
   or pop off.  To remove, slip a putty knife under a leg at the wall and lever the leg outward (about 1 mm)
   while lifting; work along the piece.
5. End caps push into the open interior at the run ends.

Cover joints on a long run: cut a straight cover shorter with a hacksaw if a joint would land on an elbow arm.

## Print notes

- Everything prints support-free in the exported orientation: bases floor-down, covers top-down, corner
  covers with one arm flat and the other standing.  The inside-corner cover stands on its leg edges, so it has
  a 5 mm per-object brim; the run under its flat arm is a 29.6 mm bridge (fine on an H2S).  The hooked retention
  faces are 0.8 mm ledges tilted 20°, the same two-line cantilever the rev 1 flat ledges were.
- Regenerate after changing parameters: `generate_raceway.py` → `check_mechanism.py` (must print ALL PASS) →
  `make_3mf.py`.
- If a printed cover feels too tight/loose, change `PRELOAD` (0.10; raise for tighter) or `VERT` (-0.05) in the
  generator and reprint one 150 mm base + cover to test; the other pieces inherit the same profile.  Rev 1
  (flat faces, 0.15/0.2 mm clearances, 1.6 mm sheets) printed fine but felt loose — that is why rev 2 preloads.
- Filament: set `FLOOR_WINDOWS = False` for a solid base floor (e.g. if you want full-width tape contact);
  it costs about 3.5 cm³ per 300 mm base.  Sheets are 1.2 mm = three 0.4 mm walls, so 2–3 wall loops print them solid.
