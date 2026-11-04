# NCCN crops for the nodal nomenclature lecture

Task for Claude Code: for each PDF below, find the page described, crop the named box or table to a PNG, and save it to `img/nccn/` with the filename given. Add a thin caption bar at the bottom of each PNG with the guideline name, version, and page code read from the PDF footer (e.g. "NCCN Prostate Cancer v2.2026 · PROS-8"). Use 2x resolution so it projects cleanly. If a page code has shifted in the downloaded version, search the PDF text for the phrases listed and use the page that contains them.

The PDFs are downloaded by hand from NCCN.org (free account, Guidelines for Physicians). Place them in `nccn-pdf/` (gitignored). Do not commit the PDFs. Check NCCN's permissions policy before any use outside an internal teaching conference; if screenshots are not permitted, redraw each box as a simple diagram with the same text and attribute it.

## 1. Prostate Cancer → `img/nccn/prostate-n1.png` and `img/nccn/prostate-m1.png`

- Page: the regional (N1) treatment page. Search text: "Regional (N1)" or "node positive" near "EBRT + ADT". Crop the decision box showing N1 → EBRT to prostate and pelvic nodes + ADT (± abiraterone).
- Page: the first metastatic castration-sensitive page. Search text: "Metastatic (M1)" and "castration-sensitive" and "low-volume". Crop the box that lists systemic options and, if on the same page, the note offering EBRT to the primary for low-volume disease.
- Also useful if space: the staging table row defining regional nodes (search "true pelvis" or "below the bifurcation of the common iliac").

## 2. Non-Small Cell Lung Cancer → `img/nccn/lung-stage3.png`

- Page: stage III workup/treatment where N2 and N3 branch. Search text: "T1–3, N2" and "N3". Crop the box or boxes so both branches are visible: N2 (surgery possible after induction / "resectable") and N3 (definitive chemoradiation). If they are on two pages, make two PNGs: `lung-n2.png`, `lung-n3.png`.
- Optional: the staging table (search "N2a" and "N2b") → `img/nccn/lung-staging.png`.

## 3. Anal Carcinoma → `img/nccn/anal-nodes.png`

- Page: the staging table. Search text: "N1a" and "inguinal, mesorectal, or internal iliac". Crop the N-category rows (N0, N1a, N1b, N1c).

## 4. Rectal Cancer → `img/nccn/rectal-nodes.png`

- Page: the staging table or the imaging principles page that defines regional nodes. Search text: "regional lymph nodes" together with "mesorectal" / "internal iliac" and "external iliac" / "inguinal" listed as non-regional or distant. Crop the definition. If the clearest statement is in a footnote, crop the footnote with the table header above it for context.
- Present anal and rectal side by side on the slide; keep both crops the same height.

## 5. Breast Cancer → `img/nccn/breast-workup.png`

- Page: the invasive breast cancer workup page where clinical stage routes patients. Search text: "cN3" or "inoperable" and "preoperative systemic therapy". Crop so the operable branch (cT1–3, cN0–1) and the locally advanced / inoperable branch are both visible.
- Optional: the staging table row for N3a (search "infraclavicular" and "N3a") → `img/nccn/breast-n3a.png`.

## 6. B-Cell Lymphomas (DLBCL section) → two PNGs

- `img/nccn/lymphoma-staging.png`: the Lugano staging table. Search text: "Lugano" and "Stage I" "Stage II" "one nodal region" "both sides of the diaphragm". Crop the whole table. The point of the slide is that no row distinguishes regional from distant nodes.
- `img/nccn/dlbcl-firstline.png`: the DLBCL first-line page that branches on stage I–II versus III–IV. Search text: "Stage I, II" and "Stage III, IV" near "R-CHOP" or "Pola-R-CHP". Crop so both branches are visible; the slide shows that the two branches reach nearly the same regimen.

## Output check

After cropping, print a table: filename · PDF · page code from footer · pixel size. Flag any crop where the search phrases were not found so it can be located by hand.


## Output (done 2026-11-03)

Crops rendered at 200 dpi with a caption bar. Pages were found by footer code after reading each page; several codes differ from the guesses above because the downloaded versions are newer (Prostate v1.2027, NSCL v9.2026, Anal v3.2026, Rectal v2.2026, Breast v9.2026, B-Cell v4.2026).

| file | PDF | page code | px |
|---|---|---|---|
| prostate-n1.png | prostate.pdf | PROS-7 | 2097x867 |
| prostate-m1.png | prostate.pdf | PROS-14 | 2097x804 |
| prostate-staging.png | prostate.pdf | ST-1 (AJCC 8th ed.) | 1086x547 |
| lung-stage3.png | nscl.pdf | NSCL-8 | 2097x570 |
| lung-n2.png | nscl.pdf | NSCL-10 | 2097x1084 |
| lung-n3.png | nscl.pdf | NSCL-13 | 2097x975 |
| lung-staging.png | nscl.pdf | ST-3 (AJCC 9th ed.) | 2097x524 |
| anal-nodes.png | anal.pdf | ST-1 (AJCC 9th ed.) | 1234x444 |
| rectal-nodes.png | rectal.pdf | REC-A 4 of 5 | 2097x713 |
| breast-workup.png | breast.pdf | BINV-12 | 2097x698 |
| breast-preop-criteria.png | breast.pdf | BINV-L 1 of 2 | 1006x615 |
| breast-n3a.png | breast.pdf | ST-2 (AJCC 8th ed.) | 1049x793 |
| lymphoma-staging.png | b-cell.pdf | ST-5 (Lugano) | 1149x855 |
| dlbcl-firstline.png | b-cell.pdf | BCEL-3 | 2097x884 |

Notes
- Prostate: the N1 page is PROS-7 (not PROS-8). The "EBRT to the primary for low-volume disease" note is no longer on the mCSPC page; PROS-14 is the metastatic pathway. No "true pelvis" definition in this version; ST-1 gives N1 = regional, M1a = nonregional nodes.
- Rectal: the staging table (ST-1) does not name which nodes are regional. The definition is on REC-A 4 of 5 (pelvic MRI reporting): internal iliac/obturator/mesorectal are locoregional; common and external iliac and retroperitoneal are distant; inguinal is locoregional only below the dentate line.
- Breast: cN3 → preoperative systemic therapy is stated on BINV-L 1 of 2 (`breast-preop-criteria.png`), not on the workup page. BINV-12 shows only the operable/inoperable split.
- Lung: `lung-stage3.png` (NSCL-8) shows both branches; NSCL-10 and NSCL-13 are the N2 and N3 detail pages.
- anal-nodes.png and rectal-nodes.png are different heights (444 vs 713 px); scale on the slide.
