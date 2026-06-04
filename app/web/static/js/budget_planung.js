/**
 * PflegeNachweis – Budgetplanung
 * Fachlogik für den interaktiven Budgetplaner.
 *
 * Konfiguration wird über data-* Attribute auf #planung-config geladen.
 * State wird ausschließlich aus dem DOM gelesen.
 * Rendering erfolgt ausschließlich über updateDOM().
 */

(function() {

    // Deutsches Zahlenformat: 1.234,56 €
    function fmtEur(val, dez) {
        if (dez === undefined) dez = 2;
        return val.toLocaleString('de-DE', {
            minimumFractionDigits: dez,
            maximumFractionDigits: dez,
        }) + ' €';
    }
    function fmtStd(val) {
        return val.toLocaleString('de-DE', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }) + ' Std.';
    }
    'use strict';

    // ── Konfiguration aus DOM lesen ──────────────────────────────────────────
    var cfg = document.getElementById('planung-config');
    if (!cfg) return;

    var BUDGET    = parseFloat(cfg.dataset.budget) || 0;
    var JAHR      = parseInt(cfg.dataset.jahr) || 2026;
    var PG_SAETZE = JSON.parse(cfg.dataset.pgSaetze || '{}');
    var SL_SAETZE = JSON.parse(cfg.dataset.slSaetze || '{}');
    var TP_SAETZE = JSON.parse(cfg.dataset.tpSaetze || '{}');
    var ENTLASTUNG     = parseFloat(cfg.dataset.entlastung) || 131;
    var ENTLASTUNG_MAX = parseFloat(cfg.dataset.entlastungMax) || 1572;
    var MONATE         = [1,2,3,4,5,6,7,8,9,10,11,12];

    // ── DOM-Hilfsfunktionen ──────────────────────────────────────────────────
    function el(id) { return document.getElementById(id); }
    function qsel(sel) { return document.querySelector(sel); }
    function qall(sel) { return document.querySelectorAll(sel); }

    // ── State lesen ──────────────────────────────────────────────────────────
    function leseState() {
        var state = { monate: {} };
        MONATE.forEach(function(m) {
            state.monate[m] = {
                pg:     parseInt((qsel('.pg-select[data-monat="'+m+'"]') || {}).value) || 1,
                vp:     parseFloat((qsel('.vp-input[data-monat="'+m+'"]') || {}).value) || 0,
                kzp:    parseFloat((qsel('.kzp-input[data-monat="'+m+'"]') || {}).value) || 0,
                slPct:  parseInt((qsel('.sl-select[data-monat="'+m+'"]') || {}).value) || 0,
            };
        });
        state.entlastungKzpAktiv = !!(el('cb-entlastung-kzp') && el('cb-entlastung-kzp').checked);

        // Vorjahresguthaben
        var vjInp = el('inp-vorjahr-guthaben');
        state.vorjahrGuthaben = vjInp ? Math.min(Math.max(parseFloat(vjInp.value) || 0, 0), ENTLASTUNG_MAX) : 0;

        // KZP Verpflegungsbeträge
        state.kzpVerpfl = {};
        document.querySelectorAll('.kzp-verpfl-input').forEach(function(inp) {
            var m = parseInt(inp.dataset.monat);
            if (m) state.kzpVerpfl[m] = parseFloat(inp.value) || 0;
        });

        return state;
    }

    // ── Berechnung ───────────────────────────────────────────────────────────
    function berechne(state) {
        var result = {
            monate: {},
            totalPG: 0, totalVP: 0, totalKZP: 0, totalSL: 0, totalTP: 0,
            restBudget: BUDGET,
            entlastungMonate: {},
        };

        MONATE.forEach(function(m) {
            var s = state.monate[m];
            var pgKey = String(s.pg);
            var pgMax  = PG_SAETZE[pgKey] || 0;
            var slMax  = SL_SAETZE[pgKey] || 0;
            var tpBetrag = TP_SAETZE[pgKey] || 0;

            // Kombinationsleistung § 38
            var slBetrag  = Math.round(slMax * s.slPct / 100);
            var pgProzent = Math.max(0, 100 - s.slPct);
            var pgBetrag  = Math.round(pgMax * pgProzent / 100);

            result.restBudget -= s.vp;
            result.restBudget -= s.kzp;
            result.totalPG  += pgBetrag;
            result.totalVP  += s.vp;
            result.totalKZP += s.kzp;
            result.totalSL  += slBetrag;
            result.totalTP  += tpBetrag;

            result.monate[m] = {
                pgBetrag:  pgBetrag,
                pgProzent: pgProzent,
                slBetrag:  slBetrag,
                slProzent: s.slPct,
                tpBetrag:  tpBetrag,
                restBudget: result.restBudget,
            };

            // Entlastungsbetrag KZP-Verrechnung
            var verpfl = (state.kzpVerpfl && state.kzpVerpfl[m]) || 0;
            var erstattet = state.entlastungKzpAktiv ? Math.min(verpfl, ENTLASTUNG) : 0;
            result.entlastungMonate[m] = {
                "erstattet": erstattet,
                "rest": ENTLASTUNG - erstattet,
            };
        });

        // Vorjahresguthaben: verfügbar Jan–Jun, danach abgelaufen
        var heute = new Date();
        var vorjahrAktiv = (heute.getFullYear() <= JAHR && heute.getMonth() < 6) ||
                           (heute.getFullYear() < JAHR);
        result.vorjahrGuthaben     = state.vorjahrGuthaben || 0;
        result.vorjahrAktiv        = vorjahrAktiv;
        result.vorjahrEntlastungGesamt = vorjahrAktiv ? result.vorjahrGuthaben : 0;

        result.pct = Math.min(100, Math.round((result.totalVP + result.totalKZP) / BUDGET * 100));
        result.restGesamt = BUDGET - result.totalVP - result.totalKZP;
        result.totalEntlastungRest = Object.values(result.entlastungMonate)
            .reduce(function(sum, e) { return sum + e.rest; }, 0)
            + result.vorjahrEntlastungGesamt;

        return result;
    }

    // ── DOM aktualisieren ────────────────────────────────────────────────────
    function updateDOM(result) {
        MONATE.forEach(function(m) {
            var r = result.monate[m];

            var pgB = qsel('.pg-betrag[data-monat="'+m+'"]');
            var pgP = qsel('.pg-prozent[data-monat="'+m+'"]');
            if (pgB) pgB.textContent = fmtEur(r.pgBetrag, 0);
            if (pgP) pgP.textContent = r.pgProzent + '%';

            var slB = qsel('.sl-betrag[data-monat="'+m+'"]');
            var slL = qsel('.sl-prozent-label[data-monat="'+m+'"]');
            if (slB) slB.textContent = fmtEur(r.slBetrag, 0);
            if (slL) slL.textContent = r.slProzent + '%';

            var tpB = qsel('.tp-betrag[data-monat="'+m+'"]');
            if (tpB) tpB.textContent = r.tpBetrag > 0 ? fmtEur(r.tpBetrag, 0) : '–';

            var restEl = qsel('.rest-betrag[data-monat="'+m+'"]');
            if (restEl) {
                restEl.textContent = fmtEur(r.restBudget, 0);
                restEl.style.color = r.restBudget < 0 ? 'var(--error)' : '#9333ea';
            }

            var entlEl = qsel('.entl-rest[data-monat="'+m+'"]');
            var e = result.entlastungMonate[m];
            if (entlEl) {
                entlEl.textContent = e.erstattet > 0
                    ? 'KZP: -' + e.erstattet.toFixed(0) + ' € / Rest: ' + fmtEur(e.rest, 0)
                    : '';
                entlEl.style.color = '#16a34a';
            }
        });

        // Totals
        function setText(id, val) { var e = el(id); if (e) e.textContent = val; }
        setText('total-vp', fmtEur(result.totalVP));
        setText('total-kzp', fmtEur(result.totalKZP));
        setText('total-pflegegeld', fmtEur(result.totalPG));
        setText('total-sl', result.totalSL > 0 ? fmtEur(result.totalSL) : '–');
        setText('total-tp', result.totalTP > 0 ? fmtEur(result.totalTP) : '–');
        setText('total-entlastung', fmtEur(result.totalEntlastungRest, 0));

        // Budget-Status-Bar
        var restEl2 = el('bsb-rest');
        if (restEl2) {
            restEl2.textContent = fmtEur(result.restGesamt);
            restEl2.style.color = result.restGesamt < 0 ? 'var(--error)'
                                : result.restGesamt < BUDGET * 0.2 ? '#b45309' : '#22c55e';
        }
        setText('bsb-geplant', fmtEur(result.totalVP + result.totalKZP));
        var bar = el('bsb-bar');
        if (bar) {
            bar.style.width = result.pct + '%';
            bar.style.background = result.pct >= 100 ? 'var(--error)'
                                 : result.pct >= 80 ? '#f59e0b' : 'var(--primary)';
        }
        setText('bsb-prozent', result.pct + '% verplant');

        // Vorjahresguthaben Badge + Hinweis
        var badge   = el('vorjahr-badge');
        var hinweis = el('vorjahr-total-hinweis');
        var vjInp   = el('inp-vorjahr-guthaben');
        if (badge) {
            if (result.vorjahrAktiv) {
                badge.textContent = '✓ nutzbar bis 30.06.' + JAHR;
                badge.style.background = '#dcfce7';
                badge.style.color      = '#16a34a';
                if (vjInp) { vjInp.disabled = false; vjInp.style.opacity = '1'; }
            } else {
                badge.textContent = '⚠ abgelaufen (nach 30.06.' + JAHR + ')';
                badge.style.background = '#fef9c3';
                badge.style.color      = '#b45309';
                if (vjInp) { vjInp.disabled = true; vjInp.style.opacity = '.45'; }
            }
        }
        if (hinweis && result.vorjahrGuthaben > 0) {
            hinweis.style.display = 'block';
            if (result.vorjahrAktiv) {
                hinweis.style.color = '#16a34a';
                hinweis.textContent = '+ ' + result.vorjahrGuthaben.toFixed(0) +
                    ' € Vorjahresguthaben werden zum Entlastungsbetrag addiert.';
            } else {
                hinweis.style.color = '#b45309';
                hinweis.textContent = 'Vorjahresguthaben nicht mehr nutzbar — Frist 30.06.' + JAHR + ' abgelaufen.';
            }
        } else if (hinweis) {
            hinweis.style.display = 'none';
        }
    }

    // ── Verbrauch-Summen ─────────────────────────────────────────────────────
    function updateVerbrauchSummen() {
        qall('.verbrauch-summe-row').forEach(function(row) {
            var totalId = row.getAttribute('data-total');
            if (!totalId) return;
            var total = 0;
            row.querySelectorAll('.vbr-input').forEach(function(inp) {
                total += parseFloat(inp.value) || 0;
            });
            var totalEl = el(totalId);
            if (totalEl) totalEl.textContent = fmtEur(total, 0);
        });
    }

    // ── Haupt-Berechnung ─────────────────────────────────────────────────────
    function run() {
        var state = leseState();
        var result = berechne(state);
        updateDOM(result);
        updateVerbrauchSummen();
    }

    // ── Chip-Toggle ──────────────────────────────────────────────────────────
    function chipKlick(chip) {
        var row = chip.getAttribute('data-row');
        var aktiv = chip.classList.toggle('la-active');
        qall('.' + row).forEach(function(tr) {
            if (aktiv) tr.classList.add('row-visible');
            else tr.classList.remove('row-visible');
        });
        // Sichtbarkeit ändert Berechnung nicht — Werte bleiben aktiv
    }

    function pgAlleSetzen(sel) {
        qall('.pg-select').forEach(function(s) { s.value = sel.value; });
        run();
    }

    // ── Aktionen ─────────────────────────────────────────────────────────────
    function gleichVerteilen() {
        var inputs = qall('.vp-input');
        var proMonat = Math.floor(BUDGET / 12 * 100) / 100;
        var verteilt = 0;
        inputs.forEach(function(inp, i) {
            if (i < inputs.length - 1) { inp.value = proMonat.toFixed(2); verteilt += proMonat; }
            else inp.value = (Math.round((BUDGET - verteilt) * 100) / 100).toFixed(2);
        });
        run();
    }

    function zuruecksetzen() {
        if (!confirm('Alle Eingaben zurücksetzen?')) return;
        // VP + KZP
        qall('.vp-input, .kzp-input').forEach(function(inp) { inp.value = 0; });
        // Sachleistungen
        qall('.sl-select').forEach(function(sel) { sel.value = 0; });
        // Pflegegrad auf PG 1 zurück
        qall('.pg-select').forEach(function(sel) { sel.value = 1; });
        // Verbrauch-Felder
        qall('.vbr-input').forEach(function(inp) { inp.value = 0; });
        // Vorjahresguthaben
        var vjInp = el('inp-vorjahr-guthaben');
        if (vjInp) vjInp.value = 0;
        // Checkbox KZP
        var cbEntl = el('cb-entlastung-kzp');
        if (cbEntl) cbEntl.checked = false;
        run();
    }

    function planungSpeichern() {
        var vp  = {}, kzp = {}, sl = {}, pg = {};
        MONATE.forEach(function(m) {
            var vpInp  = qsel('.vp-input[data-monat="'  + m + '"]');
            var kzpInp = qsel('.kzp-input[data-monat="' + m + '"]');
            var slSel  = qsel('.sl-select[data-monat="' + m + '"]');
            var pgSel  = qsel('.pg-select[data-monat="' + m + '"]');
            vp[m]  = vpInp  ? (parseFloat(vpInp.value)  || 0) : 0;
            kzp[m] = kzpInp ? (parseFloat(kzpInp.value) || 0) : 0;
            sl[m]  = slSel  ? (parseInt(slSel.value)    || 0) : 0;
            pg[m]  = pgSel  ? (parseInt(pgSel.value)    || 3) : 3;
        });
        var vjInp  = el('inp-vorjahr-guthaben');
        var cbEntl = el('cb-entlastung-kzp');
        fetch('/budget/planung/ajax-speichern', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                jahr:             JAHR,
                vp:               vp,
                kzp:              kzp,
                sl:               sl,
                pg:               pg,
                vorjahr_guthaben: vjInp  ? (parseFloat(vjInp.value) || 0) : 0,
                entlastung_kzp:   cbEntl ? cbEntl.checked : false,
                entlastung_vbr:   (function() {
                    var vbr = {};
                    MONATE.forEach(function(m) {
                        var inp = document.querySelector('.vbr-input[data-key="entlastung_vbr_' + m + '"]');
                        vbr[m] = inp ? (parseFloat(inp.value) || 0) : 0;
                    });
                    return vbr;
                })(),
            })
        }).then(function(r) { return r.json(); }).then(function(d) {
            var btn = el('btn-speichern');
            if (btn) {
                if (d.ok) {
                    btn.textContent = '✓ Gespeichert';
                    btn.style.background = '#16a34a';
                } else {
                    btn.textContent = '✗ Fehler';
                    btn.style.background = 'var(--error)';
                }
                setTimeout(function() {
                    btn.textContent = '💾 Speichern';
                    btn.style.background = '';
                }, 2000);
            }
        }).catch(function() {
            var btn = el('btn-speichern');
            if (btn) { btn.textContent = '✗ Fehler'; setTimeout(function() { btn.textContent = '💾 Speichern'; }, 2000); }
        });
    }

    function alsePdfDrucken() {
        var inputs = qall('.planung-input');
        inputs.forEach(function(inp) {
            var span = document.createElement('span');
            span.className = 'print-wert';
            span.textContent = fmtEur(parseFloat(inp.value||0), 0);
            inp.parentNode.insertBefore(span, inp);
            inp.style.display = 'none';
        });
        window.print();
        qall('.print-wert').forEach(function(s) { s.remove(); });
        inputs.forEach(function(inp) { inp.style.display = ''; });
    }

    // ── Event-Listener ───────────────────────────────────────────────────────
    qall('.la-chip').forEach(function(chip) {
        chip.addEventListener('click', function() { chipKlick(chip); });
    });
    qall('.pg-select').forEach(function(sel) {
        sel.addEventListener('change', function() { pgAlleSetzen(sel); });
    });
    qall('.vp-input, .kzp-input').forEach(function(inp) {
        inp.addEventListener('input', run);
    });
    qall('.sl-select').forEach(function(sel) {
        sel.addEventListener('change', run);
    });
    qall('.vbr-input').forEach(function(inp) {
        inp.addEventListener('input', updateVerbrauchSummen);
    });

    var cbEntl = el('cb-entlastung-kzp');
    if (cbEntl) cbEntl.addEventListener('change', run);

    var vjInp = el('inp-vorjahr-guthaben');
    if (vjInp) vjInp.addEventListener('input', run);

    el('btn-speichern') && el('btn-speichern').addEventListener('click', planungSpeichern);
    el('btn-gleich')    && el('btn-gleich').addEventListener('click', gleichVerteilen);
    el('btn-reset')     && el('btn-reset').addEventListener('click', zuruecksetzen);
    el('btn-pdf')       && el('btn-pdf').addEventListener('click', alsePdfDrucken);

    // ── Init ─────────────────────────────────────────────────────────────────
    run();

})();
