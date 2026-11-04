"""Scan AutoPET studies for iliac nodes that sit just below a vessel bifurcation.
Uses only the eval JSON (lesion centroids) and the TotalSegmentator anatomy maps (fast)."""
import json, glob, os, sys, re, numpy as np, SimpleITK as sitk
from scipy import ndimage
H = os.path.expanduser("~")
TS = json.load(open(f"{H}/Library/CloudStorage/OneDrive-UCSF/Documents/Radiology Workbench current code/dev-staging/augmented-workstation/v11-ct-chest-mvp/scripts/lib/totalseg-classes.json"))
if isinstance(TS, list): TS = {n: i for i, n in enumerate(TS)}
elif all(isinstance(k, str) and k.isdigit() for k in TS): TS = {v: int(k) for k, v in TS.items()}
idx = {r["patient"]: r for r in json.load(open(f"{H}/AutoPET/index.json"))}

def landmarks(an, img):
    sp = img.GetSpacing(); zw = lambda k: img.TransformIndexToPhysicalPoint((0, 0, int(k)))[2]
    lm = {}
    ao = an == TS["aorta"]; zs = np.nonzero(ao.any(axis=(1, 2)))[0]
    lm["aorticBifZ"] = zw(zs.min()) if len(zs) else None
    # aorta single component on the lowest slices? record the lowest slice where aorta is one blob >= 60 mm2
    for side in ("left", "right"):
        m = an == TS[f"iliac_artery_{side}"]; zs = np.nonzero(m.any(axis=(1, 2)))[0]
        lm[f"iliacTopZ_{side}"] = zw(zs.max()) if len(zs) else None
        bif = None; run = 0
        for k in sorted(zs, reverse=True):
            lab, n = ndimage.label(m[k])
            if n < 2: run = 0; continue
            sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
            big = [i + 1 for i, s in enumerate(sizes) if s * sp[0] * sp[1] >= 6]
            if len(big) >= 2:
                run += 1
                if run >= 2 and bif is None: bif = zw(k + 1)
            else: run = 0
        lm[f"ciaBifZ_{side}"] = bif
    body = an > 0; xs = np.nonzero(body.any(axis=(0, 1)))[0]
    lm["midlineX"] = img.TransformIndexToPhysicalPoint((int((xs.min() + xs.max()) / 2), 0, 0))[0] if len(xs) else 0.0
    return lm

def vessel_dist(an, img, name, xyz):
    """Distance (mm) from world xyz to the nearest voxel of label `name` on the same axial slice; also vessel centroid y offset."""
    i = img.TransformPhysicalPointToContinuousIndex([float(v) for v in xyz]); k = int(round(i[2]))
    if k < 0 or k >= an.shape[0]: return None, None
    m = an[k] == TS[name]; ys, xs = np.nonzero(m)
    if not len(ys): return None, None
    sp = img.GetSpacing(); d = np.sqrt(((xs - i[0]) * sp[0]) ** 2 + ((ys - i[1]) * sp[1]) ** 2)
    return float(d.min()), float((i[1] - ys.mean()) * sp[1])   # +ve = lesion posterior to the vessel

def main(out):
    recs = {}
    for f in glob.glob(f"{H}/AutoPET/eval*/*.json"):
        d = json.load(open(f))
        les = [g for g in d["gt"] if g.get("site") and re.search(r"iliac|Para-aortic|pelvis", g["site"])]
        if les: recs[d["id"]] = (d, les)
    print(len(recs), "studies with iliac / para-aortic / pelvic lesions", flush=True)
    rows = []
    for n, (sid, (d, les)) in enumerate(sorted(recs.items())):
        p = f"{H}/AutoPET-model/anatomy/{sid}.nii.gz"
        if not os.path.exists(p): continue
        img = sitk.ReadImage(p); an = sitk.GetArrayFromImage(img)
        lm = landmarks(an, img)
        for g in les:
            x, y, z = g["centroidMm"]; side = "left" if x > lm["midlineX"] else "right"
            ab = lm["aorticBifZ"]; cb = lm[f"ciaBifZ_{side}"]
            dil, post = vessel_dist(an, img, f"iliac_artery_{side}", (x, y, z))
            dao, _ = vessel_dist(an, img, "aorta", (x, y, z))
            row = dict(sid=sid, dx=d["diagnosis"], lesion=g["id"], site=g["site"], ml=round(g["volumeMl"], 1), suv=round(g["suvMax"], 1), xyz=[round(v) for v in (x, y, z)], side=side,
                       dzAo=None if ab is None else round(z - ab), dzCia=None if cb is None else round(z - cb), dIliac=None if dil is None else round(dil), postIliac=None if post is None else round(post), dAorta=None if dao is None else round(dao),
                       lm={k: (None if v is None else round(v)) for k, v in lm.items()})
            rows.append(row)
        if n % 25 == 0: print(n, sid, flush=True)
    json.dump(rows, open(out, "w"), indent=0)
    print("wrote", out, len(rows))
if __name__ == "__main__": main(sys.argv[1])
