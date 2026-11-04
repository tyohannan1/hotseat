"""Find and draw nodal lesions in AutoPET studies for the Hot Seat lecture.

  survey <sid> [--region pelvis|axilla|neck|chest] [--out dir]
      prints every expert-mask lesion with a proposed anatomic placement and
      writes <out>/<sid>-sheet.png: coronal PET MIP with numbered lesions +
      one axial fused crop per lesion.
  figure <sid> --out file.png --crop pelvis|chest|axilla|neck
         [--a <lesion#> --b <lesion#>] [--coronal] [--title "..."] [--nolabel]
      the slide image: axial fused crop(s) through the chosen lesions, A/B
      circles, optional coronal panel, provenance line in the corner.

Grids: CT native (anatomy map from TotalSegmentator shares it), PET native
(SEG shares it). Axials are drawn on the CT grid with PET resampled to that
slice. World = DICOM LPS: +x patient left, +y posterior, +z head.
"""
import os, sys, json, glob, math
import numpy as np, SimpleITK as sitk, pydicom, highdicom as hd
from scipy import ndimage
from PIL import Image, ImageDraw, ImageFont

H = os.path.expanduser("~")
INDEX = json.load(open(f"{H}/AutoPET/index.json"))
TS = json.load(open(f"{H}/Library/CloudStorage/OneDrive-UCSF/Documents/Radiology Workbench current code/dev-staging/augmented-workstation/v11-ct-chest-mvp/scripts/lib/totalseg-classes.json"))
FONT = "/System/Library/Fonts/Helvetica.ttc"

def font(sz, bold=False):
    try: return ImageFont.truetype(FONT, sz, index=1 if bold else 0)
    except Exception: return ImageFont.load_default()

def row_for(sid):
    pat, date = sid.rsplit("_", 1)
    for r in INDEX:
        if r["patient"] == pat and r["studyDate"] == date: return r
    raise SystemExit(f"no index row for {sid}")

def read_series(d):
    rd = sitk.ImageSeriesReader(); files = rd.GetGDCMSeriesFileNames(d); rd.SetFileNames(files); return rd.Execute(), files

def hms(s):
    s = str(s).split(".")[0].ljust(6, "0"); return int(s[:2]) * 3600 + int(s[2:4]) * 60 + int(s[4:6])

def suv_factor(first_pet_file):
    d = pydicom.dcmread(first_pet_file, stop_before_pixels=True)
    rp = d.RadiopharmaceuticalInformationSequence[0]
    weight = float(d.PatientWeight); dose = float(rp.RadionuclideTotalDose); half = float(rp.RadionuclideHalfLife)
    inj = hms(rp.RadiopharmaceuticalStartTime); scan = hms(d.get("SeriesTime", d.get("AcquisitionTime")))
    dt = scan - inj
    if dt < 0: dt += 86400
    return weight * 1000.0 / (dose * 0.5 ** (dt / half))

def seg_to_image(seg_path):
    seg = hd.seg.segread(seg_path)
    vol = seg.get_volume(combine_segments=True, skip_overlap_checks=True)
    arr = np.asarray(vol.array).astype(np.uint8); aff = np.asarray(vol.affine)
    img = sitk.GetImageFromArray(arr)
    A = aff[:3, :3][:, [2, 1, 0]]; sp = np.linalg.norm(A, axis=0); D = A / sp
    img.SetSpacing([float(s) for s in sp]); img.SetDirection([float(v) for v in D.flatten()]); img.SetOrigin([float(o) for o in aff[:3, 3]])
    return img

MIM_HOT = [(0.0, 0, 0, 0), (0.15, .25, 0, 0), (0.3, .55, 0, 0), (0.5, 1, 0, 0), (0.7, 1, .5, 0), (0.9, 1, 1, 0), (1.0, 1, 1, 0)]
def mim_hot(t):
    """Piecewise-linear mim_hot colormap (petColormaps.ts) over t in [0,1] -> float RGB array."""
    xs = np.array([m[0] for m in MIM_HOT]); out = np.zeros(t.shape + (3,), np.float32)
    for c in range(3): out[..., c] = np.interp(t, xs, np.array([m[1 + c] for m in MIM_HOT]))
    return out

