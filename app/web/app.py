from __future__ import annotations
import logging
import os
import sys
import time
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware

from models import PflegraDB
from config import Konfiguration
from services.budget_service import BudgetService
from services.export_service import ExportService
from services.import_service import ImportService
from services.backup_service import BackupService
from logging_setup import setup_logging

from web.routers import eintraege, personen, versicherte, budget, export, einstellungen, importieren, backup, antraege, admin, datenpflege, budget_planung, entlastung, pflegegrad, leistungsfinder, tagebuch, statistiken, widerspruch, gutachten, pflegeberatung, dokumente, aufgaben, zeitachse, erinnerungen, kontakte, fristen, kalender, termine
from web.routers.login import router as login_router
from web.auth import login_erforderlich, hash_passwort
from web.csrf import CSRF_COOKIE, generiere_csrf_token, get_csrf_token, pruefe_csrf_request, csrf_fehler

DATA_DIR = Path(os.environ.get("PFLEGRA_DATA", ROOT))

# ── Logging einrichten (vor allem anderen) ───────────────────────────────────
log_ordner = DATA_DIR / "logs"
setup_logging(log_ordner=log_ordner, debug=os.environ.get("PFLEGRA_DEBUG") == "1")
log = logging.getLogger(__name__)

app = FastAPI(
    title="Pflegra",
    version="1.5.5",
    root_path=os.environ.get("INGRESS_ENTRY", ""),
)


# ── Request-Logging Middleware ────────────────────────────────────────────────
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:
            log.error(
                "Unbehandelte Exception  %s %s  %s",
                request.method, request.url.path, exc,
                exc_info=True,
            )
            raise
        dauer_ms = (time.perf_counter() - start) * 1000
        # Statische Dateien nicht loggen
        if not request.url.path.startswith("/static"):
            level = logging.WARNING if response.status_code >= 400 else logging.INFO
            log.log(
                level,
                "%s  %s  %d  %.0fms",
                request.method, request.url.path,
                response.status_code, dauer_ms,
            )
        return response

app.add_middleware(RequestLoggingMiddleware)


# ── Ingress-Path Middleware ───────────────────────────────────────────────────
class IngressMiddleware(BaseHTTPMiddleware):
    """Setzt root_path aus X-Ingress-Path Header oder app.state wenn vorhanden."""
    async def dispatch(self, request: Request, call_next):
        ingress_path = request.headers.get("X-Ingress-Path", "")
        if ingress_path and not request.scope.get("root_path"):
            request.scope["root_path"] = ingress_path
        # Fallback: aus App-State (INGRESS_ENTRY Umgebungsvariable)
        if not request.scope.get("root_path"):
            try:
                entry = request.app.state.ingress_entry
                if entry:
                    request.scope["root_path"] = entry
            except AttributeError:
                pass
        return await call_next(request)

app.add_middleware(IngressMiddleware)


# ── Auth-Middleware ───────────────────────────────────────────────────────────
OEFFENTLICHE_PFADE = {"/login", "/logout", "/setup", "/health", "/version", "/impressum", "/sw.js"}

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Root-Path (Ingress-Prefix) abziehen für korrekten Pfad-Vergleich
        full_path = request.url.path
        root = request.scope.get("root_path", "")

        path = full_path[len(root):] if (root and full_path.startswith(root)) else full_path
        if not path:
            path = "/"
        # Statische Dateien und Login-Seite sind offen
        if path.startswith("/static") or path.startswith("/lang/") or path in OEFFENTLICHE_PFADE:
            return await call_next(request)
        # Kein Passwort gesetzt → direkt durchlassen (Erststart)
        # Eingeloggt prüfen — DB-basierte Auth (Multiuser)
        redirect = login_erforderlich(request)
        if redirect:
            from web.auth import _get_root
            from urllib.parse import quote
            next_path = quote(path)
            login_url = _get_root(request) + "/login?next=" + next_path
            log.warning("=== INGRESS REDIRECT === to=%s", path)
            from fastapi.responses import RedirectResponse
            return RedirectResponse(login_url, status_code=303)
        response = await call_next(request)
        # CSRF-Cookie setzen falls nicht vorhanden
        if CSRF_COOKIE not in request.cookies:
            response.set_cookie(
                CSRF_COOKIE, generiere_csrf_token(),
                httponly=False,  # muss vom JS lesbar sein für Double-Submit
                samesite="lax",
                max_age=60 * 60 * 8,
            )
        return response

app.add_middleware(AuthMiddleware)

WEB_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")
TEMPLATES = Jinja2Templates(directory=str(WEB_DIR / "templates"))

