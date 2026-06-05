/* PflegeNachweis – Hilfs-JavaScript */

// Stunden automatisch berechnen wenn Von+Bis gesetzt werden
(function () {
    function berechneStunden() {
        const von = document.getElementById('von');
        const bis = document.getElementById('bis');
        const stunden = document.getElementById('stunden');
        if (!von || !bis || !stunden) return;
        if (von.value && bis.value) {
            const [vh, vm] = von.value.split(':').map(Number);
            const [bh, bm] = bis.value.split(':').map(Number);
            const diff = (bh * 60 + bm) - (vh * 60 + vm);
            if (diff > 0) {
                stunden.value = (diff / 60).toFixed(2);
            }
        }
    }
    document.addEventListener('DOMContentLoaded', function () {
        const von = document.getElementById('von');
        const bis = document.getElementById('bis');
        if (von) von.addEventListener('change', berechneStunden);
        if (bis) bis.addEventListener('change', berechneStunden);
    });
})();

// Flash-Nachrichten nach 5s ausblenden
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.alert-ok').forEach(function (el) {
        setTimeout(function () {
            el.style.transition = 'opacity .5s';
            el.style.opacity = '0';
            setTimeout(function () { el.remove(); }, 500);
        }, 5000);
    });
});
