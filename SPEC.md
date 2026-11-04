# Hot Seat — spec for Claude Code

Build a small, reusable audience-response site for resident lectures. One engine, one JSON config per lecture. Presenter runs it on a laptop projected to a screen; residents vote on phones via a QR code. Nothing here is a product; it is a teaching tool for ~50 people in one room.

## Stack (keep it this simple)

- Static HTML/CSS/JS, no framework, no build step. Two pages: `present.html` and `vote.html`. Shared `app.js`, `style.css`.
- Firebase: Realtime Database + Auth (anonymous for voters, email/password for the presenter). Free tier.
- Hosted on GitHub Pages. Library scripts from CDN only (Firebase compat SDK, a QR code library). Pin versions.
- Lecture content lives in `lectures/<id>.json`, never in HTML or JS. Rosters live there too.

## Lecture config (`lectures/<id>.json`)

```json
{
  "id": "nodal-2026-11",
  "title": "Disease-Specific Reporting: Why Nodal Nomenclature Matters",
  "roster": { "R1": ["..."], "R2": ["..."], "R3": ["..."], "R4": ["..."] },
  "questions": [
    {
      "id": "pre1",
      "kind": "pretest",
      "pairedWith": "post1",
      "eligible": ["R3", "R4"],
      "image": "img/common-iliac.png",
      "stem": "Prostate cancer. This node is best classified as:",
      "options": ["N1", "M1a", "M1b", "Not applicable"],
      "correct": 1,
      "explain": "One or two sentences shown after reveal."
    }
  ]
}
```

- `kind` is one of `pretest`, `quick`, `posttest`. Default `eligible` by kind: pretest → R3,R4; quick → R1; posttest → R1–R4. A question may override.
- `pairedWith` links a posttest question to its pretest twin for scoring.
- Images are files in `img/`; the same image may be reused across questions.

## Firebase data model

```
/sessions/{sessionId}
  lectureId, startedAt, presenterUid
  current: { questionId | null, revealed: bool, open: bool }
  hotSeat: { name, class, answer } | null
  called: { "R1|Name": true, ... }          // no-repeat ledger

/votes/{sessionId}/{questionId}/{deviceId}
  { choice: 0-3, class: "R2", ts }

/devices/{sessionId}/{deviceId}
  { class: "R2" }                            // set once on join
```

`deviceId` is a random token the vote page generates on first load and keeps in localStorage. Good enough for residents; not a security boundary.

## Security rules

- `/sessions/*`: read by anyone signed in (anonymous counts); write only by `presenterUid`.
- `/votes/{s}/{q}/{d}`: write only if `auth.uid == d`'s owner (store `uid` alongside and match), one choice per device per question (allow overwrite until `current.open` is false). No read for anonymous users. Read for presenter.
- `/devices/{s}/{d}`: same pattern.
- Presenter signs in with email/password once; the vote page uses anonymous auth automatically.

## Participant page (`vote.html?s=<sessionId>`)

1. On load: anonymous sign-in, create or load deviceId.
2. First visit in a session: pick class (R1–R4) once; stored in `/devices` and localStorage.
3. Listen to `/sessions/{s}/current`. When a question opens, show the stem and A–D buttons (no image needed; it is on the screen). Tap locks the choice and shows "Answered." Allow changing while `open` is true.
4. Never show results or the correct answer on the phone. Between questions show "Waiting."
5. Must work on iOS Safari and Android Chrome over hospital wifi. Big buttons, no scrolling.

## Presenter page (`present.html`)

Sign in → choose lecture from `lectures/index.json` → **Start session** creates `/sessions/{id}` and shows the QR (link to `vote.html?s=…`) full screen with the join count. Then a question runner, one question per screen:

- Image left (large), stem and options right. Live "n answered" counter visible at all times; histogram hidden until Reveal.
- **Hot seat** block: eligible classes from the question (editable via checkboxes), **Pick** button with a short name-cycling animation, no repeats within the session until a pool is exhausted (then auto-reset that pool and say so). Picked name writes to `hotSeat` and `called`.
- Hot seat answer: A–D buttons the presenter taps after the resident answers aloud. Shows "Name answered B."
- **Reveal**: closes voting, draws the histogram (counts and %), marks the correct option, shows the hot seat's letter against it, shows `explain`.
- Navigation: previous / next question, jump list in a sidebar. Keyboard: Space = pick, A–D = hot seat answer, R = reveal, → / ← = next/prev, Esc = clear hot seat.
- Reopen a question if needed (presenter can set `open` back to true).

Keep the presenter layout readable from the back of a room: minimum 28px body text on the question screen, name in the hot seat block at least 96px.

## Summary screen (after the last question)

- Pre vs post: for each `pairedWith` pair, % correct on pre and post, overall and by class. Pair by deviceId.
- Per-question table: n, % correct, hot seat correct yes/no.
- **Export CSV** of raw votes (sessionId, questionId, deviceId, class, choice, correct, ts).

## Non-goals

No accounts for residents. No free-text questions. No image upload UI (images go in the repo). No framework, no bundler, no server code. Don't build an admin UI for editing lectures; the JSON is the editor.

## Acceptance checklist

- [ ] Two phones vote on the same question; presenter sees n=2 before reveal and the histogram after.
- [ ] Refreshing a phone mid-lecture keeps its class and prior answers.
- [ ] Presenter refresh mid-lecture restores the current question, called list, and hot seat.
- [ ] Picker never repeats a name until the eligible pool is exhausted.
- [ ] Anonymous users cannot read `/votes` (verify in rules simulator).
- [ ] A second lecture JSON runs with zero code changes.
- [ ] CSV export opens in Excel with one row per vote.

## Build order

1. Firebase project, auth providers, rules, `firebaseConfig` in `config.js` (gitignored template committed as `config.example.js`).
2. `vote.html` against a hand-made session document.
3. `present.html` session start + QR + question runner, no picker.
4. Picker and hot seat (port from existing selector; logic is already written).
5. Reveal, histogram, summary, CSV.
6. Deploy to GitHub Pages; dry run on hospital wifi.
