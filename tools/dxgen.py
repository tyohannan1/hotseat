"""Schematic graphics for the Hot Seat lecture: the lymphoma region map and the four carcinoma boundary lines.
Writes SVGs into <out>. Deck palette: navy slide background, light ink, teal accents, gold boundary line."""
import sys, os
OUT = sys.argv[1] if len(sys.argv) > 1 else "."
INK = "#e8eef5"; DIM = "#9fb3c8"; TEAL = "#18A3AC"; GOLD = "#FFDD00"; RED = "#ff5a5a"; NODE = "#ffb000"; MUTE = "#5d7288"
FONT = "font-family='Helvetica Neue, Helvetica, Arial, sans-serif'"

def svg(w, h, body, title=None):
    t = f"<text x='{w/2}' y='46' text-anchor='middle' font-size='34' font-weight='700' fill='{INK}' {FONT}>{title}</text>" if title else ""
    return f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {w} {h}' width='{w}' height='{h}' {FONT}>\n{t}\n{body}\n</svg>\n"

def T(x, y, s, size=22, fill=INK, anchor="start", weight=400, italic=False):
    st = " font-style='italic'" if italic else ""
    return f"<text x='{x}' y='{y}' font-size='{size}' fill='{fill}' text-anchor='{anchor}' font-weight='{weight}'{st}>{s}</text>"

def node(x, y, r=9, fill=NODE): return f"<circle cx='{x}' cy='{y}' r='{r}' fill='{fill}' stroke='#000' stroke-width='1.5'/>"
def line(x1, y1, x2, y2, col=INK, w=3, dash=None):
    d = f" stroke-dasharray='{dash}'" if dash else ""
    return f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y2}' stroke='{col}' stroke-width='{w}' stroke-linecap='round'{d}/>"
def path(d, col=INK, w=3, fill="none", dash=None, op=1):
    ds = f" stroke-dasharray='{dash}'" if dash else ""
    return f"<path d='{d}' stroke='{col}' stroke-width='{w}' fill='{fill}' stroke-linejoin='round' stroke-linecap='round'{ds} opacity='{op}'/>"

# ------------------------------------------------------------------ lymphoma regions
def regions(w=1060, h=900, standalone=True):
    """Lugano / Ann Arbor regions: body silhouette and the 17 region names used by the PET/CT workbench. Nothing else."""
    b = []
    cx = 530
    b.append(T(cx, 60, "Lugano / Ann Arbor regions", 36, INK, "middle", 700))
    # body silhouette
    b.append(f"<circle cx='{cx}' cy='{150}' r='46' fill='none' stroke='{MUTE}' stroke-width='3'/>")
    b.append(path(f"M{cx-30} 193 L{cx-30} 215 L{cx-150} 240 L{cx-215} 495 L{cx-170} 505 L{cx-125} 325 L{cx-125} 545 L{cx-135} 855 L{cx-75} 855 L{cx-35} 585 L{cx+35} 585 L{cx+75} 855 L{cx+135} 855 L{cx+125} 545 L{cx+125} 325 L{cx+170} 505 L{cx+215} 495 L{cx+150} 240 L{cx+30} 215 L{cx+30} 193 Z", MUTE, 3))
    # diaphragm
    b.append(line(cx-130, 425, cx+130, 425, TEAL, 3, "10 8"))
    b.append(T(cx+228, 432, "diaphragm", 18, TEAL, "start", 400, True))
    # (x, y, rx, ry, label, label side); patient's right on the viewer's left
    R = [
        (cx, 178, 26, 14, "Waldeyer's ring", "r"),
        (cx-62, 212, 26, 18, "Right neck", "l"), (cx+62, 212, 26, 18, "Left neck", "r"),
        (cx-85, 262, 22, 12, "Right infraclavicular", "l"), (cx+85, 262, 22, 12, "Left infraclavicular", "r"),
        (cx-135, 300, 22, 22, "Right axillary", "l"), (cx+135, 300, 22, 22, "Left axillary", "r"),
        (cx, 305, 30, 42, "Mediastinal", "r2"),
        (cx-48, 352, 16, 16, "Right hilar", "l"), (cx+48, 352, 16, 16, "Left hilar", "r"),
        (cx+70, 468, 28, 22, "Spleen", "r"),
        (cx, 505, 20, 40, "Para-aortic", "r2"),
        (cx-40, 535, 26, 20, "Mesenteric", "l"),
        (cx-55, 598, 18, 26, "Right iliac", "l"), (cx+55, 598, 18, 26, "Left iliac", "r"),
        (cx-75, 668, 20, 20, "Right inguinal", "l"), (cx+75, 668, 20, 20, "Left inguinal", "r"),
    ]
    for x, y, rx, ry, lab, side in R:
        b.append(f"<ellipse cx='{x}' cy='{y}' rx='{rx}' ry='{ry}' fill='{NODE}' fill-opacity='0.3' stroke='{NODE}' stroke-width='2.5'/>")
        if side == "l": b.append(line(x-rx-4, y, cx-222, y, DIM, 1.5)); b.append(T(cx-228, y+7, lab, 21, INK, "end"))
        elif side == "r": b.append(line(x+rx+4, y, cx+222, y, DIM, 1.5)); b.append(T(cx+228, y+7, lab, 21, INK, "start"))
        else:  # central structure: label to the right, line drops below the paired labels
            yy = y + 95 if lab == "Mediastinal" else y + 50
            b.append(line(x+rx+4, yy, cx+222, yy, DIM, 1.5)); b.append(line(x+rx+4, y, x+rx+4, yy, DIM, 1.5)); b.append(T(cx+228, yy+7, lab, 21, INK, "start"))
    return svg(w, h, "\n".join(b), None)

