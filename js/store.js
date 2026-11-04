// Store abstraction. Two backends with the same surface:
//   MockStore     - in-memory + BroadcastChannel, works with no backend (open present.html and vote.html in two tabs)
//   FirebaseStore - Realtime Database, used when config.js defines firebaseConfig
//
// Surface (all async unless noted):
//   signInPresenter(email, password) -> uid
//   signInAnonymous() -> uid
//   createSession(lectureId, presenterUid) -> sessionId
//   getSession(sessionId) -> session | null
//   onSession(sessionId, cb)          cb(session) on every change; returns unsubscribe
//   updateSession(sessionId, patch)
//   setDevice(sessionId, deviceId, {class, uid})
//   getDevice(sessionId, deviceId) -> {class} | null
//   setVote(sessionId, questionId, deviceId, {choice, class, uid})
//   onVotes(sessionId, questionId, cb)  cb({deviceId: vote}) ; returns unsubscribe   (presenter only)
//   onMyVote(sessionId, questionId, deviceId, cb)  cb(vote|null) ; returns unsubscribe   (vote page)
//   getAllVotes(sessionId) -> {questionId: {deviceId: vote}}
//
// Session shape:
//   { lectureId, startedAt, presenterUid,
//     current: { questionId|null, open: bool, revealed: bool },
//     hotSeat: { name, cls, answer|null } | null,
//     called: { "R1|Name": true } }

