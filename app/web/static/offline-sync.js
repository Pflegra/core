/**
 * Pflegra Offline-Sync
 * Speichert Einträge in IndexedDB wenn offline, sync beim nächsten Online-Sein.
 */

const DB_NAME    = 'pflegra-offline';
const DB_VERSION = 1;
const STORE_NAME = 'pending-eintraege';

// ── IndexedDB öffnen ──────────────────────────────────────────────────────────

function openDB() {
    return new Promise((resolve, reject) => {
        const req = indexedDB.open(DB_NAME, DB_VERSION);
        req.onupgradeneeded = e => {
            const db = e.target.result;
            if (!db.objectStoreNames.contains(STORE_NAME)) {
                db.createObjectStore(STORE_NAME, { keyPath: 'id', autoIncrement: true });
            }
        };
        req.onsuccess = e => resolve(e.target.result);
        req.onerror   = e => reject(e.target.error);
    });
}

// ── Eintrag lokal speichern ───────────────────────────────────────────────────

async function speichereOffline(formData, aktion) {
    const db = await openDB();
    const daten = { aktion, zeitstempel: new Date().toISOString(), felder: {} };
    for (const [k, v] of formData.entries()) daten.felder[k] = v;
    return new Promise((resolve, reject) => {
        const tx  = db.transaction(STORE_NAME, 'readwrite');
        const req = tx.objectStore(STORE_NAME).add(daten);
        req.onsuccess = () => resolve(req.result);
        req.onerror   = () => reject(req.error);
    });
}

// ── Ausstehende Einträge laden ────────────────────────────────────────────────

async function ladePending() {
    const db = await openDB();
    return new Promise((resolve, reject) => {
        const tx  = db.transaction(STORE_NAME, 'readonly');
        const req = tx.objectStore(STORE_NAME).getAll();
        req.onsuccess = () => resolve(req.result);
        req.onerror   = () => reject(req.error);
    });
}

// ── Eintrag nach Sync löschen ─────────────────────────────────────────────────

async function loescheOffline(id) {
    const db = await openDB();
    return new Promise((resolve, reject) => {
        const tx  = db.transaction(STORE_NAME, 'readwrite');
        const req = tx.objectStore(STORE_NAME).delete(id);
        req.onsuccess = () => resolve();
        req.onerror   = () => reject(req.error);
    });
}

// ── Sync: alle ausstehenden Einträge absenden ─────────────────────────────────

async function syncPending() {
    const pending = await ladePending();
    if (!pending.length) return 0;

    let synced = 0;
    for (const eintrag of pending) {
        try {
            const body = new FormData();
            for (const [k, v] of Object.entries(eintrag.felder)) body.append(k, v);

            const res = await fetch(eintrag.aktion, {
                method:      'POST',
                body,
                credentials: 'same-origin',
                redirect:    'follow',
            });

            if (res.ok || res.redirected) {
                await loescheOffline(eintrag.id);
                synced++;
            }
        } catch (e) {
            console.warn('Sync fehlgeschlagen für Eintrag', eintrag.id, e);
        }
    }
    aktualisiereSyncBadge();
    return synced;
}

// ── Badge in Navigation aktualisieren ────────────────────────────────────────

async function aktualisiereSyncBadge() {
    const pending = await ladePending();
    const anzahl  = pending.length;
    let badge = document.getElementById('offline-sync-badge');

    if (anzahl > 0) {
        if (!badge) {
            badge = document.createElement('span');
            badge.id = 'offline-sync-badge';
            badge.style.cssText = `
                display:inline-flex;align-items:center;justify-content:center;
                background:#e53e3e;color:white;border-radius:99px;
                font-size:.65rem;font-weight:700;min-width:16px;height:16px;
                padding:0 4px;margin-left:4px;vertical-align:middle;
            `;
            // An "Einträge" Nav-Link hängen
            const navLinks = document.querySelectorAll('.nav-link, nav a');
            for (const link of navLinks) {
                if (link.textContent.includes('Einträge')) {
                    link.appendChild(badge);
                    break;
                }
            }
        }
        badge.textContent = anzahl;
        badge.title = `${anzahl} Eintrag${anzahl > 1 ? 'e' : ''} wartet auf Synchronisation`;
    } else if (badge) {
        badge.remove();
    }
}

// ── Online-Event: automatisch syncen ─────────────────────────────────────────

window.addEventListener('online', async () => {
    const synced = await syncPending();
    if (synced > 0) {
        zeigeToast(`✅ ${synced} Eintrag${synced > 1 ? 'e' : ''} synchronisiert`);
        // Seite neu laden wenn wir auf der Einträge-Liste sind
        if (window.location.pathname.includes('/eintraege')) {
            setTimeout(() => window.location.reload(), 1500);
        }
    }
});

// ── Toast-Benachrichtigung ────────────────────────────────────────────────────

function zeigeToast(text, dauer = 3500) {
    let toast = document.getElementById('pflegra-toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'pflegra-toast';
        toast.style.cssText = `
            position:fixed;bottom:5rem;left:50%;transform:translateX(-50%);
            background:#2d3748;color:white;padding:.65rem 1.25rem;
            border-radius:10px;font-size:.88rem;z-index:9999;
            box-shadow:0 4px 16px rgba(0,0,0,.3);
            transition:opacity .3s;pointer-events:none;
        `;
        document.body.appendChild(toast);
    }
    toast.textContent = text;
    toast.style.opacity = '1';
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => { toast.style.opacity = '0'; }, dauer);
}

// ── Init ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
    await aktualisiereSyncBadge();

    // Beim Laden: falls online und pending → sync
    if (navigator.onLine) {
        const synced = await syncPending();
        if (synced > 0) zeigeToast(`✅ ${synced} Eintrag${synced > 1 ? 'e' : ''} synchronisiert`);
    }
});

// Export für Formular-Handler
window.pflegraOffline = { speichereOffline, syncPending, zeigeToast, aktualisiereSyncBadge };