# ------------------------------------------------------------------ pelvis: common iliac bifurcation
def pelvis(w=1400, h=900, standalone=True):
    b = []
    cx = 520
    # aorta and iliac tree (coronal)
    b.append(path(f"M{cx-22} 90 L{cx-22} 300 Q{cx-22} 330 {cx-50} 350 L{cx-150} 470 Q{cx-165} 488 {cx-168} 510 L{cx-200} 720", RED, 14))
    b.append(path(f"M{cx+22} 90 L{cx+22} 300 Q{cx+22} 330 {cx+50} 350 L{cx+150} 470 Q{cx+165} 488 {cx+168} 510 L{cx+200} 720", RED, 14))
    b.append(f"<rect x='{cx-22}' y='90' width='44' height='215' fill='{RED}'/>")
    # internal iliacs
    b.append(path(f"M{cx-150} 470 L{cx-120} 560 L{cx-110} 640", RED, 9))
    b.append(path(f"M{cx+150} 470 L{cx+120} 560 L{cx+110} 640", RED, 9))
    # labels of vessels
    b.append(T(cx+60, 200, "aorta", 22, DIM)); b.append(T(cx+115, 420, "common iliac", 22, DIM)); b.append(T(cx+205, 640, "external iliac", 22, DIM)); b.append(T(cx+40, 620, "internal iliac", 22, DIM))
    # inguinal ligament
    b.append(line(cx-290, 690, cx-150, 735, TEAL, 3, "10 8")); b.append(line(cx+290, 690, cx+150, 735, TEAL, 3, "10 8"))
    b.append(T(cx-300, 680, "inguinal ligament", 20, TEAL, "start", 400, True))
    # aortic bifurcation and common iliac bifurcation lines
    b.append(line(cx-330, 330, cx+330, 330, DIM, 2, "6 8")); b.append(T(cx-340, 322, "aortic bifurcation", 20, DIM, "end")); b.append(T(cx-340, 344, "(L4)", 20, DIM, "end"))
    b.append(line(cx-330, 470, cx+330, 470, GOLD, 5)); b.append(T(cx-340, 452, "common iliac", 24, GOLD, "end", 700)); b.append(T(cx-340, 480, "bifurcation", 24, GOLD, "end", 700)); b.append(T(cx-340, 506, "the edge of the pelvis", 18, GOLD, "end", 400, True))
    # nodes
    b.append(node(cx-60, 250)); b.append(T(cx-80, 257, "para-aortic", 20, INK, "end"))
    b.append(node(cx-110, 410)); b.append(T(cx-130, 417, "common iliac", 20, INK, "end"))
    b.append(node(cx-200, 600)); b.append(T(cx-220, 607, "external iliac", 20, INK, "end"))
    b.append(node(cx-95, 560)); b.append(T(cx-75, 548, "internal iliac", 20, INK, "start"))
    b.append(node(cx-225, 770)); b.append(T(cx-245, 777, "inguinal", 20, INK, "end"))
    # right column: consequences
    x0 = 920
    b.append(T(x0, 150, "Prostate", 30, INK, "start", 700))
    b.append(T(x0, 200, "Below the line: N1, pelvic.", 24)); b.append(T(x0, 232, "Radiated with the prostate, curative.", 22, DIM))
    b.append(T(x0, 285, "Above the line: M1a, metastatic.", 24)); b.append(T(x0, 317, "Hormones and drugs lead.", 22, DIM))
    b.append(T(x0, 400, "Bladder", 30, INK, "start", 700)); b.append(T(x0, 450, "Common iliac is still regional (N3).", 24)); b.append(T(x0, 482, "The line does not matter here.", 22, DIM))
    b.append(T(x0, 565, "Lymphoma", 30, INK, "start", 700)); b.append(T(x0, 615, "One iliac chain = one region.", 24)); b.append(T(x0, 647, "“Right iliac” and stop.", 22, DIM))
    b.append(T(x0, 740, "Report: the vessel the node sits on, and which side", 22, TEAL)); b.append(T(x0, 770, "of the bifurcation.", 22, TEAL))
    return svg(w, h, "\n".join(b), "Line 1: the common iliac bifurcation" if standalone else None)

