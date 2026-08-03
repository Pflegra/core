:root {
  /* Aus Lauras Loginreferenz und der Pflegra-Anwendung abgeleitete Markenpalette */
  --navy-900: #143d5d;
  --navy-800: #19506d;
  --blue-700: #1a6fa6;
  --teal-700: #1f7893;
  --teal-600: #278f91;
  --mint-200: #cceee5;
  --mint-100: #e7f7f3;
  --sky-100: #eaf4fb;
  --page: #f4f7fb;
  --surface: #ffffff;
  --ink: #102a43;
  --muted: #587086;
  --line: #d7e3ed;
  --focus: #f5b84b;
  /* Kompatibilitätsnamen für die vollständige Geschichte und Rechtseiten */
  --green: var(--teal-600);
  --green-dark: var(--navy-900);
  --mint: var(--mint-200);
  --soft: var(--sky-100);
  --paper: var(--page);
  --shadow: 0 26px 70px rgba(20, 61, 93, .13);
  --shadow-soft: 0 14px 38px rgba(20, 61, 93, .08);
  --radius: 1.25rem;
  --radius-lg: 1.75rem;
  --max: 1180px;
}

*, *::before, *::after { box-sizing: border-box; }
html { scroll-behavior: smooth; scroll-padding-top: 6rem; }
body {
  margin: 0; color: var(--ink); background: var(--page);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 1rem; line-height: 1.65;
}
img { display: block; max-width: 100%; }
a { color: var(--blue-700); text-underline-offset: .2em; }
a:hover { color: var(--navy-900); }
button, a { -webkit-tap-highlight-color: transparent; }
:focus-visible { outline: 3px solid var(--focus); outline-offset: 4px; }
.skip-link {
  position: fixed; top: .5rem; left: .5rem; z-index: 1000; transform: translateY(-150%);
  padding: .75rem 1rem; border-radius: .6rem; background: var(--navy-900); color: #fff;
}
.skip-link:focus { transform: none; }
.wrap { width: min(calc(100% - 2rem), var(--max)); margin-inline: auto; }
.site-header {
  position: sticky; top: 0; z-index: 100; border-bottom: 1px solid rgba(215, 227, 237, .9);
  background: rgba(244, 247, 251, .95); backdrop-filter: blur(14px);
}
.nav { min-height: 4.75rem; display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
.brand { display: inline-flex; flex: 0 0 auto; align-items: center; text-decoration: none; }
.brand-logo { display: block; width: 10rem; height: auto; }
.brand-logo-footer { width: 10rem; }
.nav-toggle {
  display: none; min-width: 44px; min-height: 44px; padding: .55rem;
  border: 1px solid var(--line); border-radius: .75rem; background: var(--surface);
  color: var(--navy-900); font: inherit; font-weight: 750;
}
.nav-links { display: flex; align-items: center; gap: 1.35rem; }
.nav-links a { color: var(--muted); font-size: .91rem; font-weight: 700; text-decoration: none; }
.nav-links a:hover { color: var(--navy-900); }
.button {
  display: inline-flex; align-items: center; justify-content: center; min-height: 48px;
  padding: .78rem 1.15rem; border: 1px solid transparent; border-radius: .78rem;
  font-weight: 800; line-height: 1.2; text-align: center; text-decoration: none;
}
.button-primary { background: var(--teal-700); color: #fff; box-shadow: 0 8px 20px rgba(31, 120, 147, .18); }
.button-primary:hover { background: var(--navy-800); color: #fff; }
.nav-links .button-primary, .nav-links .button-primary:hover, .nav-links .button-primary:focus-visible { color: #fff; }
.button-accent { background: var(--teal-600); color: #fff; }
.button-accent:hover { background: #207b7d; color: #fff; }
.button-ghost { border-color: rgba(255,255,255,.48); background: rgba(255,255,255,.08); color: #fff; }
.button-ghost:hover { border-color: #fff; background: rgba(255,255,255,.16); color: #fff; }
.button-secondary { border-color: var(--line); background: var(--surface); color: var(--navy-900); }
.button-secondary:hover { border-color: var(--teal-700); color: var(--teal-700); }
.eyebrow {
  margin: 0 0 .8rem; color: var(--teal-700); font-size: .76rem; font-weight: 850;
  letter-spacing: .13em; text-transform: uppercase;
}
h1, h2, h3 { margin-top: 0; color: var(--ink); line-height: 1.12; letter-spacing: -.035em; }
h1 { margin-bottom: 1.25rem; font-size: clamp(2.55rem, 5.8vw, 4.9rem); }
h2 { margin-bottom: 1rem; font-size: clamp(2rem, 4vw, 3.15rem); }
h3 { margin-bottom: .55rem; font-size: 1.2rem; }
.section { padding: clamp(4.5rem, 7vw, 7.5rem) 0; }
.section-soft { background: var(--sky-100); }
.section-heading { max-width: 760px; margin-bottom: 2.7rem; }
.section-heading > p:last-child { margin: 0; color: var(--muted); font-size: 1.08rem; }
.compact-heading { margin-bottom: 2rem; }

.hero {
  position: relative; overflow: hidden; padding: clamp(3rem, 5vw, 4.5rem) 0 0;
  background: linear-gradient(180deg, var(--page) 0%, #f7fafc 62%, var(--sky-100) 62%, var(--sky-100) 100%);
}
.hero-flow { position: relative; }
.hero-copy {
  position: relative; z-index: 2; max-width: 1100px; margin: 0 auto; text-align: center;
}
.hero-copy h1 { margin-inline: auto; color: var(--navy-900); font-size: clamp(3rem, 6.2vw, 5.25rem); letter-spacing: -.055em; }
.demo-note {
  max-width: 52rem; margin: .9rem auto 0; padding: .75rem 1rem; border: 1px solid rgba(31, 120, 147, .22);
  border-radius: .75rem; background: rgba(255,255,255,.7); color: var(--muted); font-size: .9rem; line-height: 1.5;
}
.demo-note strong { color: var(--navy-900); }
.hero-lead { max-width: 740px; margin: 0 auto; color: var(--muted); font-size: clamp(1.05rem, 1.8vw, 1.25rem); }
.actions { display: flex; flex-wrap: wrap; gap: .75rem; margin: 1.6rem 0; }
.hero-copy .actions { justify-content: center; margin: 1.8rem 0 1.3rem; }
.hero-trust { display: flex; flex-wrap: wrap; justify-content: center; gap: .6rem 1.3rem; margin: 0; padding: 0; color: var(--navy-800); list-style: none; font-size: .88rem; }
.hero-trust li::before { content: "✓"; margin-right: .4rem; color: var(--teal-600); font-weight: 900; }
.hero-product-stage { position: relative; margin-top: clamp(2.5rem, 5vw, 3.5rem); padding-bottom: clamp(3.5rem, 7vw, 6rem); }
.hero-product-stage::before {
  content: ""; position: absolute; top: clamp(2.5rem, 7vw, 5rem); bottom: 0;
  left: 50%; width: 100vw; transform: translateX(-50%);
  background: linear-gradient(110deg, var(--navy-900), var(--teal-700));
}
.hero-product { position: relative; width: min(1040px, 94%); margin: 0 auto; }
.hero-product .image-button { border-radius: .45rem; box-shadow: var(--shadow); }
.hero-product figcaption {
  position: relative; width: min(720px, calc(100% - 2rem)); margin: 1.2rem auto 0;
  color: #e8f3f7; font-size: .95rem; text-align: center;
}
.hero-product figcaption strong { color: #fff; }
.image-button {
  position: relative; display: block; width: 100%; padding: 0; overflow: hidden; cursor: zoom-in;
  border: 1px solid var(--line); border-radius: 1rem; background: var(--surface);
}
.image-button img { width: 100%; }
.zoom-hint {
  position: absolute; right: .65rem; bottom: .65rem; padding: .35rem .6rem;
  border-radius: .5rem; background: rgba(20,61,93,.9); color: #fff; font-size: .72rem; font-weight: 750;
}
.familiar-section { background: var(--surface); }
.situation-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; }
.situation-card {
  padding: 1.5rem 1rem 1rem 0; border-top: 3px solid var(--mint-200);
  background: transparent;
}
.situation-card > span { display: grid; place-items: center; width: 2.7rem; height: 2.7rem; margin-bottom: 1rem; border-radius: .8rem; background: var(--mint-100); }
.situation-card p, .benefit-card p, .model-card p { margin: 0; color: var(--muted); }
.benefit-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: .85rem; }
.benefit-card { padding: 1.35rem; border: 1px solid var(--line); border-radius: .8rem; background: var(--surface); }
.number { margin-bottom: .9rem; color: var(--teal-600); font-size: .78rem; font-weight: 900; letter-spacing: .12em; }
.product-section { background: var(--surface); }
.showcase { display: grid; grid-template-columns: 1fr 1fr; gap: 1.3rem; }
.showcase-wide { grid-column: 1 / -1; }
.showcase-item { margin: 0; }
.showcase-item .image-button { aspect-ratio: 16 / 9; }
.showcase-item .image-button img { width: 100%; height: 100%; object-fit: cover; object-position: top; }
.showcase-item figcaption { padding: .9rem .15rem 0; color: var(--muted); }
.showcase-item figcaption strong { color: var(--ink); }
.steps-section { background: linear-gradient(115deg, #eef6fb, #e8f6f3); }
.steps-layout { display: grid; grid-template-columns: .8fr 1.2fr; gap: clamp(2rem, 7vw, 6rem); align-items: start; }
.steps-list { display: grid; gap: .8rem; margin: 0; padding: 0; list-style: none; }
.steps-list li { display: flex; gap: 1rem; padding: 1.25rem; border: 1px solid rgba(215,227,237,.9); border-radius: 1rem; background: rgba(255,255,255,.82); }
.steps-list li > span { display: grid; place-items: center; width: 2.6rem; height: 2.6rem; flex: 0 0 2.6rem; border-radius: 50%; background: var(--teal-700); color: #fff; font-weight: 850; }
.steps-list p { margin: 0; color: var(--muted); }
.trust-section { background: linear-gradient(145deg, #123b59 0%, #185b73 55%, #1f7886 100%); color: #dcebf3; }
.trust-section h2, .trust-section h3 { color: #fff; }
.trust-layout { display: grid; grid-template-columns: 1fr 1fr; gap: clamp(2rem, 7vw, 6rem); align-items: center; }
.trust-layout > div:first-child > p:last-child { color: #dcebf3; font-size: 1.06rem; }
.trust-points { display: grid; gap: .8rem; }
.trust-points article { display: flex; gap: .85rem; padding: 1rem 1.15rem; border: 1px solid rgba(255,255,255,.14); border-radius: 1rem; background: rgba(255,255,255,.07); }
.trust-points article > span { color: #91e3cf; font-weight: 900; }
.trust-points p { margin: 0; color: #dcebf3; font-size: .9rem; }
.story-section { background: var(--surface); }
.story-layout { display: grid; grid-template-columns: minmax(240px, .7fr) minmax(0, 1.3fr); gap: clamp(2rem, 7vw, 6rem); align-items: center; }
.story-portrait { padding: 1rem; border-radius: 50% 50% 45% 55% / 45% 50% 50% 55%; background: linear-gradient(145deg, var(--sky-100), var(--mint-100)); }
.story-portrait img { width: 100%; aspect-ratio: 1; object-fit: cover; border-radius: inherit; }
.story-layout p { color: var(--muted); }
.text-link { display: inline-flex; gap: .4rem; align-items: center; color: var(--teal-700); font-weight: 800; text-decoration: none; }
.text-link:hover { color: var(--navy-900); }
.model-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; }
.model-card { padding: 1.5rem; border: 1px solid var(--line); border-radius: var(--radius); background: var(--surface); }
.status { display: inline-flex; margin-bottom: 1rem; padding: .3rem .65rem; border-radius: 99px; background: var(--mint-100); color: #14665f; font-size: .75rem; font-weight: 850; }
.status-planned { background: #e9f1f7; color: var(--navy-800); }
.closing-section { background: var(--surface); }
.closing-card {
  display: grid; grid-template-columns: 1.25fr .75fr; gap: 2rem; align-items: center;
  padding: clamp(2rem, 5vw, 4rem); border-radius: var(--radius-lg);
  background: linear-gradient(135deg, var(--navy-900), var(--teal-700)); color: #fff; box-shadow: var(--shadow);
}
.closing-card h2 { color: #fff; }
.closing-card p { color: #dcebf3; }
.closing-card .actions { justify-content: flex-end; }
.site-footer { padding: 3rem 0; background: #0e2f48; color: #c9dce8; }
.footer-grid { display: grid; grid-template-columns: 1fr auto; gap: 2rem; align-items: start; }
.footer-links { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: .65rem 1.2rem; }
.footer-links a { color: #e8f1f6; }
.legal-main { padding: 3rem 0 5rem; }
.legal-card { max-width: 820px; padding: clamp(1.25rem, 4vw, 3rem); border: 1px solid var(--line); border-radius: var(--radius); background: var(--surface); }
.legal-card h2 { margin-top: 2.3rem; font-size: 1.35rem; letter-spacing: -.01em; }
.legal-card li { margin-bottom: .35rem; }
.fine-print { color: var(--muted); font-size: .88rem; }
.card-kicker { margin-bottom: .8rem; color: var(--teal-700); font-size: .75rem; font-weight: 850; letter-spacing: .1em; text-transform: uppercase; }
.section-intro { max-width: 700px; margin-bottom: 2.5rem; color: var(--muted); font-size: 1.08rem; }
.path-grid { display: grid; grid-template-columns: 1.2fr .8fr; gap: 1rem; align-items: stretch; }
.path-box { padding: 2rem; border: 1px solid var(--line); border-radius: var(--radius); background: var(--surface); }
.path-box p { color: var(--muted); }
.story-heading > div { min-width: 0; }

.lightbox[hidden] { display: none; }
.lightbox {
  position: fixed; inset: 0; z-index: 999; display: grid; place-items: center; padding: 2rem;
  background: rgba(7, 28, 43, .92);
}
.lightbox img { max-width: min(1500px, 94vw); max-height: 86vh; border-radius: .8rem; box-shadow: 0 25px 80px rgba(0,0,0,.45); }
.lightbox-close { position: absolute; top: 1rem; right: 1.25rem; width: 46px; height: 46px; border: 1px solid rgba(255,255,255,.5); border-radius: 50%; background: rgba(255,255,255,.12); color: #fff; font-size: 1.8rem; cursor: pointer; }

@media (max-width: 1000px) {
  .nav-links { gap: .85rem; }
  .situation-grid { grid-template-columns: 1fr 1fr; }
  .benefit-grid { grid-template-columns: repeat(2, 1fr); }
  .benefit-card:last-child { grid-column: 1 / -1; }
}
@media (max-width: 800px) {
  html { scroll-padding-top: 5rem; }
  .nav { min-height: 4.25rem; }
  .nav-toggle { display: inline-flex; align-items: center; justify-content: center; }
  .nav-links {
    position: absolute; top: 100%; left: 0; right: 0; display: none; padding: .7rem 1rem 1rem;
    border-bottom: 1px solid var(--line); background: var(--page); box-shadow: 0 14px 30px rgba(20,61,93,.1);
  }
  .nav-links[data-open="true"] { display: grid; }
  .nav-links a { min-height: 44px; display: flex; align-items: center; padding: .4rem .2rem; }
  .hero { padding-top: 3.5rem; }
  .hero-copy { max-width: 700px; }
  .hero-product { width: 100%; }
  .showcase, .steps-layout, .trust-layout, .story-layout, .path-grid, .closing-card { grid-template-columns: 1fr; }
  .showcase-wide { grid-column: auto; }
  .model-grid { grid-template-columns: 1fr; }
  .closing-card .actions { justify-content: flex-start; }
  .footer-grid { grid-template-columns: 1fr; }
  .footer-links { justify-content: flex-start; }
}
@media (max-width: 480px) {
  .wrap { width: min(calc(100% - 1.25rem), var(--max)); }
  .section { padding: 3.5rem 0; }
  h1 { font-size: clamp(2.15rem, 10.5vw, 2.7rem); }
  h2 { font-size: clamp(1.8rem, 9vw, 2.35rem); }
  .hero { padding-top: 2.6rem; background: linear-gradient(180deg, var(--page) 0%, #f7fafc 66%, var(--sky-100) 66%, var(--sky-100) 100%); }
  .hero-copy { text-align: left; }
  .demo-note { margin-inline: 0; }
  .hero-lead { font-size: .98rem; line-height: 1.55; }
  .actions { display: grid; }
  .hero-copy .actions { justify-content: stretch; margin: 1.3rem 0 1rem; }
  .hero-copy .button { width: 100%; }
  .situation-grid, .benefit-grid { grid-template-columns: 1fr; }
  .benefit-card:last-child { grid-column: auto; }
  .hero-trust { display: grid; grid-template-columns: 1fr 1fr; justify-content: start; font-size: .78rem; }
  .hero-trust li:last-child { grid-column: 1 / -1; }
  .hero-product-stage { margin-top: 2.2rem; padding-bottom: 3rem; }
  .hero-product-stage::before { top: 2rem; }
  .hero-product figcaption { width: 100%; text-align: left; }
  .showcase-item .image-button { aspect-ratio: 4 / 3; }
  .showcase-item .image-button img { object-fit: cover; object-position: top left; }
}
@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
  *, *::before, *::after { animation-duration: .01ms !important; animation-iteration-count: 1 !important; transition-duration: .01ms !important; }
}
@media print {
  .site-header, .actions, .skip-link, .lightbox { display: none; }
  body { background: #fff; }
  .legal-card { border: 0; padding: 0; }
}
