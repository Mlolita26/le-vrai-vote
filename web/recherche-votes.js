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

  function appliquerA(champ) {
    var mots = sansAccent(champ.value).split(/\s+/).filter(Boolean);
    var selCarte = champ.dataset.cartes;
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
      if (ok) trouves++;
    });

    // Un conteneur vidé de toutes ses cartes se masque aussi : sinon il ne
    // reste que son titre de section, ce qui se lit comme un résultat.
    (champ.dataset.groupes || "").split(",").forEach(function (sel) {
      sel = sel.trim();
      if (!sel) return;
      document.querySelectorAll(sel).forEach(function (g) {
        var restants = g.querySelectorAll(selCarte + ":not(.hors-recherche)").length;
        g.classList.toggle("hors-recherche", mots.length > 0 && restants === 0);
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

    var compte = champ.parentNode.querySelector(".recherche-compte");
    if (compte) {
      compte.textContent = !mots.length ? ""
        : trouves === 0
          ? "Aucun vote clé ne correspond. Essayez un mot plus court, ou un thème."
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