# ------------------------------------------------------------------ trachea: left lateral wall
def trachea(w=1400, h=900, standalone=True):
    b = []
    cx, cy = 470, 430
    # axial schematic at the lower paratracheal level: anterior at top, patient's right on viewer's left
    b.append(T(cx, 110, "anterior", 20, DIM, "middle", 400, True)); b.append(T(120, cy+8, "R", 26, DIM, "middle", 700)); b.append(T(820, cy+8, "L", 26, DIM, "middle", 700))
    # vertebra
    b.append(f"<ellipse cx='{cx}' cy='{cy+230}' rx='95' ry='60' fill='none' stroke='{MUTE}' stroke-width='3'/>")
    # esophagus
    b.append(f"<ellipse cx='{cx+15}' cy='{cy+110}' rx='40' ry='26' fill='none' stroke='{MUTE}' stroke-width='3'/>"); b.append(T(cx+15, cy+117, "esophagus", 16, DIM, "middle"))
    # trachea
    b.append(f"<circle cx='{cx}' cy='{cy}' r='70' fill='none' stroke='{INK}' stroke-width='5'/>"); b.append(T(cx, cy+8, "trachea", 20, INK, "middle"))
    # SVC and aorta
    b.append(f"<circle cx='{cx-150}' cy='{cy-40}' r='40' fill='none' stroke='{MUTE}' stroke-width='3'/>"); b.append(T(cx-150, cy-33, "SVC", 18, DIM, "middle"))
    b.append(f"<circle cx='{cx+170}' cy='{cy+10}' r='48' fill='none' stroke='{MUTE}' stroke-width='3'/>"); b.append(T(cx+170, cy+17, "aorta", 18, DIM, "middle"))
    b.append(f"<circle cx='{cx-40}' cy='{cy-150}' r='48' fill='none' stroke='{MUTE}' stroke-width='3'/>"); b.append(T(cx-40, cy-143, "asc. aorta", 16, DIM, "middle"))
    # midline (dashed) and the left lateral wall (gold)
    b.append(line(cx, cy-260, cx, cy+320, DIM, 2, "8 8")); b.append(T(cx+8, cy-265, "midline", 18, DIM))
    b.append(line(cx+70, cy-260, cx+70, cy+320, GOLD, 5)); b.append(T(cx+80, cy-265, "left lateral wall of the trachea", 22, GOLD, "start", 700))
    # station zones
    b.append(T(cx-115, cy-100, "2R / 4R", 24, INK, "middle", 700)); b.append(T(cx+135, cy-100, "2L / 4L", 24, INK, "middle", 700))
    b.append(f"<rect x='{cx-260}' y='{cy-230}' width='{330}' height='{300}' fill='{NODE}' fill-opacity='0.06' stroke='none'/>")
    b.append(f"<rect x='{cx+72}' y='{cy-230}' width='{200}' height='{300}' fill='{TEAL}' fill-opacity='0.08' stroke='none'/>")
    # nodes: one just left of midline but medial to the wall, one lateral to the wall
    b.append(node(cx+40, cy-95)); b.append(T(cx+40, cy-115, "still 4R", 20, NODE, "middle", 700))
    b.append(node(cx+120, cy-20)); b.append(T(cx+120, cy-40, "4L", 20, NODE, "middle", 700))
    b.append(node(cx-110, cy-30)); b.append(T(cx-110, cy-50, "4R", 20, NODE, "middle", 700))
    # right column
    x0 = 920
    b.append(T(x0, 150, "Lung cancer", 30, INK, "start", 700))
    b.append(T(x0, 200, "Same side as the tumor: N2.", 24)); b.append(T(x0, 232, "Surgery may still be on the table.", 22, DIM))
    b.append(T(x0, 285, "Opposite side: N3.", 24)); b.append(T(x0, 317, "Surgery off; chemoradiation.", 22, DIM))
    b.append(T(x0, 370, "The side is set by the left tracheal wall,", 22, INK)); b.append(T(x0, 400, "not the midline. Station 7 is midline", 22, INK)); b.append(T(x0, 430, "and always counts as N2.", 22, INK))
    b.append(T(x0, 520, "Lymphoma", 30, INK, "start", 700)); b.append(T(x0, 570, "The whole mediastinum is one region.", 24)); b.append(T(x0, 602, "Right or left changes nothing; size does.", 22, DIM))
    b.append(T(x0, 700, "2 vs 4: above or below the top of the aortic arch", 20, TEAL)); b.append(T(x0, 728, "(on the right, the innominate vein crossing).", 20, TEAL))
    b.append(T(x0, 790, "Report: the station number, not the position.", 22, TEAL))
    return svg(w, h, "\n".join(b), "Line 2: the left lateral wall of the trachea" if standalone else None)

