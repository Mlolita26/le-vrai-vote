/* Le Vrai Vote — recherche d'une loi dans une liste de votes clés.
   Utilisée sur la fiche d'un candidat et sur le comparateur.

   Amélioration progressive : le champ est livré avec l'attribut `hidden` et
   n'est révélé que par ce script. Un champ de recherche inerte est pire qu'un
   champ absent — l'utilisateur tape et rien ne se passe, sans comprendre.

   La recherche ignore accents et casse : « nucleaire » trouve « nucléaire ».
   C'est la raison d'être du script — sans cela, la moitié des recherches
   françaises tapées au clavier échoueraient. Elle porte sur le titre ET le
   résumé du vote : plusieurs sujets n'apparaissent que dans le résumé (aucun
   titre ne contient « pesticide », un résumé oui).

   Contrat côté HTML :
     <div class="recherche-votes" hidden>
       <label for="…">…</label>
       <input data-recherche-votes
              data-cartes="<sélecteur d'UNE carte>"      (un seul sélecteur)
              data-groupes="<sélecteurs de conteneurs>"  (séparés par des virgules)
              data-reset-filtres="<sélecteurs de barres de puces>">
       <p class="recherche-compte" role="status" aria-live="polite"></p>
     </div>
*/
(function () {
  // Les diacritiques combinants, isolés par la décomposition NFD. Construit
  // via RegExp à partir d'échappements ASCII : écrits en littéraux dans le
  // source, ces caractères sont invisibles dans un éditeur et se perdraient au
  // premier changement d'encodage du fichier.
  var DIACRITIQUES = new RegExp("[\u0300-\u036f]", "g");

  function sansAccent(s) {
    return (s || "").normalize("NFD").replace(DIACRITIQUES, "").toLowerCase();
  }

  // Le texte normalisé est mémorisé sur l'élément lui-même, pas dans un
  // attribut data- : les résumés cumulés pèsent ~80 ko qu'il serait absurde
  // d'écrire dans le DOM. Le comparateur recrée ses cartes à chaque rendu,
  // le cache se renouvelle donc tout seul.
  function texte(el) {
    if (el._lvvTexte === undefined) el._lvvTexte = sansAccent(el.textContent);
    return el._lvvTexte;
  }

  function champs() {
    return [].slice.call(document.querySelectorAll("[data-recherche-votes]"));
  }

  /* Vrai dès qu'une recherche est en cours : les filtres à puces s'en servent
     pour ne pas replacer la page en haut pendant la frappe. */
  function active() {
    return champs().some(function (c) { return c.value.trim() !== ""; });
  }

  /* Une recherche doit balayer tous les thèmes, sinon « nucléaire » ne trouve
     rien quand un thème est sélectionné. On remet donc les puces sur « tous »
     en simulant le clic, plutôt qu'en dupliquant leur logique. */
  function remetFiltresAZero(champ) {
    var sel = champ.dataset.resetFiltres;
    if (!sel) return;
    document.querySelectorAll(sel).forEach(function (barre) {
      var tout = barre.querySelector('.filtre-chip[data-cible="tous"]');
      if (tout && !tout.classList.contains("actif")) tout.click();
    });
  }

  /* Rang d'une carte : 0 quand tous les mots cherchés figurent dans le titre,
     puis un cran par mot absent du titre. Une loi dont l'intitulé porte le mot
     passe donc avant celle qui ne le mentionne que dans son résumé. */
  function rangDe(carte, mots, selTitre) {
    if (!mots.length || !selTitre) return 0;
    var t = carte.querySelector(selTitre);
    var titre = t ? sansAccent(t.textContent) : "";
    var dedans = 0;
    mots.forEach(function (m) { if (titre.indexOf(m) >= 0) dedans++; });
    return mots.length - dedans;
  }

  /* Ordre d'origine d'un conteneur, mémorisé au premier passage : le tri part
     toujours de lui, jamais du résultat du tri précédent. Sans cela l'ordre
     dériverait de frappe en frappe et ne serait plus restituable. */
  function ordreOriginal(parent, elements) {
    if (!parent._lvvOrdre) parent._lvvOrdre = elements.slice();
    return parent._lvvOrdre.filter(function (n) { return n.parentNode === parent; });
  }

  /* Repose `elements` dans cet ordre, à l'emplacement qu'occupait le premier.
     L'ancre évite de les envoyer à la fin du conteneur : un bloc de thème
     commence par son titre, un groupe par son intitulé de sous-catégorie. */
  function placer(parent, elements) {
    if (elements.length < 2) return;
    var ancre = document.createComment("lvv-ordre");
    parent.insertBefore(ancre, elements[0]);
    elements.forEach(function (n) { parent.insertBefore(n, ancre); });
    parent.removeChild(ancre);
  }

  function trier(parent, elements, rang) {
    var base = ordreOriginal(parent, elements);
    // Array.prototype.sort est stable : à rang égal, l'ordre éditorial d'origine
    // (par thème puis par date) est conservé.
    placer(parent, base.slice().sort(function (a, b) { return rang(a) - rang(b); }));
  }

  /* Regroupe des éléments par conteneur parent, pour ne trier qu'entre frères. */
  function parParent(elements) {
    var paires = [];
    elements.forEach(function (n) {
      var p = n.parentNode;
      if (!p) return;
      var entree = paires.filter(function (x) { return x.parent === p; })[0];
      if (!entree) { entree = { parent: p, enfants: [] }; paires.push(entree); }
      entree.enfants.push(n);
    });
    return paires;
  }

  function appliquerA(champ) {
    var mots = sansAccent(champ.value).split(/\s+/).filter(Boolean);
    var selCarte = champ.dataset.cartes;
    var selTitre = champ.dataset.titre;
    if (!selCarte) return;
    if (mots.length) remetFiltresAZero(champ);

    var cartes = [].slice.call(document.querySelectorAll(selCarte));
    var trouves = 0;
    cartes.forEach(function (c) {
      var t = texte(c);
      // Tous les mots doivent être présents : « loi nucleaire » est plus
      // précis que « loi » ou « nucleaire ».
      var ok = mots.every(function (m) { return t.indexOf(m) >= 0; });
      c.classList.toggle("hors-recherche", !ok);
      c._lvvRang = ok ? rangDe(c, mots, selTitre) : Infinity;
      if (ok) trouves++;
    });

    // Titres d'abord, à l'intérieur de chaque liste.
    parParent(cartes).forEach(function (g) {
      trier(g.parent, g.enfants, function (c) { return c._lvvRang; });
    });

    // Un conteneur vidé de toutes ses cartes se masque aussi : sinon il ne
    // reste que son titre de section, ce qui se lit comme un résultat. Les
    // conteneurs restants remontent selon leur meilleure carte : sans cela,
    // un titre trouvé dans un thème tardif resterait sous les résultats de
    // résumé d'un thème antérieur, et le classement ne se verrait pas.
    (champ.dataset.groupes || "").split(",").forEach(function (sel) {
      sel = sel.trim();
      if (!sel) return;
      var groupes = [].slice.call(document.querySelectorAll(sel));
      groupes.forEach(function (g) {
        var restants = g.querySelectorAll(selCarte + ":not(.hors-recherche)");
        g.classList.toggle("hors-recherche", mots.length > 0 && restants.length === 0);
        var meilleur = Infinity;
        [].forEach.call(restants, function (c) {
          if (c._lvvRang < meilleur) meilleur = c._lvvRang;
        });
        g._lvvRang = mots.length ? meilleur : 0;
      });
      parParent(groupes).forEach(function (x) {
        trier(x.parent, x.enfants, function (g) { return g._lvvRang; });
      });
    });

    // Les barres de puces se retirent pendant une recherche. Elles viennent
    // d'être remises sur « tous », elles n'ont donc plus de rôle ; et sur
    // mobile les quinze puces de thème occupent cinq rangées, qu'il faudrait
    // franchir avant d'apercevoir les résultats — l'inverse du but recherché.
    (champ.dataset.resetFiltres || "").split(",").forEach(function (sel) {
      sel = sel.trim();
      if (!sel) return;
      document.querySelectorAll(sel).forEach(function (barre) {
        barre.classList.toggle("hors-recherche", mots.length > 0);
      });
    });

    // Recherche infructueuse : on affiche l'explication et l'accès à la
    // proposition de loi. Le terme cherché est réinjecté par textContent, pas
    // par innerHTML : c'est une saisie libre, elle ne doit jamais être
    // interprétée comme du balisage.
    var vide = champ.parentNode.querySelector(".recherche-vide");
    if (vide) vide.hidden = !(mots.length && trouves === 0);

    var compte = champ.parentNode.querySelector(".recherche-compte");
    if (compte) {
      // Le conseil (« essayez un mot plus court ») a migré dans le bloc
      // .recherche-vide : le répéter ici le ferait annoncer deux fois.
      compte.textContent = !mots.length ? ""
        : trouves === 0
          ? "Aucun vote clé ne correspond à « " + champ.value.trim() + " »."
          : trouves + (trouves > 1 ? " votes clés trouvés" : " vote clé trouvé")
            + " sur " + cartes.length + ".";
    }
  }

  function appliquer() { champs().forEach(appliquerA); }

  function initialiser() {
    champs().forEach(function (champ) {
      var boite = champ.closest(".recherche-votes");
      if (boite) boite.hidden = false;
      champ.addEventListener("input", function () { appliquerA(champ); });
      // Échap vide le champ et rétablit la liste complète.
      champ.addEventListener("keydown", function (ev) {
        if (ev.key === "Escape" && champ.value) {
          ev.preventDefault();
          champ.value = "";
          appliquerA(champ);
        }
      });
      // Un champ pré-rempli par le navigateur (retour arrière) doit filtrer.
      if (champ.value.trim()) appliquerA(champ);
    });
  }

  // Exposé pour le comparateur, qui reconstruit ses cartes à chaque rendu et
  // doit donc réappliquer la recherche en cours.
  window.LVVRechercheVotes = { appliquer: appliquer, active: active };

  if (document.readyState !== "loading") initialiser();
  else document.addEventListener("DOMContentLoaded", initialiser);
})();