(function (global) {
  const now = () => Date.now();

  // ---------- Mock ----------
  class MockStore {
    constructor() {
      this.kind = "mock";
      const raw = (() => { try { return JSON.parse(localStorage.getItem("hs_mock") || "{}"); } catch (e) { return {}; } })();
      this.data = Object.assign({ sessions: {}, votes: {}, devices: {} }, raw);
      this.listeners = { session: {}, votes: {} };
      this.chan = ("BroadcastChannel" in global) ? new BroadcastChannel("hs_mock") : null;
      if (this.chan) this.chan.onmessage = (e) => { this.data = e.data; this._fanout(); };
    }
    _persist() {
      try { localStorage.setItem("hs_mock", JSON.stringify(this.data)); } catch (e) {}
      if (this.chan) this.chan.postMessage(this.data);
      this._fanout();
    }
    _fanout() {
      for (const sid in this.listeners.session) this.listeners.session[sid].forEach(cb => cb(this.data.sessions[sid] || null));
      for (const key in this.listeners.votes) {
        const [sid, qid] = key.split("::");
        const v = (this.data.votes[sid] || {})[qid] || {};
        this.listeners.votes[key].forEach(cb => cb(v));
      }
    }
    async signInPresenter() { return "mock-presenter"; }
    async signInAnonymous() {
      let uid = null; try { uid = localStorage.getItem("hs_mock_uid"); } catch (e) {}
      if (!uid) { uid = "anon-" + Math.random().toString(36).slice(2, 10); try { localStorage.setItem("hs_mock_uid", uid); } catch (e) {} }
      return uid;
    }
    async createSession(lectureId, presenterUid) {
      const sid = Math.random().toString(36).slice(2, 8).toUpperCase();
      this.data.sessions[sid] = { lectureId, presenterUid, startedAt: now(), current: { questionId: null, open: false, revealed: false }, hotSeat: null, called: {} };
      this.data.votes[sid] = {}; this.data.devices[sid] = {};
      this._persist(); return sid;
    }
    async getSession(sid) { return this.data.sessions[sid] || null; }
    onSession(sid, cb) {
      (this.listeners.session[sid] ||= []).push(cb);
      cb(this.data.sessions[sid] || null);
      return () => { this.listeners.session[sid] = (this.listeners.session[sid] || []).filter(f => f !== cb); };
    }
    async updateSession(sid, patch) {
      const s = this.data.sessions[sid]; if (!s) return;
      deepMerge(s, patch); this._persist();
    }
    async setDevice(sid, did, rec) { (this.data.devices[sid] ||= {})[did] = rec; this._persist(); }
    async getDevice(sid, did) { return ((this.data.devices[sid] || {})[did]) || null; }
    async setVote(sid, qid, did, vote) {
      ((this.data.votes[sid] ||= {})[qid] ||= {})[did] = Object.assign({ ts: now() }, vote); this._persist();
    }
    onVotes(sid, qid, cb) {
      const key = sid + "::" + qid;
      (this.listeners.votes[key] ||= []).push(cb);
      cb(((this.data.votes[sid] || {})[qid]) || {});
      return () => { this.listeners.votes[key] = (this.listeners.votes[key] || []).filter(f => f !== cb); };
    }
    onMyVote(sid, qid, did, cb) { return this.onVotes(sid, qid, v => cb((v || {})[did] || null)); }
    async getAllVotes(sid) { return this.data.votes[sid] || {}; }
    async countDevices(sid) { return Object.keys(this.data.devices[sid] || {}).length; }
    onDeviceCount(sid, cb) { return this.onSession(sid, () => cb(Object.keys(this.data.devices[sid] || {}).length)); }
  }

  // ---------- Firebase (compat SDK, loaded via <script> tags) ----------
  class FirebaseStore {
    constructor(app) {
      this.kind = "firebase";
      this.auth = app.auth();
      this.db = app.database();
    }
    async signInPresenter(email, password) {
      const cred = await this.auth.signInWithEmailAndPassword(email, password);
      return cred.user.uid;
    }
    async signInAnonymous() {
      if (this.auth.currentUser) return this.auth.currentUser.uid;
      const cred = await this.auth.signInAnonymously();
      return cred.user.uid;
    }
    async createSession(lectureId, presenterUid) {
      const sid = Math.random().toString(36).slice(2, 8).toUpperCase();
      await this.db.ref("sessions/" + sid).set({
        lectureId, presenterUid, startedAt: firebase.database.ServerValue.TIMESTAMP,
        current: { questionId: null, open: false, revealed: false }, hotSeat: null, called: {}
      });
      return sid;
    }
    async getSession(sid) { const s = await this.db.ref("sessions/" + sid).get(); return s.exists() ? s.val() : null; }
    onSession(sid, cb) {
      const ref = this.db.ref("sessions/" + sid);
      const h = ref.on("value", s => cb(s.exists() ? s.val() : null));
      return () => ref.off("value", h);
    }
    async updateSession(sid, patch) {
      // flatten to multi-path update so nested keys merge rather than replace
      const flat = {};
      (function walk(obj, path) {
        for (const k in obj) {
          const v = obj[k], p = path ? path + "/" + k : k;
          if (v && typeof v === "object" && !Array.isArray(v) && Object.keys(v).length && !("__set" in v)) walk(v, p);
          else flat[p] = (v && v.__set !== undefined) ? v.__set : v;
        }
      })(patch, "");
      await this.db.ref("sessions/" + sid).update(flat);
    }
    async setDevice(sid, did, rec) { await this.db.ref(`devices/${sid}/${did}`).set(rec); }
    async getDevice(sid, did) { const s = await this.db.ref(`devices/${sid}/${did}`).get(); return s.exists() ? s.val() : null; }
    async setVote(sid, qid, did, vote) {
      await this.db.ref(`votes/${sid}/${qid}/${did}`).set(Object.assign({ ts: firebase.database.ServerValue.TIMESTAMP }, vote));
    }
    onVotes(sid, qid, cb) {
      const ref = this.db.ref(`votes/${sid}/${qid}`);
      const h = ref.on("value", s => cb(s.exists() ? s.val() : {}));
      return () => ref.off("value", h);
    }
    onMyVote(sid, qid, did, cb) {
      // Anonymous users may read only their own vote record, so listen to that path, not the whole question.
      const ref = this.db.ref(`votes/${sid}/${qid}/${did}`);
      const h = ref.on("value", s => cb(s.exists() ? s.val() : null));
      return () => ref.off("value", h);
    }
    async getAllVotes(sid) { const s = await this.db.ref("votes/" + sid).get(); return s.exists() ? s.val() : {}; }
    async countDevices(sid) { const s = await this.db.ref("devices/" + sid).get(); return s.exists() ? Object.keys(s.val()).length : 0; }
    onDeviceCount(sid, cb) {
      const ref = this.db.ref("devices/" + sid);
      const h = ref.on("value", s => cb(s.exists() ? Object.keys(s.val()).length : 0));
      return () => ref.off("value", h);
    }
  }

  function deepMerge(target, patch) {
    for (const k in patch) {
      const v = patch[k];
      if (v && typeof v === "object" && !Array.isArray(v) && "__set" in v) { target[k] = v.__set; continue; }
      if (v && typeof v === "object" && !Array.isArray(v) && target[k] && typeof target[k] === "object") deepMerge(target[k], v);
      else target[k] = v;
    }
  }

  // Factory: Firebase if config.js supplied a config and the SDK loaded, else mock.
  function makeStore() {
    if (global.firebaseConfig && global.firebase && global.firebase.initializeApp) {
      const app = global.firebase.apps.length ? global.firebase.app() : global.firebase.initializeApp(global.firebaseConfig);
      return new FirebaseStore(app);
    }
    return new MockStore();
  }

  // A lecture is an ordered list of items: {type:"slide", ...} or {type:"question", ...}.
  // Older files with a plain `questions` array are upgraded in place. `questions` is always
  // derived from items so scoring, pairing, the summary and the CSV ignore slides.
  function normalizeLecture(l) {
    if (!Array.isArray(l.items)) l.items = (l.questions || []).map(q => Object.assign({ type: "question" }, q));
    l.items.forEach((it, i) => { if (!it.type) it.type = "question"; if (!it.id) it.id = "s" + (i + 1); });
    l.questions = l.items.filter(it => it.type === "question");
    l.eligibleByKind = l.eligibleByKind || {};
    return l;
  }

  global.HotSeatStore = { makeStore, MockStore, FirebaseStore, normalizeLecture };
})(window);
