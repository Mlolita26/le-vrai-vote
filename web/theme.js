/* Le Vrai Vote — bascule mode clair / sombre.
   À placer dans web/theme.js. Charge-le sur chaque page, p.ex. :
     <script src="/le-vrai-vote/theme.js" defer></script>
   Sans ce fichier, le mode sombre suit automatiquement le réglage
   du système du visiteur (via styles.css). Avec ce fichier, un bouton
   de bascule apparaît dans la navigation et le choix est mémorisé. */
(function () {
  var KEY = 'lvv-theme';
  var root = document.documentElement;

  // Charge Spectral + Libre Franklin sans bloquer le rendu de la page.
  try {
    var f = document.createElement('link');
    f.rel = 'stylesheet';
    f.href = 'https://fonts.googleapis.com/css2?family=Spectral:wght@500;600;700&family=Libre+Franklin:wght@400;500;600;700&family=Archivo:wght@600;900&display=swap';
    document.head.appendChild(f);
  } catch (e) {}

  function apply(t) { if (t) root.setAttribute('data-theme', t); }

  var saved = null;
  try { saved = localStorage.getItem(KEY); } catch (e) {}
  if (saved === 'dark' || saved === 'light') apply(saved);

  function current() {
    var attr = root.getAttribute('data-theme');
    if (attr) return attr;
    return (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light';
  }

  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  ready(function () {
    var nav = document.querySelector('.entete-nav') || document.querySelector('.entete-nav nav');
    if (!nav) return;
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'bascule-theme';
    btn.setAttribute('aria-label', 'Basculer le mode sombre');
    function label() { btn.textContent = current() === 'dark' ? '\u2600 Clair' : '\u263e Sombre'; }
    label();
    btn.addEventListener('click', function () {
      var next = current() === 'dark' ? 'light' : 'dark';
      apply(next);
      try { localStorage.setItem(KEY, next); } catch (e) {}
      label();
    });
    nav.appendChild(btn);
  });
})();

/* Le Vrai Vote — cartes de vote repliables sur mobile.
   Amélioration progressive : sans JS, tout reste déplié (aucune info
   cachée). Sur mobile, chaque carte devient un bouton accessible au
   clavier (Entrée/Espace) qui déplie le détail ; les liens restent
   cliquables sans déplier. Desktop : inchangé. */
(function () {
  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }
  ready(function () {
    if (!window.matchMedia) return;
    var mq = window.matchMedia('(max-width:640px)');
    var cards = [].slice.call(document.querySelectorAll('.vote-carte'));
    if (!cards.length) return;
    function toggle(card, e) {
      if (e && e.target && e.target.closest && e.target.closest('a')) return;
      var open = card.classList.toggle('open');
      card.setAttribute('aria-expanded', open ? 'true' : 'false');
    }
    function onClick(e) { toggle(e.currentTarget, e); }
    function onKey(e) {
      if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') {
        if (e.target.closest && e.target.closest('a')) return;
        e.preventDefault();
        toggle(e.currentTarget, null);
      }
    }
    function apply() {
      cards.forEach(function (c) {
        if (mq.matches) {
          if (c.dataset.coll) return;
          c.dataset.coll = '1';
          c.classList.add('collapsible');
          c.setAttribute('role', 'button');
          c.setAttribute('tabindex', '0');
          c.setAttribute('aria-expanded', 'false');
          c.addEventListener('click', onClick);
          c.addEventListener('keydown', onKey);
        } else if (c.dataset.coll) {
          delete c.dataset.coll;
          c.classList.remove('collapsible', 'open');
          c.removeAttribute('role');
          c.removeAttribute('tabindex');
          c.removeAttribute('aria-expanded');
          c.removeEventListener('click', onClick);
          c.removeEventListener('keydown', onKey);
        }
      });
    }
    apply();
    if (mq.addEventListener) mq.addEventListener('change', apply);
    else if (mq.addListener) mq.addListener(apply);
  });
})();
