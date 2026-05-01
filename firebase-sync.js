// Helper de sincronización Firebase Firestore para apps Maxifer.
// Espeja un set de claves de localStorage a documentos de Firestore.
// Last-write-wins por timestamp del cliente.
//
// Uso desde el HTML:
//   <script>window.MAXIFER_SYNC_NAMESPACE = 'compras';</script>
//   <script type="module" src="./firebase-sync.js"></script>
//
//   <script>
//   window.addEventListener('maxifer-sync-ready', () => {
//     window.MaxiferSync.start(['MI_KEY_1', 'MI_KEY_2'], {
//       statusEl: document.getElementById('syncStatus'),
//       onRemote: (key, value) => { /* re-render */ }
//     });
//   });
//   </script>

import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.13.0/firebase-app.js';
import {
  getFirestore,
  doc,
  setDoc,
  getDoc,
  onSnapshot
} from 'https://www.gstatic.com/firebasejs/10.13.0/firebase-firestore.js';

const firebaseConfig = {
  apiKey: "AIzaSyAtfElcZuiip27qeU3tZzQf6CsCMZhrTV0",
  authDomain: "presupuestador-maxifer.firebaseapp.com",
  projectId: "presupuestador-maxifer",
  storageBucket: "presupuestador-maxifer.firebasestorage.app",
  messagingSenderId: "1049921095923",
  appId: "1:1049921095923:web:8956008db3b58b33004f86",
  measurementId: "G-LMXG9MDKGC"
};

const TS_SUFFIX = '__ts';
const PUSH_DEBOUNCE_MS = 800;

const tsKey = (key) => key + TS_SUFFIX;

function readLocal(key) {
  const v = localStorage.getItem(key);
  if (v === null) return null;
  try { return JSON.parse(v); } catch { return v; }
}

function readLocalTs(key) {
  return parseInt(localStorage.getItem(tsKey(key)) || '0', 10);
}

function writeLocal(key, value, ts) {
  // Bypassea el patch de setItem para no re-disparar push.
  Storage.prototype._origSetItem.call(localStorage, key, JSON.stringify(value));
  Storage.prototype._origSetItem.call(localStorage, tsKey(key), String(ts));
}

class FirebaseSync {
  constructor(namespace) {
    this.namespace = namespace;
    this.app = initializeApp(firebaseConfig);
    this.db = getFirestore(this.app);
    this.synced = new Set();
    this.unsubs = new Map();
    this.pushTimers = new Map();
    this.statusEl = null;
    this.ready = false;
    this.onRemote = null;
  }

  _docRef(key) {
    return doc(this.db, 'apps', this.namespace, 'state', key);
  }

  _setStatus(msg, type) {
    if (!this.statusEl) return;
    this.statusEl.textContent = msg;
    this.statusEl.dataset.syncType = type || 'info';
  }

  async start(keys, opts = {}) {
    this.statusEl = opts.statusEl || null;
    this.onRemote = opts.onRemote || null;
    this._patchLocalStorage();
    keys.forEach(k => this.synced.add(k));

    // Si hay datos locales sin timestamp (escritos antes de que el patch
    // estuviera instalado, o antes de agregar Firebase), les ponemos
    // ts=Date.now() para que la reconciliación los considere "frescos"
    // y no los pise con el remoto.
    keys.forEach(k => {
      if (localStorage.getItem(k) !== null && !localStorage.getItem(tsKey(k))) {
        Storage.prototype._origSetItem.call(localStorage, tsKey(k), String(Date.now()));
      }
    });

    this._setStatus('☁️ Sincronizando...', 'sync');

    // Reconciliación inicial
    await Promise.all(keys.map(k => this._reconcile(k)));

    // Suscripción a cambios remotos
    keys.forEach(k => this._subscribe(k));

    // Flushear pushes pendientes cuando la pestaña se va a fondo / cierra
    const flush = () => {
      for (const [key, timer] of this.pushTimers) {
        clearTimeout(timer);
        this.pushTimers.delete(key);
        this._push(key);
      }
    };
    window.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'hidden') flush();
    });
    window.addEventListener('pagehide', flush);

    this.ready = true;
    this._setStatus('☁️ Sincronizado', 'ok');
    window.dispatchEvent(new Event('maxifer-sync-started'));
  }

  async _reconcile(key) {
    try {
      const ref = this._docRef(key);
      const snap = await getDoc(ref);
      const localValue = readLocal(key);
      const localTs = readLocalTs(key);

      if (snap.exists()) {
        const remote = snap.data();
        const remoteTs = remote.ts || 0;
        if (remoteTs > localTs) {
          writeLocal(key, remote.value, remoteTs);
        } else if (localTs > remoteTs && localValue !== null) {
          await setDoc(ref, { value: localValue, ts: localTs });
        }
      } else if (localValue !== null) {
        const ts = localTs || Date.now();
        await setDoc(ref, { value: localValue, ts });
        if (!localTs) writeLocal(key, localValue, ts);
      }
    } catch (err) {
      console.warn('[firebase-sync] reconcile failed for', key, err);
      this._setStatus('⚠️ Error sincronización', 'err');
    }
  }

  _subscribe(key) {
    const ref = this._docRef(key);
    const unsub = onSnapshot(ref, (snap) => {
      if (!snap.exists()) return;
      const remote = snap.data();
      const remoteTs = remote.ts || 0;
      const localTs = readLocalTs(key);
      if (remoteTs > localTs) {
        writeLocal(key, remote.value, remoteTs);
        if (this.onRemote) {
          try { this.onRemote(key, remote.value); } catch (e) { console.warn(e); }
        }
        window.dispatchEvent(new CustomEvent('maxifer-sync-update', {
          detail: { key, value: remote.value }
        }));
      }
    }, (err) => {
      console.warn('[firebase-sync] snapshot error', key, err);
      this._setStatus('⚠️ Sin conexión', 'err');
    });
    this.unsubs.set(key, unsub);
  }

  _patchLocalStorage() {
    if (Storage.prototype._maxiferPatched) return;
    const proto = Storage.prototype;
    const orig = proto.setItem;
    proto._origSetItem = orig;
    const self = this;
    proto.setItem = function(k, v) {
      orig.call(this, k, v);
      if (self.synced.has(k)) {
        const ts = Date.now();
        orig.call(this, tsKey(k), String(ts));
        self._schedulePush(k);
      }
    };
    proto._maxiferPatched = true;
  }

  _schedulePush(key) {
    clearTimeout(this.pushTimers.get(key));
    this._setStatus('☁️ Guardando...', 'sync');
    const t = setTimeout(() => this._push(key), PUSH_DEBOUNCE_MS);
    this.pushTimers.set(key, t);
  }

  async _push(key) {
    try {
      const value = readLocal(key);
      if (value === null) return;
      const ts = readLocalTs(key) || Date.now();
      await setDoc(this._docRef(key), { value, ts });
      this._setStatus('☁️ Sincronizado', 'ok');
    } catch (err) {
      console.warn('[firebase-sync] push failed for', key, err);
      this._setStatus('⚠️ Error al guardar', 'err');
    }
  }
}

const namespace = window.MAXIFER_SYNC_NAMESPACE || 'default';
window.MaxiferSync = new FirebaseSync(namespace);
window.dispatchEvent(new Event('maxifer-sync-ready'));