# i18n
from i18n import get_lang, make_t, SUPPORTED_LANGS
TEMPLATES.env.globals["SUPPORTED_LANGS"] = SUPPORTED_LANGS


# base_ctx lives in web.routers.deps — imported below
from web.routers.deps import base_ctx  # noqa: E402

@app.on_event("startup")
async def startup():
    konfig_pfad = DATA_DIR / "config.json"
    konfig = Konfiguration.lade(konfig_pfad)
    db_pfad = DATA_DIR / "pflegra.db"
    db = PflegraDB(db_pfad)
    app.state.data_dir = DATA_DIR
    app.state.konfig_pfad = konfig_pfad
    app.state.konfig = konfig
    app.state.db = db
    app.state.budget_service = BudgetService(db, konfig)
    app.state.export_service = ExportService(db, konfig)
    app.state.import_service = ImportService(db)
    backup_svc = BackupService(konfig)
    backup_svc._db_pfad = db_pfad
    backup_svc._backup_ordner = db_pfad.parent / "backups"
    app.state.backup_service = backup_svc

    # Ingress-Entry aus Umgebungsvariable (gesetzt von run.sh via bashio)
    import os
    ingress_entry = os.environ.get("INGRESS_ENTRY", "")
    app.state.ingress_entry = ingress_entry
    if ingress_entry:
        import logging
        logging.getLogger("web.app").info("Ingress-Entry: %s", ingress_entry)

    # Migration: bestehenden Single-User aus config.json → DB-Admin
    if not db.user_admin_existiert():
        from models import User as UserModel
        from web.auth import hash_passwort as _hash
        if konfig.passwort_hash:
            # Bestehendes Passwort aus config.json
            admin = UserModel(
                username=konfig.benutzer_name or "admin",
                passwort=konfig.passwort_hash,
                rolle="admin",
                aktiv=True,
                notiz="Migriert aus config.json",
            )
        else:
            # Kein Passwort gesetzt → Admin mit Temp-Passwort anlegen
            # User muss Passwort in Einstellungen ändern
            admin = UserModel(
                username="admin",
                passwort=_hash("admin"),
                rolle="admin",
                aktiv=True,
                notiz="Standard-Admin (Passwort bitte ändern!)",
            )
            log.warning("Kein Passwort in config.json — Admin mit Standard-Passwort 'admin' angelegt!")
        db.user_speichern(admin)
        log.info("Admin-User angelegt: %s (ID=%d)", admin.username, db.user_laden_by_username(admin.username).id)

    # Demo-User anlegen — immer NACH Admin, immer rolle="user"
    if not db.user_laden_by_username("demo"):
        from models import User as UserModel
        from web.auth import hash_passwort as _hash
        demo = UserModel(
            username="demo",
            passwort=_hash("demo"),
            rolle="user",   # NIEMALS admin
            aktiv=True,
            notiz="Automatisch angelegter Demo-User",
        )
        db.user_speichern(demo)
        demo_obj = db.user_laden_by_username("demo")
        log.info("Demo-User angelegt (demo/demo, ID=%d)", demo_obj.id if demo_obj else -1)
    else:
        # Sicherheitscheck: Demo darf nie Admin sein
        demo_u = db.user_laden_by_username("demo")
        if demo_u and demo_u.rolle == "admin":
            demo_u.rolle = "user"
            db.user_speichern(demo_u)
            log.warning("Demo-User hatte Admin-Rolle — korrigiert auf user")

    # Migration: Absender-Daten aus config.json → user_settings für Admin
    if konfig.absender_name:
        admin_u = db.user_laden_by_username(konfig.benutzer_name or "admin")
        if admin_u:
            existing = db.user_settings_laden(admin_u.id)
            if not existing.absender_name:
                from models import UserSettings
                s = UserSettings(
                    user_id=admin_u.id,
                    absender_name=konfig.absender_name,
                    absender_adresse=konfig.absender_adresse,
                    absender_mail=konfig.absender_mail,
                    absender_geburtsdatum=konfig.absender_geburtsdatum,
                    stundensatz=konfig.stundensatz,
                )
                db.user_settings_speichern(s)
                log.info("Absender-Daten aus config.json nach user_settings migriert")
    from demo_reset import demo_reset, starte_demo_reset_scheduler
    demo_u = db.user_laden_by_username("demo")
    if demo_u:
        demo_reset(db)
        log.info("Demo-User Daten initialisiert (owner_id=%d)", demo_u.id)
    starte_demo_reset_scheduler(lambda: app.state.db)

    # Erinnerungen-Scheduler
    from services.erinnerungen_service import ErinnerungenConfig, erinnerungen_lauf
    import asyncio, threading

    def _erinnerungen_loop():
        import time
        from datetime import datetime
        letzter_lauf_tag = None
        while True:
            try:
                jetzt = datetime.now()
                heute = jetzt.date()
                ecfg = ErinnerungenConfig.aus_db(app.state.db)
                if jetzt.hour == ecfg.erinnerung_stunde and letzter_lauf_tag != heute:
                    log.info("Starte Erinnerungen-Lauf...")
                    erinnerungen_lauf(app.state.db)
                    letzter_lauf_tag = heute
            except Exception as exc:
                log.error("Erinnerungen-Scheduler Fehler: %s", exc, exc_info=True)
            time.sleep(60)

    t = threading.Thread(target=_erinnerungen_loop, daemon=True, name="erinnerungen-scheduler")
    t.start()
    log.info("Erinnerungen-Scheduler gestartet")

    log.info("Pflegra gestartet  DATA_DIR=%s  DB=%s  Users=%d",
             DATA_DIR, db_pfad, db.user_anzahl())