class Study:
    def __init__(self, sid):
        self.sid = sid; r = row_for(sid); self.row = r; sd = r["studyDir"]
        self.ct, self.ctfiles = read_series(os.path.join(sd, r["ct"]["dir"]))
        self.pet, pfiles = read_series(os.path.join(sd, r["pt"]["dir"]))
        self.suvf = suv_factor(pfiles[0])
        seg = seg_to_image(os.path.join(sd, r["seg"]["dir"], r["seg"]["file"]))
        # SEG onto the PET grid (they normally coincide; resample to be safe)
        seg = sitk.Resample(seg, self.pet, sitk.Transform(), sitk.sitkNearestNeighbor, 0, sitk.sitkUInt8)
        self.seg = sitk.GetArrayFromImage(seg)                      # [z,y,x] on PET grid
        self.suv = sitk.GetArrayFromImage(self.pet).astype(np.float32) * self.suvf
        self.anat = sitk.ReadImage(f"{H}/AutoPET-model/anatomy/{sid}.nii.gz")
        # the NIfTI map carries a flipped y direction; resample it onto the CT grid so array indices line up with ctarr
        self.anat = sitk.Resample(self.anat, self.ct, sitk.Transform(), sitk.sitkNearestNeighbor, 0, sitk.sitkUInt8)
        self.an = sitk.GetArrayFromImage(self.anat)                 # [z,y,x] on the CT grid
        self.ctarr = sitk.GetArrayFromImage(self.ct).astype(np.int16)
        self.lesions = self.components()
        self.landmarks = self.pelvic_landmarks()
        for L in self.lesions: L["place"] = self.place(L)
        self.date = f'{r["studyDate"][:4]}-{r["studyDate"][4:6]}-{r["studyDate"][6:]}'

    # ---- lesions
    def components(self):
        lab, n = ndimage.label(self.seg > 0, structure=np.ones((3, 3, 3))); self.lab = lab
        sp = self.pet.GetSpacing(); vox_ml = sp[0] * sp[1] * sp[2] / 1000.0
        out = []
        for i in range(1, n + 1):
            m = lab == i; cnt = int(m.sum())
            if cnt * vox_ml < 0.05: continue
            zz, yy, xx = np.nonzero(m)
            c_idx = (float(xx.mean()), float(yy.mean()), float(zz.mean()))
            cw = self.pet.TransformContinuousIndexToPhysicalPoint(c_idx)
            s = self.suv[m]; k = int(np.argmax(s)); peak_idx = (int(xx[k]), int(yy[k]), int(zz[k]))
            pw = self.pet.TransformIndexToPhysicalPoint(peak_idx)
            # widest axial slice (most voxels) → the slice to draw
            zs, counts = np.unique(zz, return_counts=True); zbest = int(zs[np.argmax(counts)])
            zw = self.pet.TransformIndexToPhysicalPoint((peak_idx[0], peak_idx[1], zbest))[2]
            ext = [(float(xx.max() - xx.min() + 1) * sp[0]), (float(yy.max() - yy.min() + 1) * sp[1]), (float(zz.max() - zz.min() + 1) * sp[2])]
            out.append(dict(n=len(out) + 1, id=i, ml=cnt * vox_ml, suvmax=float(s.max()), centroid=[round(v, 1) for v in cw], peak=[round(v, 1) for v in pw], zdraw=round(float(zw), 1), extent=[round(e) for e in ext]))
        out.sort(key=lambda L: -L["ml"])
        for i, L in enumerate(out): L["n"] = i + 1
        return out

    # ---- anatomy helpers (CT grid)
    def label_mask(self, name): return self.an == TS[name]
    def zworld_ct(self, k): return self.ct.TransformIndexToPhysicalPoint((0, 0, int(k)))[2]
    def kslice_ct(self, zw):
        k = self.ct.TransformPhysicalPointToContinuousIndex((0.0, 0.0, float(zw)))[2]; return int(round(min(max(k, 0), self.ct.GetSize()[2] - 1)))
    def xy_ct(self, xw, yw):
        i = self.ct.TransformPhysicalPointToContinuousIndex((float(xw), float(yw), 0.0)); return i[0], i[1]
    def extent_z(self, name):
        m = self.label_mask(name); zs = np.nonzero(m.any(axis=(1, 2)))[0]
        if not len(zs): return None
        return self.zworld_ct(zs.min()), self.zworld_ct(zs.max())
    def midline_x(self):
        m = self.an > 0; xs = np.nonzero(m.any(axis=(0, 1)))[0]
        if not len(xs): return 0.0
        return self.ct.TransformIndexToPhysicalPoint((int((xs.min() + xs.max()) / 2), 0, 0))[0]

    def pelvic_landmarks(self):
        lm = {}
        ao = self.extent_z("aorta"); lm["aorticBifZ"] = round(ao[0], 1) if ao else None
        for side in ("left", "right"):
            m = self.label_mask(f"iliac_artery_{side}")
            bif = None; run = 0
            zs = np.nonzero(m.any(axis=(1, 2)))[0]
            for k in sorted(zs, reverse=True):            # from the aortic end downward
                lab, n = ndimage.label(m[k]); sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1)) if n else []
                big = sum(1 for s in sizes if s * self.ct.GetSpacing()[0] ** 2 >= 8)
                run = run + 1 if big >= 2 else 0
                if run >= 3: bif = self.zworld_ct(k + 2); break
            lm[f"commonIliacBifZ_{side}"] = round(bif, 1) if bif is not None else None
            fe = self.extent_z(f"femur_{side}"); lm[f"femurTopZ_{side}"] = round(fe[1], 1) if fe else None
            cl = self.extent_z(f"clavicula_{side}"); lm[f"clavicleBottomZ_{side}"] = round(cl[0], 1) if cl else None
        lm["midlineX"] = round(self.midline_x(), 1)
        return lm

    def place(self, L):
        """Coarse anatomic placement from the TotalSegmentator map. A proposal, not a verdict."""
        x, y, z = L["centroid"]; lm = self.landmarks
        side = "left" if x > lm["midlineX"] else "right"
        S = "L" if side == "left" else "R"
        k = self.kslice_ct(z); sl = self.an[k]
        lab = int(sl[int(round(self.xy_ct(x, y)[1])), int(round(self.xy_ct(x, y)[0]))]) if 0 <= k < sl.shape[0] else 0
        name = next((n for n, v in TS.items() if v == lab), "none")
        ab, cb, ft, clb = lm["aorticBifZ"], lm[f"commonIliacBifZ_{side}"], lm[f"femurTopZ_{side}"], lm[f"clavicleBottomZ_{side}"]
        txt = f"{S} "
        if ab is not None and ft is not None and z < ab + 40 and z > ft - 120:
            # pelvis / lower abdomen
            if z >= ab: txt += "para-aortic / low retroperitoneal"
            elif cb is None or z >= cb: txt += "common iliac (between aortic and common iliac bifurcations)"
            elif z > (ft + 8):
                # internal vs external: posterior of the iliac vessels on this slice?
                m = self.label_mask(f"iliac_artery_{side}")[k]; ys, xs = np.nonzero(m)
                if len(ys):
                    yv = self.ct.TransformIndexToPhysicalPoint((0, int(ys.mean()), 0))[1]
                    txt += "internal iliac? (posterior to the iliac vessels)" if y > yv + 10 else "external iliac (along the external iliac vessels)"
                else: txt += "pelvic sidewall (no iliac vessel on this slice)"
            else:
                txt += "inguinal (at/below the femoral head)" if y < 0 or True else "pelvic"
        elif clb is not None and z > clb - 5 and abs(x - lm["midlineX"]) > 25:
            txt += "supraclavicular / low neck (above the clavicle)"
        elif abs(x - lm["midlineX"]) > 70 and clb is not None and z < clb and z > clb - 180:
            txt += "axillary (lateral chest wall)"
        else: txt += "other"
        return dict(side=S, label_at_centroid=name, text=txt)

    # ---- drawing
    def axial_fused(self, zw, crop, suv_hi=5.0):
        """CT slice nearest zw, rendered like the Augmented Workstation fusion viewport:
        CT soft tissue -160..240 HU; PET mim_hot over SUV 0..suv_hi (default 0-5 preset); PET layer at 50 % opacity, no masking.
        Returns (fused_rgb, ct_rgb, body_box, k)."""
        k = self.kslice_ct(zw); ct = self.ctarr[k].astype(np.float32)
        ref = sitk.Image((self.ct.GetSize()[0], self.ct.GetSize()[1], 1), sitk.sitkFloat32)
        ref.SetSpacing(self.ct.GetSpacing()); ref.SetDirection(self.ct.GetDirection())
        o = self.ct.TransformIndexToPhysicalPoint((0, 0, k)); ref.SetOrigin(o)
        p = sitk.Resample(sitk.Cast(self.pet, sitk.sitkFloat32), ref, sitk.Transform(), sitk.sitkLinear, 0.0, sitk.sitkFloat32)
        suv = sitk.GetArrayFromImage(p)[0] * self.suvf
        g = np.clip((ct + 160.0) / 400.0, 0, 1)                   # workstation "Soft tissue" preset: -160..240
        ctrgb = np.stack([g, g, g], -1)
        t = np.clip(suv / suv_hi, 0, 1)
        hot = mim_hot(t)
        fused = 0.5 * ctrgb + 0.5 * hot                            # FusionViewport: PET opacity 0.5 over CT opacity 1
        body = ct > -500; body = ndimage.binary_opening(body, iterations=3)
        ys, xs = np.nonzero(body)
        if len(ys): y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
        else: y0, y1, x0, x1 = 0, ct.shape[0] - 1, 0, ct.shape[1] - 1
        pad = 8
        box = [max(0, x0 - pad), max(0, y0 - pad), min(ct.shape[1], x1 + pad), min(ct.shape[0], y1 + pad)]
        return (fused * 255).astype(np.uint8), (ctrgb * 255).astype(np.uint8), box, k

    def coronal_mip(self, zlo=None, zhi=None, suv_hi=8.0):
        """PET MIP (anterior view) as uint8 gray, rows = z (head up), cols = x. Returns (img, mapping fn world->(col,row))."""
        v = self.suv; mip = v.max(axis=1)                        # [z,x]
        sp = self.pet.GetSpacing(); scale = sp[2] / sp[0]
        g = np.clip(mip / suv_hi, 0, 1) ** 0.7                   # white uptake on black, to sit on the slide
        im = Image.fromarray((g * 255).astype(np.uint8)).resize((mip.shape[1], int(mip.shape[0] * scale)), Image.BILINEAR)
        im = im.transpose(Image.FLIP_TOP_BOTTOM)
        def tomap(w):
            i = self.pet.TransformPhysicalPointToContinuousIndex((float(w[0]), float(w[1]), float(w[2])))
            return i[0], im.height - 1 - i[2] * scale
        return im.convert("RGB"), tomap

    def slice_centroid(self, L, zw):
        """Centre and size (mm) of lesion L's own outline on the PET slice nearest world z (falls back to the nearest slice that holds it)."""
        kz = int(round(self.pet.TransformPhysicalPointToContinuousIndex((0.0, 0.0, float(zw)))[2]))
        for dk in (0, 1, -1, 2, -2, 3, -3):
            k = kz + dk
            if 0 <= k < self.lab.shape[0]:
                ys, xs = np.nonzero(self.lab[k] == L["id"])
                if len(ys): break
        else: return L["centroid"][0], L["centroid"][1], max(L["extent"][0], L["extent"][1])
        sp = self.pet.GetSpacing()
        c = self.pet.TransformContinuousIndexToPhysicalPoint((float(xs.mean()), float(ys.mean()), float(k)))
        return c[0], c[1], max((xs.max() - xs.min() + 1) * sp[0], (ys.max() - ys.min() + 1) * sp[1])

    def trachea_left_wall_x(self, zw):
        """World x of the left lateral tracheal wall on the CT slice nearest zw (None if no trachea there)."""
        k = self.kslice_ct(zw); m = self.label_mask("trachea")[k]; ys, xs = np.nonzero(m)
        if not len(xs): return None
        return self.ct.TransformIndexToPhysicalPoint((int(xs.max()), 0, 0))[0] + self.ct.GetSpacing()[0] / 2

    def vessel_mip(self, zlo_w, zhi_w, hu_lo=100.0, half_mm=32.0, width_mm=150.0):
        """Coronal 'CT angiogram' of the aorto-iliac vessels: contrast-bright voxels in a slab around the labelled vessels, bone and organs removed
        with the TotalSegmentator map, keeping only components connected to the labelled aorta / iliac arteries. Returns (PIL RGB, world->(col,row))."""
        ct, an, sp = self.ctarr, self.an, self.ct.GetSpacing()
        drop = np.zeros(an.shape, bool)
        for n, v in TS.items():
            if n.startswith(("vertebrae", "sacrum", "hip", "femur", "rib", "costal", "kidney", "urinary", "liver", "spleen", "small_bowel", "colon", "duodenum", "stomach", "pancreas", "iliopsoas", "gluteus", "autochthon", "gallbladder")): drop |= an == v
        drop = ndimage.binary_dilation(drop, iterations=2)
        vm = (an == TS["aorta"]) | (an == TS["iliac_artery_left"]) | (an == TS["iliac_artery_right"])
        zlo, zhi = sorted((self.kslice_ct(zlo_w), self.kslice_ct(zhi_w)))
        ys = np.nonzero(vm[zlo:zhi + 1])[1]; yc = float(np.median(ys)); half = half_mm / sp[1]
        y0, y1 = int(max(0, yc - half)), int(min(an.shape[1], yc + half))
        sub = ((ct > hu_lo) & ~drop)[zlo:zhi + 1, y0:y1, :]
        lab, n = ndimage.label(sub); keep = np.unique(lab[vm[zlo:zhi + 1, y0:y1, :] & (lab > 0)]); keep = keep[keep > 0]
        sub2 = np.isin(lab, keep)
        hu = np.where(sub2, ct[zlo:zhi + 1, y0:y1, :], -1000).max(axis=1)
        g = np.clip((hu - 70) / 230.0, 0, 1) ** 0.7
        scale = sp[2] / sp[0]
        im = Image.fromarray((g * 255).astype(np.uint8)).resize((g.shape[1], int(g.shape[0] * scale)), Image.BILINEAR).transpose(Image.FLIP_TOP_BOTTOM).convert("RGB")
        mx = self.landmarks["midlineX"]; px = self.ct.TransformPhysicalPointToContinuousIndex((float(mx), 0.0, 0.0))[0]; w = width_mm / 2 / sp[0]
        box = (int(max(0, px - w)), 0, int(min(im.width, px + w)), im.height); im = im.crop(box)
        def tomap(wpt):
            i = self.ct.TransformPhysicalPointToContinuousIndex((float(wpt[0]), float(wpt[1]), float(wpt[2])))
            return i[0] - box[0], im.height - 1 - (i[2] - zlo) * scale
        return im, tomap

    def nearest(self, xyz):
        c=np.array(xyz,float); return min(self.lesions, key=lambda L: np.linalg.norm(np.array(L["centroid"])-c))

    def coronal_fused(self, yw, zc, height_mm, xc, width_mm, suv_hi=8.0):
        """Coronal CT slice at world y with PET fused; crop to (xc±width/2, zc±height/2). Returns PIL image + world->(col,row) fn."""
        _, j = self.xy_ct(0, yw); j = int(round(j)); ct = self.ctarr[:, j, :].astype(np.float32)   # [z,x]
        nx, ny, nz = self.ct.GetSize()
        ref = sitk.Image((nx, 1, nz), sitk.sitkFloat32); ref.SetSpacing(self.ct.GetSpacing()); ref.SetDirection(self.ct.GetDirection())
        ref.SetOrigin(self.ct.TransformIndexToPhysicalPoint((0, j, 0)))
        pp = sitk.Resample(sitk.Cast(self.pet, sitk.sitkFloat32), ref, sitk.Transform(), sitk.sitkLinear, 0.0, sitk.sitkFloat32)
        suv = sitk.GetArrayFromImage(pp)[:, 0, :] * self.suvf
        g = np.clip((ct - (40 - 200)) / 400.0, 0, 1); rgb = np.stack([g, g, g], -1)
        a = np.clip((suv - 2.0) / (suv_hi - 2.0), 0, 1)
        hot = np.stack([np.clip(a * 2.0, 0, 1), np.clip(a * 1.4 - 0.3, 0, 1), np.clip(a * 1.6 - 1.0, 0, 1)], -1)
        alpha = (a > 0).astype(np.float32)[..., None] * np.clip(0.35 + 0.65 * a, 0, 1)[..., None]
        rgb = (rgb * (1 - alpha) + hot * alpha)
        im = Image.fromarray((rgb * 255).astype(np.uint8))
        sp = self.ct.GetSpacing(); scale = sp[2] / sp[0]
        im = im.resize((im.width, int(im.height * scale)), Image.BILINEAR).transpose(Image.FLIP_TOP_BOTTOM)
        def tomap(w):
            i = self.ct.TransformPhysicalPointToContinuousIndex((float(w[0]), float(w[1]), float(w[2])))
            return i[0], im.height - 1 - i[2] * scale
        cx, cy = tomap((xc, yw, zc)); hw = width_mm / 2 / sp[0]; hh = height_mm / 2 / sp[0]
        box = (int(max(0, cx - hw)), int(max(0, cy - hh)), int(min(im.width, cx + hw)), int(min(im.height, cy + hh)))
        c = im.crop(box)
        return c, (lambda w: (tomap(w)[0] - box[0], tomap(w)[1] - box[1]))

    def provenance(self, lesions):
        return f"AutoPET {self.sid.split('_')[0]} · {self.date} · FDG · lesion {','.join(str(n) for n in lesions)}"