# ------------------------------------------------------------------ anorectal: dentate line and mesorectal fascia
def anorectal(w=1400, h=900, standalone=True):
    b = []
    cx = 430
    # rectum and anal canal (coronal), mesorectal fascia envelope
    b.append(path(f"M{cx-55} 150 L{cx-60} 520 L{cx-35} 640 L{cx-25} 720 L{cx+25} 720 L{cx+35} 640 L{cx+60} 520 L{cx+55} 150", INK, 5))
    b.append(path(f"M{cx-150} 140 Q{cx-175} 400 {cx-110} 600 L{cx-60} 650", TEAL, 3, dash="10 8")); b.append(path(f"M{cx+150} 140 Q{cx+175} 400 {cx+110} 600 L{cx+60} 650", TEAL, 3, dash="10 8"))
    b.append(T(cx-160, 130, "mesorectal fascia", 20, TEAL, "end", 400, True))
    b.append(T(cx, 340, "rectum", 22, DIM, "middle")); b.append(T(cx, 690, "anal", 18, DIM, "middle")); b.append(T(cx, 710, "canal", 18, DIM, "middle"))
    # dentate line
    b.append(line(cx-100, 640, cx+100, 640, GOLD, 5)); b.append(T(cx+110, 646, "dentate line", 24, GOLD, "start", 700))
    # levator / pelvic floor
    b.append(line(cx-230, 560, cx-60, 630, MUTE, 4)); b.append(line(cx+230, 560, cx+60, 630, MUTE, 4)); b.append(T(cx-240, 552, "levator", 18, DIM, "end"));
    # nodes
    b.append(node(cx-105, 300)); b.append(T(cx-125, 307, "mesorectal", 20, INK, "end"))
    b.append(node(cx-200, 380)); b.append(T(cx-220, 387, "internal iliac / obturator", 20, INK, "end"))
    b.append(node(cx-250, 250)); b.append(T(cx-270, 257, "external iliac", 20, INK, "end"))
    b.append(node(cx-215, 760)); b.append(T(cx-235, 767, "inguinal", 20, INK, "end"))
    b.append(node(cx+215, 760)); b.append(node(cx+200, 380)); b.append(node(cx+105, 300))
    # right: two tables
    x0 = 820
    b.append(T(x0, 150, "Anal canal SCC", 30, INK, "start", 700))
    for i, r in enumerate(["Regional: inguinal, mesorectal, internal iliac (N1a)", "Regional: external iliac (N1b)", "All of them are already inside the radiation field."]):
        b.append(T(x0, 200 + i * 34, r, 22, INK if i < 2 else DIM))
    b.append(T(x0, 350, "Rectal adenocarcinoma", 30, INK, "start", 700))
    for i, r in enumerate(["Regional: mesorectal, internal iliac, obturator", "Distant (M1): external iliac, common iliac", "Inguinal: regional only if the tumor reaches", "   below the dentate line; otherwise M1"]):
        b.append(T(x0, 400 + i * 34, r, 22, INK))
    b.append(T(x0, 580, "Lymphoma", 30, INK, "start", 700)); b.append(T(x0, 630, "Pelvic and inguinal are different regions,", 24)); b.append(T(x0, 662, "but one node in either is the same stage.", 24))
    b.append(T(x0, 760, "Report: name the node group, and whether the primary", 22, TEAL)); b.append(T(x0, 790, "sits above or below the dentate line.", 22, TEAL))
    return svg(w, h, "\n".join(b), "Line 3: the dentate line and the mesorectal fascia" if standalone else None)