# ── Globaler Fehler-Handler ───────────────────────────────────────────────────
@app.exception_handler(404)
async def nicht_gefunden(request: Request, exc):
    lang = get_lang(request)
    return TEMPLATES.TemplateResponse(request, "fehler.html", {
        "pflegedienst_name": _pflegedienst_name(request),
        "code": 404,
        "meldung": "Seite nicht gefunden.",
        "lang": lang,
        "_": make_t(lang),
    }, status_code=404)


@app.exception_handler(500)
async def server_fehler(request: Request, exc):
    log.error("500 bei %s: %s", request.url.path, exc, exc_info=True)
    lang = get_lang(request)
    return TEMPLATES.TemplateResponse(request, "fehler.html", {
        "pflegedienst_name": _pflegedienst_name(request),
        "code": 500,
        "meldung": "Interner Fehler – Details wurden ins Log geschrieben.",
        "lang": lang,
        "_": make_t(lang),
    }, status_code=500)


def _pflegedienst_name(request: Request) -> str:
    try:
        return request.app.state.konfig.pflegedienst_name
    except Exception:
        return ""

app.include_router(login_router)
app.include_router(eintraege.router)
app.include_router(personen.router)
app.include_router(versicherte.router)
app.include_router(budget.router)
app.include_router(export.router)
app.include_router(einstellungen.router)
app.include_router(importieren.router)
app.include_router(backup.router)
app.include_router(antraege.router)
app.include_router(admin.router)
app.include_router(datenpflege.router)
app.include_router(budget_planung.router)
app.include_router(entlastung.router)
app.include_router(pflegegrad.router)
app.include_router(leistungsfinder.router)
app.include_router(tagebuch.router)
app.include_router(statistiken.router)
app.include_router(pflegeberatung.router)
app.include_router(dokumente.router)
app.include_router(aufgaben.router)
app.include_router(erinnerungen.router)
app.include_router(kontakte.router)
app.include_router(fristen.router)
app.include_router(kalender.router)
app.include_router(termine.router)
app.include_router(zeitachse.router)
app.include_router(widerspruch.router)
app.include_router(gutachten.router)
from fastapi.responses import JSONResponse
import time as _time

_start_time = _time.time()
APP_VERSION = "1.5.5"



@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    from fastapi.responses import FileResponse
    return FileResponse(str(WEB_DIR / "static" / "favicon.ico"))

@app.get("/sw.js")
async def service_worker():
    """Service Worker muss vom Root-Scope aus erreichbar sein."""
    from fastapi.responses import FileResponse
    sw_path = WEB_DIR / "static" / "sw.js"
    return FileResponse(sw_path, media_type="application/javascript",
                        headers={"Service-Worker-Allowed": "/"})

@app.get("/impressum", response_class=HTMLResponse)
async def impressum(request: Request):
    return TEMPLATES.TemplateResponse(request, "impressum.html", {
        **base_ctx(request),
    })


@app.get("/health")
async def health(request: Request):
    """Health-Check Endpoint — für Docker Healthcheck und Monitoring."""
    try:
        db = request.app.state.db
        db.statistik()  # DB-Verbindung testen
        db_ok = True
        db_integrity = db._schema.integrity_check()
    except Exception:
        db_ok = False
        db_integrity = False

    status = "ok" if (db_ok and db_integrity) else "degraded"
    return JSONResponse({
        "status": status,
        "db": "ok" if db_ok else "error",
        "db_integrity": "ok" if db_integrity else "error",
        "schema_version": db.schema_version() if db_ok else None,
        "uptime_s": int(_time.time() - _start_time),
        "version": APP_VERSION,
    }, status_code=200 if db_ok else 503)