def vessel_diagram(nodes, W=640, Hh=900):
    """Schematic aorto-iliac tree (anterior view, patient's right on the left) with named bifurcations.
    nodes: list of (letter, branch) with branch in L-CIA, R-CIA, L-EIA, R-EIA, L-IIA, R-IIA, AO (just above the aortic bifurcation)."""
    im = Image.new("RGB", (W, Hh), (0, 0, 0)); d = ImageDraw.Draw(im)
    cx = W // 2; TEAL = (24, 163, 172); VES = (235, 90, 90); DIM = (170, 170, 170)
    y_top, y_ab, y_cb, y_bot = 70, 330, 560, 850
    wA, wC, wE, wI = 34, 24, 18, 13
    def seg(p0, p1, w): d.line([p0, p1], fill=VES, width=w); 
    for p, r in ((p, w // 2) for p, w in ()): pass
    # aorta
    seg((cx, y_top), (cx, y_ab), wA)
    pts = {}
    for sgn, side in ((-1, "R"), (1, "L")):            # viewer's left = patient's right
        cb = (cx + sgn * 120, y_cb); seg((cx, y_ab), cb, wC); pts[f"{side}-CIA"] = ((cx + cb[0]) // 2 + sgn * 0, (y_ab + y_cb) // 2)
        ei = (cx + sgn * 215, y_bot); seg(cb, ei, wE); pts[f"{side}-EIA"] = ((cb[0] + ei[0]) // 2, (y_cb + y_bot) // 2)
        ii = (cx + sgn * 95, y_cb + 190); seg(cb, ii, wI); pts[f"{side}-IIA"] = ((cb[0] + ii[0]) // 2, (y_cb + ii[1]) // 2)
        # round the joints
        for (x, y), w in ((cb, wC),): d.ellipse([x - w // 2, y - w // 2, x + w // 2, y + w // 2], fill=VES)
    d.ellipse([cx - wA // 2, y_ab - wA // 2, cx + wA // 2, y_ab + wA // 2], fill=VES)
    pts["AO"] = (cx + 40, y_ab - 70)
    # bifurcation lines + labels
    for y, lab in ((y_ab, "aortic bifurcation"), (y_cb, "common iliac bifurcation")):
        for x in range(30, W - 30, 22): d.line([(x, y), (x + 11, y)], fill=TEAL, width=3)
        d.text((W // 2, y - 34), lab, fill=TEAL, font=font(24, True), anchor="mm", stroke_width=2, stroke_fill=(0, 0, 0))
    # vessel names
    f = font(20)
    d.text((cx + 28, y_top + 60), "aorta", fill=DIM, font=f)
    d.text((cx + 150, y_ab + 70), "common iliac", fill=DIM, font=f)
    d.text((cx + 215, y_bot - 90), "external iliac", fill=DIM, font=f)
    d.text((cx + 20, y_cb + 150), "internal iliac", fill=DIM, font=f)
    d.text((40, Hh - 40), "patient's right", fill=DIM, font=font(17)); d.text((W - 170, Hh - 40), "patient's left", fill=DIM, font=font(17))
    for letter, br in nodes:
        x, y = pts[br]; draw_marker(d, (x, y), letter, r=26, f=font(34, True))
    d.text((10, 8), "Vessels", fill=(200, 200, 200), font=font(22), stroke_width=2, stroke_fill=(0, 0, 0))
    return im

CROPMM = {"pelvis": 420, "chest": 400, "axilla": 300, "neck": 260, "body": 520, "iliac": 200, "groin": 240, "vessel": 150, "pelvis300": 300}

def crop_region(img, box, S, k, crop, center=None):
    """Crop the axial to the body box, then to a square of CROPMM mm around center (world x,y) if given."""
    sp = S.ct.GetSpacing()[0]; x0, y0, x1, y1 = box
    if center is not None:
        cx, cy = S.xy_ct(center[0], center[1]); half = CROPMM[crop] / 2 / sp
        x0, x1 = int(max(0, cx - half)), int(min(img.shape[1], cx + half))
        y0, y1 = int(max(0, cy - half * 0.8)), int(min(img.shape[0], cy + half * 0.8))
    return img[y0:y1, x0:x1], (x0, y0)

LETTER_ONLY = False   # set by --letteronly: letters stay where they are, circles are not drawn
def draw_marker(d, xy, letter, r=22, col=(255, 221, 0), f=None):
    x, y = xy
    if not LETTER_ONLY: d.ellipse([x - r, y - r, x + r, y + r], outline=col, width=4)
    d.text((x + r + 6, y - r - 4), letter, fill=col, font=f or font(34, True), stroke_width=2, stroke_fill=(0, 0, 0))

def survey(sid, out, region=None):
    S = Study(sid)
    print(f"{sid}  {S.row['diagnosis']}  CT {S.row['ct']['dir']}  PET {S.row['pt']['dir']}")
    print("landmarks:", json.dumps(S.landmarks))
    keep = []
    for L in S.lesions:
        t = L["place"]["text"]
        if region and not (region in t or (region == "pelvis" and ("iliac" in t or "inguinal" in t or "aortic" in t)) or (region == "neck" and "supraclav" in t) or (region == "axilla" and "axill" in t)): pass
        print(f"  #{L['n']:2d} {L['ml']:6.1f} mL  SUVmax {L['suvmax']:5.1f}  z {L['centroid'][2]:7.1f}  xy ({L['centroid'][0]:6.1f},{L['centroid'][1]:6.1f})  ext {L['extent']}  at:{L['place']['label_at_centroid']:<22s} {t}")
        keep.append(L)
    # sheet: coronal MIP + axial per lesion (max 12)
    mip, tomap = S.coronal_mip()
    mip = mip.resize((int(mip.width * 1.6), int(mip.height * 1.6)))
    d = ImageDraw.Draw(mip); f = font(22, True)
    for L in keep:
        cx, cy = tomap(L["centroid"]); cx *= 1.6; cy *= 1.6
        d.ellipse([cx - 9, cy - 9, cx + 9, cy + 9], outline=(220, 40, 40), width=3); d.text((cx + 11, cy - 12), str(L["n"]), fill=(220, 40, 40), font=f)
    tiles = []
    for L in keep[:12]:
        img, _, box, k = S.axial_fused(L["zdraw"], "body")
        sub, (ox, oy) = crop_region(img, box, S, k, "body")
        im = Image.fromarray(sub); dd = ImageDraw.Draw(im)
        px, py = S.xy_ct(L["centroid"][0], L["centroid"][1]); draw_marker(dd, (px - ox, py - oy), str(L["n"]), r=16, f=font(26, True))
        dd.text((6, 4), f"#{L['n']} z {L['zdraw']} · {L['ml']:.1f} mL · SUV {L['suvmax']:.1f}", fill=(255, 255, 255), font=font(18), stroke_width=2, stroke_fill=(0, 0, 0))
        dd.text((6, im.height - 24), L["place"]["text"][:60], fill=(255, 221, 0), font=font(16), stroke_width=2, stroke_fill=(0, 0, 0))
        tiles.append(im.resize((400, int(400 * im.height / im.width))))
    th = max([t.height for t in tiles] + [1]); cols = 3; rows = math.ceil(len(tiles) / cols)
    W = mip.width + 10 + cols * 405; Hh = max(mip.height, rows * (th + 5) + 30)
    sheet = Image.new("RGB", (W, Hh), (20, 20, 20)); sheet.paste(mip, (0, 0))
    for i, t in enumerate(tiles): sheet.paste(t, (mip.width + 10 + (i % cols) * 405, 30 + (i // cols) * (th + 5)))
    ImageDraw.Draw(sheet).text((mip.width + 12, 4), f"{sid} {S.row['diagnosis']} {S.date}", fill=(255, 255, 255), font=font(20, True))
    os.makedirs(out, exist_ok=True); p = os.path.join(out, f"{sid}-sheet.png"); sheet.save(p)
    json.dump(dict(sid=sid, diagnosis=S.row["diagnosis"], studyDir=S.row["studyDir"], ct=S.row["ct"]["dir"], pt=S.row["pt"]["dir"], seg=S.row["seg"], landmarks=S.landmarks, lesions=S.lesions), open(os.path.join(out, f"{sid}-lesions.json"), "w"), indent=1)
    print("wrote", p)

def figure(sid, out, crop, a=None, b=None, coronal=False, title=None, nolabel=False, letters=("A", "B"), zoom=1.0, extra=None, suv_hi=5.0, coronalct=None, lines=None, zforce=None, tline=False, vmip=False, vmip_hu=100.0, vlabels=None, vdiag=None):
    S = Study(sid)
    byn = {L["n"]: L for L in S.lesions}
    def res(v):
        if v is None: return None
        if isinstance(v, str) and "," in v: return S.nearest([float(t) for t in v.split(",")])
        return byn[int(v)]
    picks = [(letters[0], res(a))] if a else []
    if b: picks.append((letters[1], res(b)))
    for let, L in picks: print(f"{let} = lesion #{L['n']} {L['ml']:.1f} mL SUV {L['suvmax']:.1f} centroid {L['centroid']} -> {L['place']['text']}")
    panels = []
    # one axial per distinct draw-slice; if A and B are within 6 mm, share a slice
    groups = []
    if zforce is not None: groups = [dict(z=float(zforce), items=list(picks))]
    for let, L in ([] if zforce is not None else picks):
        for g in groups:
            if abs(g["z"] - L["zdraw"]) <= 6: g["items"].append((let, L)); break
        else: groups.append(dict(z=L["zdraw"], items=[(let, L)]))
    rows = []
    for g in groups:
        z = float(np.mean([L["zdraw"] for _, L in g["items"]]))
        fused, ctimg, box, k = S.axial_fused(z, crop, suv_hi=suv_hi)
        center = g["items"][0][1]["centroid"] if crop != "body" else None
        if crop in ("pelvis", "chest"): center = (S.landmarks["midlineX"], center[1]) if center else None
        row = []
        for img, tag in ((ctimg, "CT"), (fused, "Fused")):
            sub, (ox, oy) = crop_region(img, box, S, k, crop, center)
            im = Image.fromarray(sub)
            if zoom != 1.0: im = im.resize((int(im.width * zoom), int(im.height * zoom)), Image.LANCZOS)
            d = ImageDraw.Draw(im)
            if not nolabel:
                for let, L in g["items"]:
                    cx, cy, ext = S.slice_centroid(L, z)
                    px, py = S.xy_ct(cx, cy)
                    r = max(16, int(ext / 2 / S.ct.GetSpacing()[0] * zoom) + 8)
                    draw_marker(d, ((px - ox) * zoom, (py - oy) * zoom), let, r=r)
            if tline:
                xw = S.trachea_left_wall_x(z)
                if xw is not None:
                    px = (S.xy_ct(xw, 0)[0] - ox) * zoom
                    d.line([(px, 0), (px, im.height)], fill=(24, 163, 172), width=3)
                    d.text((px + 8, im.height - 60), "left tracheal\nwall", fill=(24, 163, 172), font=font(20, True), stroke_width=2, stroke_fill=(0, 0, 0))
            d.text((10, 8), tag, fill=(200, 200, 200), font=font(22), stroke_width=2, stroke_fill=(0, 0, 0))
            row.append(im)
        rows.append(row)
    vpanel = None
    if vdiag:
        vpanel = vessel_diagram([(t.split("=")[0], t.split("=")[1]) for t in vdiag.split(";") if t])
    if vmip and vpanel is None:
        zs = [L["zdraw"] for _, L in picks]; ab = S.landmarks["aorticBifZ"] or float(np.mean(zs))
        im, vmap = S.vessel_mip(min(min(zs) - 45, ab - 100), max(max(zs) + 45, ab + 55), hu_lo=vmip_hu)
        im = im.resize((im.width * 2, im.height * 2), Image.LANCZOS); d = ImageDraw.Draw(im)
        for let, L in picks:
            cx, cy = [v * 2 for v in vmap(L["centroid"])]; r = max(14, L["extent"][0] / 2 / S.ct.GetSpacing()[0] * 2 + 8)
            d.line([(0, cy), (im.width, cy)], fill=(24, 163, 172), width=2)
            if not nolabel: draw_marker(d, (cx, cy), let, r=int(r), f=font(30, True))
        for zl, txt in (vlabels or []):
            _, py = [v * 2 for v in vmap((S.landmarks["midlineX"], 0.0, float(zl)))]
            d.line([(im.width - 150, py), (im.width - 8, py)], fill=(24, 163, 172), width=3)
            lines_txt = txt.split("\\n")
            for i, t in enumerate(lines_txt): d.text((im.width - 150, py - 24 * len(lines_txt) - 2 + i * 24), t, fill=(24, 163, 172), font=font(21, True), stroke_width=2, stroke_fill=(0, 0, 0))
        d.text((10, 8), "Vessels", fill=(200, 200, 200), font=font(22), stroke_width=2, stroke_fill=(0, 0, 0))
        vpanel = im
    panels = []   # legacy single-row path keeps working for the coronal options below
    if coronalct is not None:
        # coronalct = "y" world (mm) of the coronal plane, or "auto" = mean y of the iliac arteries (pelvis) / trachea (chest); panel spans the picked lesions in z
        zs = [L["zdraw"] for _, L in picks]; zc = float(np.mean(zs)) if zs else 0.0
        if coronalct == "auto":
            name = "trachea" if crop in ("chest", "neck", "axilla") else "iliac_artery_left"
            m = S.label_mask(name) | (S.label_mask("iliac_artery_right") if name.startswith("iliac") else False)
            zlo, zhi = S.kslice_ct(min(zs) - 20), S.kslice_ct(max(zs) + 20)
            sub = m[min(zlo, zhi):max(zlo, zhi) + 1]; ys = np.nonzero(sub)[1]
            coronalct = S.ct.TransformIndexToPhysicalPoint((0, int(np.median(ys)), 0))[1] if len(ys) else 0.0
            print("coronal plane y =", round(float(coronalct), 1))
        hgt_mm = max(220.0, (max(zs) - min(zs)) + 160.0) if zs else 260.0
        c, cmap = S.coronal_fused(float(coronalct), zc, hgt_mm, S.landmarks["midlineX"], hgt_mm * 0.75, suv_hi=suv_hi)
        d = ImageDraw.Draw(c)
        if not nolabel:
            for let, L in picks:
                px, py = cmap(L["centroid"]); draw_marker(d, (px, py), let, r=16, f=font(28, True))
        for ln in (lines or []):   # ("z", value, label): horizontal reference line at world z
            if ln[0] == "z":
                _, py = cmap((S.landmarks["midlineX"], float(coronalct), float(ln[1])))
                d.line([(0, py), (c.width, py)], fill=(24, 163, 172), width=3)
                d.text((6, py - 22), ln[2], fill=(24, 163, 172), font=font(18, True), stroke_width=2, stroke_fill=(0, 0, 0))
        hgt = max(p.height for p in panels) if panels else c.height
        c = c.resize((int(c.width * hgt / c.height), hgt), Image.LANCZOS)
        panels.insert(0, c)
    if coronal:
        mip, tomap = S.coronal_mip(suv_hi=suv_hi)
        zs = [L["zdraw"] for _, L in picks]; zc = np.mean(zs) if zs else 0
        ch = CROPMM[crop] / S.pet.GetSpacing()[0]; cw = ch * 0.6
        cx, cy = tomap((S.landmarks["midlineX"], 0, zc))
        box = (int(max(0, cx - cw / 2)), int(max(0, cy - ch / 2)), int(min(mip.width, cx + cw / 2)), int(min(mip.height, cy + ch / 2)))
        c = mip.crop(box); c = c.resize((c.width * 3, c.height * 3), Image.LANCZOS); d = ImageDraw.Draw(c)
        tomap0 = tomap; tomap = lambda w: (tomap0(w)[0] * 3 - box[0] * 3 + 0, tomap0(w)[1] * 3 - box[1] * 3); box = (0, 0, 0, 0)
        if not nolabel:
            for let, L in picks:
                px, py = tomap(L["centroid"]); draw_marker(d, (px - box[0], py - box[1]), let, r=20, f=font(30, True))
        hgt = max(p.height for p in panels) if panels else 500
        c = c.resize((int(c.width * hgt / c.height), hgt), Image.LANCZOS)
        panels.insert(0, c)
    gap = 12
    if panels and rows: rows[0] = panels + rows[0]
    rw = [sum(p.width for p in r) + gap * (len(r) - 1) for r in rows]; rh = [max(p.height for p in r) for r in rows]
    W = max(rw); Hrows = sum(rh) + gap * (len(rows) - 1)
    xoff = 0
    if vpanel is not None:
        vpanel = vpanel.resize((int(vpanel.width * Hrows / vpanel.height), Hrows), Image.LANCZOS); xoff = vpanel.width + gap
    Hh = Hrows + 34
    fig = Image.new("RGB", (W + xoff, Hh), (0, 0, 0)); y = 0
    if vpanel is not None: fig.paste(vpanel, (0, 0))
    for r, h in zip(rows, rh):
        x = xoff + (W - (sum(p.width for p in r) + gap * (len(r) - 1))) // 2
        for p in r: fig.paste(p, (x, y)); x += p.width + gap
        y += h + gap
    d = ImageDraw.Draw(fig)
    if title: d.text((8, 6), title, fill=(255, 255, 255), font=font(22, True), stroke_width=2, stroke_fill=(0, 0, 0))
    d.text((8, Hh - 26), S.provenance([L["n"] for _, L in picks]), fill=(170, 170, 170), font=font(15))
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True); fig.save(out); print("wrote", out, fig.size)
    side = dict(sid=sid, diagnosis=S.row["diagnosis"], studyDir=S.row["studyDir"], ct=S.row["ct"]["dir"], pt=S.row["pt"]["dir"], seg=S.row["seg"], crop=crop, lesions={let: L for let, L in picks}, landmarks=S.landmarks)
    json.dump(side, open(os.path.splitext(out)[0] + ".json", "w"), indent=1)

if __name__ == "__main__":
    a = sys.argv[1:]
    def opt(n, d=None): return a[a.index(n) + 1] if n in a else d
    if a[0] == "survey": survey(a[1], opt("--out", "."), opt("--region"))
    elif a[0] == "figure":
        LETTER_ONLY = "--letteronly" in a
        lines = [("z", float(v.split(":")[0]), v.split(":")[1]) for v in opt("--zline", "").split(";") if v]
        figure(a[1], opt("--out"), opt("--crop", "body"), a=opt("--a"), b=opt("--b"), coronal="--coronal" in a, title=opt("--title"), nolabel="--nolabel" in a, zoom=float(opt("--zoom", "1")), suv_hi=float(opt("--suvhi", "5")), coronalct=opt("--coronalct"), lines=lines, letters=tuple(opt("--letters", "A,B").split(",")), zforce=opt("--z"), tline="--tline" in a, vmip="--vmip" in a, vmip_hu=float(opt("--vmiphu", "100")), vlabels=[(float(v.split(":")[0]), v.split(":")[1]) for v in opt("--vlabel", "").split(";") if v], vdiag=opt("--vdiag"))
    elif a[0] == "stack":
        # stack <sid> --lesion n --crop pelvis --out file [--above 30 --below 12 --step 4] : CT-only axial thumbnails from above the lesion down through it, lesion outlined on each slice it touches
        S = Study(a[1]); byn = {L["n"]: L for L in S.lesions}; L = byn[int(opt("--lesion"))] if opt("--lesion") else S.nearest([float(v) for v in opt("--near").split(",")]); crop = opt("--crop", "pelvis")
        print(f"lesion #{L['n']} {L['ml']:.1f} mL SUV {L['suvmax']:.1f} centroid {L['centroid']} zdraw {L['zdraw']}")
        above, below, step = float(opt("--above", "30")), float(opt("--below", "12")), float(opt("--step", "4"))
        zs = np.arange(L["zdraw"] + above, L["zdraw"] - below - 0.1, -step); tiles = []
        for z in zs:
            fused, ctimg, box, k = S.axial_fused(z, crop); center = (S.landmarks["midlineX"], L["centroid"][1]) if crop not in ("iliac", "groin", "vessel") else (L["centroid"][0], L["centroid"][1])
            sub, (ox, oy) = crop_region(ctimg if "--fused" not in a else fused, box, S, k, crop, center); im = Image.fromarray(sub); d = ImageDraw.Draw(im)
            kz = int(round(S.pet.TransformPhysicalPointToContinuousIndex((0.0, 0.0, float(z)))[2]))
            if 0 <= kz < S.lab.shape[0] and (S.lab[kz] == L["id"]).any():
                cx, cy, ext = S.slice_centroid(L, z); px, py = S.xy_ct(cx, cy); draw_marker(d, (px - ox, py - oy), "", r=max(14, int(ext / 2 / S.ct.GetSpacing()[0]) + 8))
            for nm, col in (() if "--nohatch" in a else (("aorta", (255, 90, 90)), ("iliac_artery_left", (90, 160, 255)), ("iliac_artery_right", (90, 255, 160)))):
                ys, xs = np.nonzero(S.label_mask(nm)[k])
                for yy, xx in zip(ys[::3], xs[::3]): d.point((xx - ox, yy - oy), fill=col)
            d.text((6, 4), f"z {z:.0f}  ({z - L['zdraw']:+.0f} mm)", fill=(255, 255, 255), font=font(20, True), stroke_width=2, stroke_fill=(0, 0, 0))
            sc = float(opt("--scale", "0.6")); tiles.append(im.resize((int(im.width * sc), int(im.height * sc)), Image.LANCZOS))
        cols = int(opt("--cols", "4")); w, h = tiles[0].size; rows_n = (len(tiles) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * w + (cols - 1) * 6, rows_n * h + (rows_n - 1) * 6 + 30), (0, 0, 0))
        for i, t in enumerate(tiles): sheet.paste(t, ((i % cols) * (w + 6), 30 + (i // cols) * (h + 6)))
        ImageDraw.Draw(sheet).text((6, 4), f"{a[1]} lesion #{L['n']} {L['ml']:.1f} mL SUV {L['suvmax']:.1f} {L['place']['text']}  landmarks {json.dumps(S.landmarks)}", fill=(255, 255, 255), font=font(16))
        sheet.save(opt("--out")); print("wrote", opt("--out"), sheet.size)
    elif a[0] == "compose":
        # compose --out file row1.png row2.png ... : stack row images vertically (each keeps its own provenance line); sidecars merged
        files = [f for f in a[1:] if f.endswith(".png") and f != opt("--out")]; ims = [Image.open(f).convert("RGB") for f in files]
        W = max(i.width for i in ims); gap = 12; Hh = sum(i.height for i in ims) + gap * (len(ims) - 1)
        fig = Image.new("RGB", (W, Hh), (0, 0, 0)); y = 0
        for i in ims: fig.paste(i, ((W - i.width) // 2, y)); y += i.height + gap
        fig.save(opt("--out")); print("wrote", opt("--out"), fig.size)
        rows = []
        for f in files:
            j = os.path.splitext(f)[0] + ".json"
            if os.path.exists(j): rows.append(json.load(open(j)))
        json.dump(dict(rows=rows), open(os.path.splitext(opt("--out"))[0] + ".json", "w"), indent=1)
    elif a[0] == "axial":
        # axial <sid> --z Z --out file [--crop chest] : one fused axial at z, every lesion within 8 mm numbered
        S = Study(a[1]); z = float(opt("--z")); crop = opt("--crop", "body")
        img, _, box, k = S.axial_fused(z, crop, suv_hi=float(opt("--suvhi", "5")))
        near = [L for L in S.lesions if abs(L["centroid"][2] - z) <= 8 or (L["centroid"][2] - L["extent"][2] / 2 <= z <= L["centroid"][2] + L["extent"][2] / 2)]
        center = (S.landmarks["midlineX"], near[0]["centroid"][1]) if near and crop != "body" else None
        sub, (ox, oy) = crop_region(img, box, S, k, crop, center); im = Image.fromarray(sub); d = ImageDraw.Draw(im)
        for L in near:
            px, py = S.xy_ct(L["centroid"][0], L["centroid"][1]); draw_marker(d, (px - ox, py - oy), str(L["n"]), r=16, f=font(26, True))
            print(f"#{L['n']} {L['ml']:.1f} mL SUV {L['suvmax']:.1f} centroid {L['centroid']} {L['place']['text']}")
        d.text((6, 4), f"{a[1]} z {z}", fill=(255, 255, 255), font=font(18), stroke_width=2, stroke_fill=(0, 0, 0))
        im.save(opt("--out")); print("wrote", opt("--out"), im.size)
