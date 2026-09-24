"""Build a native Bambu Studio project (H2S, 0.4 nozzle, 0.20 mm) from stl/ via the Bambu Studio CLI.
Usage:  python make_3mf.py            -> CableRaceway_H2S_PLA.3mf    (Bambu PLA Basic, 3 walls)
        python make_3mf.py --petg     -> CableRaceway_H2S_PETG.3mf   (Bambu PETG HF, 3 walls; tougher snap legs)
One project = 1.2 m of run + 2 flat elbows + 1 inside corner + 1 outside corner + 2 end caps.  Duplicate the
straight plate in Bambu Studio for longer runs.  Everything prints support-free in its exported orientation."""
import os, subprocess, sys, zipfile, re, json, shutil

PETG = "--petg" in sys.argv
BS = r"C:\Program Files\Bambu Studio\bambu-studio.exe"
SYS = os.path.join(os.environ["APPDATA"], "BambuStudio", "system", "BBL")
MACHINE = os.path.join(SYS, "machine", "Bambu Lab H2S 0.4 nozzle.json")
PROCESS = os.path.join(SYS, "process", "0.20mm Standard @BBL H2S.json")
FILAMENT = os.path.join(SYS, "filament", "Bambu PETG HF @BBL H2S.json" if PETG else "Bambu PLA Basic @BBL H2S.json")
OUT = "CableRaceway_H2S_PETG.3mf" if PETG else "CableRaceway_H2S_PLA.3mf"

COUNTS = {                       # copies per project
    "straight_base_300": 4, "straight_cover_300": 4, "straight_base_150": 1,
    "elbow_flat_base": 2, "elbow_flat_cover": 2,
    "corner_inside_cover": 1, "corner_inside_base_stub": 2,
    "corner_outside_cover": 1, "corner_outside_base_stub": 2,
    "end_cap": 2,
}
BRIM_OBJECTS = {"corner_inside_cover": "5"}   # stands on two 1.6 mm leg edges -> per-object brim; nothing else needs one

here = os.path.dirname(os.path.abspath(__file__)); os.chdir(here)
pin = os.path.join(here, "plate_in"); shutil.rmtree(pin, ignore_errors=True); os.makedirs(pin)
parts = []
for name, n in COUNTS.items():
    for k in range(1, n + 1):
        dst = os.path.join(pin, f"{name}_{k}.stl" if n > 1 else f"{name}.stl")
        shutil.copy(os.path.join(here, "stl", name + ".stl"), dst); parts.append(dst)

cmd = [BS, "--load-settings", f"{MACHINE};{PROCESS}", "--load-filaments", FILAMENT,
       "--arrange", "1", "--export-3mf", OUT, "--outputdir", here] + parts
subprocess.run(cmd, check=True, timeout=900)
res = json.load(open("result.json")); os.remove("result.json")
if res.get("return_code") != 0:
    sys.exit(f"Bambu CLI failed: {res}")
shutil.rmtree(pin, ignore_errors=True)

# print settings edited inside the zip (Bambu reverts anything not listed in different_settings_to_system)
z = zipfile.ZipFile(OUT); items = {n: z.read(n) for n in z.namelist()}; z.close()
j = json.loads(items["Metadata/project_settings.config"].decode())
edits = {"wall_loops": "3", "sparse_infill_density": "15%", "sparse_infill_pattern": "gyroid",
         "layer_height": "0.2", "enable_support": "0", "brim_type": "no_brim",
         "seam_position": "aligned", "top_shell_layers": "4", "bottom_shell_layers": "4"}
j.update(edits)
ds = set(j.get("different_settings_to_system", [""])[0].split(";")) - {""}
ds |= set(edits)
j["different_settings_to_system"] = [";".join(sorted(ds))] + j.get("different_settings_to_system", [""])[1:]
items["Metadata/project_settings.config"] = json.dumps(j, indent=4).encode()

ms = items["Metadata/model_settings.config"].decode()
for name, width in BRIM_OBJECTS.items():
    for m in re.findall(rf'\n    <metadata key="name" value="({re.escape(name)}(?:_\d+)?\.stl)"/>', ms):
        tag = '\n    ' + f'<metadata key="name" value="{m}"/>'      # 4-space indent = object level, not the <part> copy
        ms = ms.replace(tag, tag + '\n    <metadata key="brim_type" value="outer_only"/>'
                                   '\n    ' + f'<metadata key="brim_width" value="{width}"/>')
items["Metadata/model_settings.config"] = ms.encode()
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zo:
    for n, b in items.items():
        zo.writestr(n, b)

z = zipfile.ZipFile(OUT)
ms = z.read("Metadata/model_settings.config").decode()
names = dict(re.findall(r'<object id="(\d+)">\s*<metadata key="name" value="([^"]+)"', ms))
os.makedirs("previews", exist_ok=True)
for i, p in enumerate(re.findall(r"<plate>(.*?)</plate>", ms, re.S), 1):
    ids = re.findall(r'key="object_id" value="(\d+)"', p)
    print(f"plate {i}: {len(ids)} objects: {sorted(names.get(x, x) for x in ids)}")
    png = f"Metadata/plate_{i}.png"
    if png in z.namelist():
        open(os.path.join("previews", f"plate_{i}{'_petg' if PETG else ''}.png"), "wb").write(z.read(png))
print(OUT, os.path.getsize(OUT) // 1024, "KB")