@app.get("/version")
async def version():
    """Version-Endpoint."""
    return JSONResponse({
        "version": APP_VERSION,
        "python": __import__("sys").version.split()[0],
    })

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    db = request.app.state.db
    konfig = request.app.state.konfig
    budget_service = request.app.state.budget_service
    aktuelles_jahr = konfig.standard_jahr or date.today().year

    from web.auth import get_aktueller_user
    from web.routers.deps import get_owner_id
    user = get_aktueller_user(request)
    owner_id = get_owner_id(request)

    personen = db.personen(owner_id)
    alle_eintraege = db.alle(owner_id)

    # Personenkarten mit Budget + Versichertendaten
    karten = []
    for person in personen:
        vers = db.versicherter_laden(person)
        bericht = None
        try:
            bericht = budget_service.bericht_fuer_person(
                person, aktuelles_jahr, eintraege=alle_eintraege
            )
        except Exception:
            pass

        # Letzte Einträge dieser Person
        person_eintraege = sorted(
            [e for e in alle_eintraege if e.person == person],
            key=lambda e: e.datum, reverse=True
        )
        letzter_eintrag = person_eintraege[0].datum if person_eintraege else None

        karten.append({
            "name": person,
            "initialen": "".join(t[0].upper() for t in person.split()[:2]),
            "vers": vers,
            "budget": bericht.budget if bericht else None,
            "ampel": bericht.ampel if bericht else "gruen",
            "eintraege_anzahl": len(person_eintraege),
            "letzter_eintrag": letzter_eintrag,
        })

    statistik = db.statistik(owner_id)

    # Letzter Pflegegrad aus Verlauf
    letzter_pg = None
    try:
        verlauf = db.pg_verlauf_alle(owner_id)
        if verlauf:
            letzter_pg = verlauf[0]  # neuester Eintrag
    except Exception:
        pass

    # Nicht ausgeschöpfte Leistungen (Entlastungsbetrag)
    nicht_ausgeschoepft = []
    try:
        from datetime import date as _date
        monat = _date.today().month
        for k in karten:
            if not k["vers"]:
                continue
            pg = k["vers"].pflegegrad or 0
            if pg < 1:
                continue
            from pflege_rules import get_regelwerk
            r = get_regelwerk(aktuelles_jahr)
            # Entlastungsbetrag: Verbrauch dieses Monats prüfen
            verbrauch = db.entlastung_summe(k["name"], owner_id, aktuelles_jahr, monat)
            monatlich = r.entlastungsbetrag_monatlich
            if verbrauch < monatlich * 0.1:  # weniger als 10% genutzt
                nicht_ausgeschoepft.append({
                    "person": k["name"],
                    "leistung": "Entlastungsbetrag",
                    "betrag": monatlich,
                    "paragraf": "§ 45b SGB XI",
                    "link": "/entlastung/",
                })
    except Exception:
        pass

    # Leistungsvorschau für Dashboard (Top-4 verfügbare Leistungen)
    leistungsvorschau = []
    try:
        if letzter_pg and letzter_pg.pflegegrad > 0:
            from leistungsfinder import berechne_leistungen
            lf = berechne_leistungen(letzter_pg.pflegegrad, "haeuslich", "pflegegeld", aktuelles_jahr)
            for p in lf.monatlich[:4]:
                leistungsvorschau.append({
                    "titel": p.titel,
                    "betrag": p.betrag,
                    "einheit": p.einheit,
                    "kategorie": p.kategorie,
                })
    except Exception:
        pass

    # Fristen berechnen
    fristen = []
    try:
        from services.fristen_service import berechne_fristen
        from pflege_rules import get_regelwerk
        r = get_regelwerk(aktuelles_jahr)
        personen_daten = []
        for k in karten:
            entl_gesamt = 0.0
            entl_monat = 0.0
            try:
                entl_gesamt = db.entlastung_summe(k["name"], owner_id, aktuelles_jahr)
                entl_monat  = db.entlastung_summe(k["name"], owner_id, aktuelles_jahr, date.today().month)
            except Exception:
                pass
            letztes_pg_datum = None
            try:
                pg_e = db.pg_verlauf_alle(owner_id, k["name"])
                if pg_e:
                    from datetime import datetime as _dt
                    letztes_pg_datum = _dt.strptime(pg_e[0].datum, "%Y-%m-%d").date()
            except Exception:
                pass
            personen_daten.append({
                "name": k["name"],
                "vers": k["vers"],
                "bericht": k["budget"],
                "entlastung_verbrauch_gesamt": entl_gesamt,
                "entlastung_verbrauch_monat":  entl_monat,
                "letztes_pg_datum": letztes_pg_datum,
            })
        fristen = berechne_fristen(personen_daten, aktuelles_jahr, r)
    except Exception:
        pass

    # Letzte Gutachten-Analysen
    letzte_gutachten = []
    try:
        from web.routers.gutachten import _lade_analysen
        letzte_gutachten = _lade_analysen(request, owner_id)[:3]
    except Exception:
        pass

    # Letzte Dokumente
    letzte_dokumente = []
    dokumente_gesamt = 0
    try:
        from web.routers.dokumente import _lade_dokumente
        alle_dokumente = _lade_dokumente(request, owner_id)
        dokumente_gesamt = len(alle_dokumente)
        letzte_dokumente = alle_dokumente[:3]
    except Exception:
        pass
    beratung_fristen = []
    letzte_beratungen = []
    try:
        from web.routers.pflegeberatung import _lade_eintraege
        alle_beratungen = _lade_eintraege(request, owner_id)
        seen = set()
        for b in alle_beratungen:
            if b.person not in seen:
                seen.add(b.person)
                letzte_beratungen.append(b)
                if b.tage_bis_termin is not None and b.tage_bis_termin <= 60:
                    beratung_fristen.append(b)
    except Exception:
        pass

    # Aufgaben berechnen
    offene_aufgaben = []
    try:
        from services.aufgaben_service import berechne_aufgaben
        from web.routers.fristen import _lade_fristen as _lade_eigene_fristen
        eigene_fristen = _lade_eigene_fristen(request, owner_id, nur_offen=True)
        offene_aufgaben = berechne_aufgaben(fristen, letzte_beratungen, eigene_fristen)
    except Exception:
        pass
    naechste_aktion = None
    try:
        from datetime import date as _date
        kandidaten = []
        # Fristen
        for f in fristen:
            if f.tage_bis_faellig is not None:
                kandidaten.append((f.tage_bis_faellig, f.titel, f.faellig_str if hasattr(f, 'faellig_str') else ""))
        # Beratungsfristen
        for b in beratung_fristen:
            if b.tage_bis_termin is not None:
                kandidaten.append((b.tage_bis_termin, f"Pflegeberatung § 37.3 · {b.person}", b.naechster_termin_str))
        if kandidaten:
            kandidaten.sort(key=lambda x: x[0])
            tage, titel, datum = kandidaten[0]
            if tage < 0:
                naechste_aktion = {"emoji": "🚨", "text": f"{titel}", "hinweis": "überfällig", "klasse": "rot"}
            elif tage <= 14:
                naechste_aktion = {"emoji": "⚠️", "text": f"{titel}", "hinweis": f"fällig am {datum}", "klasse": "gelb"}
            elif tage <= 30:
                naechste_aktion = {"emoji": "⏰", "text": f"{titel}", "hinweis": f"fällig am {datum}", "klasse": "gelb"}
            elif tage <= 60:
                naechste_aktion = {"emoji": "📅", "text": f"{titel}", "hinweis": f"fällig am {datum}", "klasse": "blau"}
    except Exception:
        pass

    return TEMPLATES.TemplateResponse(request, "index.html", {
        **base_ctx(request),
        "karten": karten,
        "statistik": statistik,
        "aktuelles_jahr": aktuelles_jahr,
        "letzter_pg": letzter_pg,
        "nicht_ausgeschoepft": nicht_ausgeschoepft,
        "leistungsvorschau": leistungsvorschau,
        "fristen": fristen,
        "naechste_aktion": naechste_aktion,
        "offene_aufgaben": offene_aufgaben,
        "letzte_gutachten": letzte_gutachten,
        "letzte_dokumente": letzte_dokumente,
        "dokumente_gesamt": dokumente_gesamt,
        "beratung_fristen": beratung_fristen,
        "letzte_beratungen": letzte_beratungen,
    })


# ── Sprachumschaltung ─────────────────────────────────────────────────────────
@app.get("/lang/{lang}")
async def sprache_setzen(lang: str, request: Request):
    from fastapi.responses import RedirectResponse as RR
    from web.auth import get_aktueller_user
    referer = request.headers.get("referer", "/")
    if lang not in SUPPORTED_LANGS:
        lang = "de"
    # Wenn referer von externer Domain kommt → auf /login redirecten
    host = request.headers.get("host", "")
    if referer and host and host not in referer:
        referer = "/login"
    response = RR(referer, status_code=303)
    response.set_cookie("pflegra_lang", lang, max_age=60*60*24*365, httponly=False, samesite="lax")
    return response
