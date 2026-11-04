"""Inguinal candidates: lesions labelled inguinal, with z relative to the femoral head top and the hip bone, and anterior position."""
import json, glob, os, sys, re, numpy as np, SimpleITK as sitk
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pelvis_scan import TS, H, landmarks, vessel_dist
rows = []
recs = {}
for f in glob.glob(f"{H}/AutoPET/eval*/*.json"):
    d = json.load(open(f)); les = [g for g in d["gt"] if g.get("site") and "inguinal" in g["site"]]
    if les: recs[d["id"]] = (d, les)
print(len(recs), "studies with inguinal-labelled lesions", flush=True)
for n, (sid, (d, les)) in enumerate(sorted(recs.items())):
    p = f"{H}/AutoPET-model/anatomy/{sid}.nii.gz"
    if not os.path.exists(p): continue
    img = sitk.ReadImage(p); an = sitk.GetArrayFromImage(img); sp = img.GetSpacing()
    zw = lambda k: img.TransformIndexToPhysicalPoint((0, 0, int(k)))[2]
    body = an > 0; xs = np.nonzero(body.any(axis=(0, 1)))[0]; mid = img.TransformIndexToPhysicalPoint((int((xs.min() + xs.max()) / 2), 0, 0))[0]
    for g in les:
        x, y, z = g["centroidMm"]; side = "left" if x > mid else "right"
        fe = an == TS[f"femur_{side}"]; zs = np.nonzero(fe.any(axis=(1, 2)))[0]
        ftop = zw(zs.max()) if len(zs) else None
        hip = an == TS[f"hip_{side}"]; hz = np.nonzero(hip.any(axis=(1, 2)))[0]; hbot = zw(hz.min()) if len(hz) else None
        i = img.TransformPhysicalPointToContinuousIndex([float(x), float(y), float(z)]); k = int(round(i[2]))
        # femoral head centre y on this slice (anterior offset of the node): +ve = node anterior to the femur centre
        ant = None
        if 0 <= k < an.shape[0]:
            ys, xs2 = np.nonzero(fe[k])
            if len(ys): ant = float((ys.mean() - i[1]) * sp[1])
        dil, _ = vessel_dist(an, img, f"iliac_artery_{side}", (x, y, z))
        rows.append(dict(sid=sid, dx=d["diagnosis"], lesion=g["id"], site=g["site"], ml=round(g["volumeMl"], 1), suv=round(g["suvMax"], 1), xyz=[round(v) for v in (x, y, z)], side=side,
                         dzFemurTop=None if ftop is None else round(z - ftop), dzHipBottom=None if hbot is None else round(z - hbot), antOfFemur=None if ant is None else round(ant), dIliac=None if dil is None else round(dil)))
    if n % 25 == 0: print(n, sid, flush=True)
json.dump(rows, open(sys.argv[1], "w"), indent=0); print("wrote", sys.argv[1], len(rows))