# ------------------------------------------------------------------ axilla: pectoralis minor
def axilla(w=1400, h=900, standalone=True):
    b = []
    # axial schematic of the left axilla: anterior up, medial (sternum) on the left of the drawing
    b.append(T(200, 120, "medial (sternum)", 20, DIM, "start", 400, True)); b.append(T(760, 120, "lateral (arm)", 20, DIM, "end", 400, True)); b.append(T(480, 100, "anterior", 20, DIM, "middle", 400, True))
    # chest wall (ribs) curve
    b.append(path("M120 560 Q420 470 760 560", MUTE, 8)); b.append(T(440, 700, "chest wall", 18, DIM, "middle"))
    # pectoralis major (anterior, broad)
    b.append(path("M130 300 Q450 180 780 330", INK, 14, op=0.9)); b.append(T(450, 230, "pectoralis major", 20, INK, "middle"))
    # pectoralis minor (oblique: coracoid lateral-anterior to ribs 3-5 medial-posterior)
    b.append(path("M300 470 L620 330", GOLD, 12)); b.append(T(470, 380, "pectoralis minor", 22, GOLD, "middle", 700))
    b.append(T(640, 322, "coracoid", 16, DIM, "start"))
    # borders of pec minor projected
    b.append(line(620, 150, 620, 560, GOLD, 2, "8 8")); b.append(line(300, 150, 300, 560, GOLD, 2, "8 8"))
    # axillary vein
    b.append(f"<ellipse cx='520' cy='440' rx='34' ry='20' fill='none' stroke='{TEAL}' stroke-width='3'/>"); b.append(T(520, 447, "ax. vein", 14, TEAL, "middle"))
    # level labels
    b.append(T(700, 610, "Level I", 26, INK, "middle", 700)); b.append(T(700, 638, "lateral to pec minor", 18, DIM, "middle"))
    b.append(T(460, 610, "Level II", 26, INK, "middle", 700)); b.append(T(460, 638, "behind pec minor", 18, DIM, "middle"))
    b.append(T(210, 610, "Level III", 26, INK, "middle", 700)); b.append(T(210, 638, "medial to pec minor", 18, DIM, "middle"))
    b.append(T(460, 300, "Rotter's (interpectoral)", 20, INK, "middle")); b.append(node(460, 325))
    b.append(node(700, 450)); b.append(node(430, 440)); b.append(node(210, 430)); b.append(node(150, 350)); b.append(T(150, 380, "internal mammary", 16, DIM, "middle"))
    # right column
    x0 = 880
    b.append(T(x0, 150, "Breast cancer", 30, INK, "start", 700))
    b.append(T(x0, 200, "Level I or II: the surgeon's axilla.", 24)); b.append(T(x0, 232, "Sentinel node or dissection.", 22, DIM))
    b.append(T(x0, 285, "Level III (infraclavicular): cN3a.", 24)); b.append(T(x0, 317, "Systemic therapy before any surgery.", 22, DIM))
    b.append(T(x0, 370, "Rotter's: not reached by a standard", 22, INK)); b.append(T(x0, 400, "dissection; radiation covers it only if named.", 22, INK))
    b.append(T(x0, 450, "Internal mammary: cN3b. Supraclavicular: cN3c.", 22, INK))
    b.append(T(x0, 540, "Lymphoma", 30, INK, "start", 700)); b.append(T(x0, 590, "Axillary/pectoral is one region;", 24)); b.append(T(x0, 622, "infraclavicular is another. Count regions.", 24))
    b.append(T(x0, 720, "Report: the level by its relation to pectoralis minor,", 22, TEAL)); b.append(T(x0, 750, "and say Rotter's, internal mammary and", 22, TEAL)); b.append(T(x0, 780, "supraclavicular by name.", 22, TEAL))
    return svg(w, h, "\n".join(b), "Line 4: the pectoralis minor" if standalone else None)

def composite():
    # 2x2 of the four lines, each as a nested svg
    parts = []
    for i, fn in enumerate([pelvis, trachea, anorectal, axilla]):
        inner = fn(standalone=True)
        inner = inner.replace("<svg xmlns='http://www.w3.org/2000/svg' ", f"<svg x='{(i % 2) * 1400}' y='{(i // 2) * 900}' ")
        parts.append(inner)
    return f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 2800 1800' width='2800' height='1800'>\n" + "\n".join(parts) + "\n</svg>\n"

os.makedirs(OUT, exist_ok=True)
for name, fn in [("regions-lymphoma", regions), ("line1-pelvis", pelvis), ("line2-trachea", trachea), ("line3-anorectal", anorectal), ("line4-axilla", axilla)]:
    open(os.path.join(OUT, name + ".svg"), "w").write(fn(standalone=False))
open(os.path.join(OUT, "four-lines.svg"), "w").write(composite())
print("wrote", os.listdir(OUT))
