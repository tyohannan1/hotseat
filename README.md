# Hot Seat

Audience-response pages for resident lectures. One engine, one JSON per lecture. Presenter runs `present.html` on the projected laptop; residents open `vote.html` from a QR code on their phones.

No framework, no build. Static files + Firebase Realtime Database.

## Try it right now (no server)

Open `present.html` in a browser (double-click works; a local server is better for image loading: `python3 -m http.server` then http://localhost:8000/present.html). Without `config.js` it runs in **local test mode**: votes live in this browser only and sync between tabs. Open `vote.html?s=<code>` in a second tab to vote. Everything works except that other devices can't join.

## Go live (30–45 min, once)

1. **Firebase project.** console.firebase.google.com → Add project (name it anything, no Analytics).
2. **Realtime Database.** Build → Realtime Database → Create → pick a region → start in locked mode.
3. **Auth.** Build → Authentication → Get started → Sign-in method: enable **Anonymous** and **Email/Password**. Then Users → Add user: your email + a password. This is the presenter login.
4. **Web app config.** Project settings (gear) → Your apps → Web (`</>`) → register → copy the `firebaseConfig` object. `cp config.example.js config.js` and paste it in.
5. **Rules.** Realtime Database → Rules tab → paste the contents of `database.rules.json` → Publish.
6. **Deploy.** Push this folder to a GitHub repo → Settings → Pages → deploy from `main`. Your URL is `https://<you>.github.io/<repo>/present.html`. (`config.js` is gitignored; add it to the repo deliberately if you want Pages to serve it, or keep the presenter laptop's local copy. The web config is not secret; the rules are the security boundary.)
7. **Dry run.** Open `present.html`, sign in, start a session, scan the QR with two phones on hospital wifi. Open Notes, press `F`, and walk the whole deck on the real projector from the back of the room.

## Running a lecture

- **Start new session** → QR lobby. Residents scan, pick their year once.
- **Begin** → first question. Each question screen:
  - Image left, stem + options right. Options show bars only after Reveal.
  - **Hot seat** block: eligible years are preset by question kind (pretest R3–R4, quick check R1, posttest none) and editable with the checkboxes. **Pick** cycles names; no repeats until a pool is exhausted. Tap A–D after the resident answers aloud.
  - **Open voting / Close voting / Reveal.** Reveal closes voting, draws bars, marks the correct option and the hot seat's letter, shows the explanation. Pretest questions have no Reveal: their answers appear only in the Summary, beside the posttest.
- Keyboard: `Space` pick · `A–D` hot seat answer · `O` open · `X` close · `R` reveal · `←`/`→` prev/next · `Z` zoom the image full-bleed · `F` presentation mode · `V` pre/post reveal · `Esc` close zoom, else clear hot seat.
- **Present** (header button or `F`): full screen, no header or jump bar, larger type. The projector shows only the slide; the control bar fades until you hover.
- **Notes** (header button): opens `notes.html` in a second window for the laptop screen. It follows the session: current item, its speaker notes, what is projected, next item, live answer count, hot seat, the correct letter, and a clock against `runOfShow` in the lecture JSON (red when you reach a segment more than a minute late). Put the laptop on *extended* display, presenter window on the projector, notes window on the laptop.
- **Pre/post** (header button, `V`, or Next after the last item): one pretest/posttest pair per screen, pretest bars beside posttest bars, correct row marked, the one-line reason. Pretest and posttest questions have no per-question Reveal; this screen is the only reveal. Then Summary.
- **Summary** (header button, or Next after the last question): pre vs post per pair and overall, by year, paired improvement by device, per-question table, **Download CSV**.
- **Resume**: if the presenter page is refreshed, enter the session code to pick up where you were. Phones keep their year and prior answers.

## Smoke test

`npm install` once (and `npx playwright install chromium`), then `npm test`. It starts a local server, opens a presenter tab and a phone tab, walks slides and questions, votes, picks a hot seat, reveals a quick check, resumes after a refresh, and checks the summary. Local test mode only; it does not touch Firebase.

## Writing a lecture

`lectures/<id>.json`, then add it to `lectures/index.json`. See `lectures/nodal-2026-11.json`. The full prose and speaker notes for that lecture are in `LECTURE.md`; the JSON holds only what is projected.

A lecture is an ordered `items` list. Each item is a teaching slide or a question, and the presenter steps through them in order with the arrow keys.

- **Slide** `{ "type": "slide", "id", "eyebrow", "title", "body", "image", "caption", "nccn", "table", "notes" }`. `notes` (same line format as `body`) shows only in the notes window; `questionNotes` per kind and `lobbyNotes` cover questions and the QR screen. `runOfShow` is `[{label, minutes, from: itemId}]`. `body` is an array of lines: `- ` bullets, `# ` subheads, `> ` pull quotes, `**bold**`, `*italic*`. `image` (left) and `nccn` (one path or an array of crops from `img/nccn/`) are optional. `table` is `{ "head": [...], "rows": [[...]] }`; set `"tableFirst": true` to put it above the body. Phones show "Waiting" while a slide is up.
- **Question** `{ "type": "question", ... }`: the fields below, unchanged. Only question items count for the summary and the CSV.
- Older files with a plain `questions` array still load.

- `roster`: four arrays, one name per line. Edit every July.
- `sharedStem` / `sharedOptions`: used by any question that omits its own `stem` / `options`.
- Each question: `type: "question"`, `id`, `kind` (`pretest` | `quick` | `posttest`), `hotSeat` (`afterPoll` | `beforePoll` | `none`), `image` (path in `img/`, or `null`), `imageCaption`, `disease` (shown above the shared stem), optional `stem` and `options` (overrides), `correct` (0-based index), `explain`, optional `eligible` (overrides `eligibleByKind`), `pairedWith` (links pre/post).
- Posttest questions are copies of the pretest questions with new ids and `kind: "posttest"`.

Images are not in this repo. Drop PNGs into `img/` with the filenames the JSON expects; a missing image shows a labeled placeholder rather than breaking the slide.

## Files

- `present.html` — presenter (projector)
- `notes.html` — speaker notes window (laptop screen)
- `vote.html` — participant
- `js/store.js` — data layer; `MockStore` (local) and `FirebaseStore` behind one interface
- `css/style.css`
- `database.rules.json` — paste into Firebase
- `config.example.js` → `config.js`
- `lectures/` — one JSON per lecture + `index.json`
- `LECTURE.md` — the nodal nomenclature talk, full prose and run of show
- `tests/` + `playwright.config.mjs` — smoke test
- `img/` — your images

## Data

`sessions/{sid}`: current question, open/revealed flags, hot seat, called list.
`devices/{sid}/{deviceId}`: year.
`votes/{sid}/{qid}/{deviceId}`: choice, year, timestamp.

Device id is a random token in the phone's localStorage. One vote per device per question, changeable while voting is open. Anonymous users can read only their own vote and device; the presenter (email login, session creator) reads everything.

## Images and graphics (2026-11-04)

Slide images are rendered from AutoPET FDG studies with `tools/nodeshots.py` (run with `~/AutoPET-model/.venv/bin/python -I`). Provenance for every image is in `img/SOURCES.md` and in a sidecar `.json` next to each PNG; the notes window shows the study id under the speaker notes.

- `survey <sid> --out dir`: list a study's lesions with a proposed placement; writes a contact sheet.
- `figure <sid> --crop pelvis300 --a 4 --b 6 --vmip --out img/x.png`: CT + fused axial pair per node (A, B), circles centred on the node outline; `--vmip` adds the bone-free coronal vessel panel (`--vmiphu 120` for studies with bright veins or bowel); `--tline` draws the left tracheal wall; `--z` forces one slice; `--nolabel` drops the circles.
- `stack <sid> --near x,y,z --crop iliac --above 36 --below 8`: CT thumbnails through a node for choosing slices (`--nohatch` hides the vessel tint).
- `compose --out img/x.png row1.png row2.png`: stack two single-study rows (used for the two-patient pelvis images).
- `tools/pelvis_scan.py` and `tools/inguinal_scan.py`: scan all studies for nodes just below the aortic or common iliac bifurcation, or in the groin, from the eval JSON and the anatomy maps.
- `tools/dxgen.py <outdir>`: the SVG diagrams in `img/dx/` (lymphoma regions map, four boundary lines, 2×2 composite), drawn for this talk; slides `op-regions`, `c1-line` … `c4-line` show them before each case image and quick check.

The anatomy maps in `~/AutoPET-model/anatomy/` have a flipped y axis relative to the CT; `nodeshots.py` resamples them onto the CT grid.
