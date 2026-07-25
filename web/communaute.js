/* Le Vrai Vote — « Communauté » côté navigateur.
 *
 * 1) Ampoule « m'a aidé à décider » sur chaque vote clé (élément [data-vote-id]).
 *    - injectée au chargement + sur les cartes ajoutées dynamiquement (comparateur) ;
 *    - 1 vote par appareil (localStorage), réversible ;
 *    - le compteur vient du service (window.LVV_API) ; sans service, mode « bientôt ».
 * 2) Classement des lois les plus utiles sur la page Communauté (#lvv-classement).
 *
 * Aucune dépendance. Ne casse jamais la page si le service est absent ou en panne.
 */
(function () {
  "use strict";
  var API = (window.LVV_API || "").replace(/\/+$/, "");
  var counts = {};          // uid -> nombre (rempli depuis /counts)
  var loaded = false;

  function vkey(uid) { return "lvv_v_" + uid; }
  function hasVoted(uid) { try { return localStorage.getItem(vkey(uid)) === "1"; } catch (e) { return false; } }
  function setVoted(uid, v) { try { v ? localStorage.setItem(vkey(uid), "1") : localStorage.removeItem(vkey(uid)); } catch (e) {} }

  function fmt(n) { return (n || 0).toLocaleString("fr-FR"); }

  // ── Ampoules ───────────────────────────────────────────────────────────────
  function bulbFor(el) {
    if (el.querySelector(":scope > .lvv-bulb")) return; // déjà posée
    var uid = el.getAttribute("data-vote-id");
    if (!uid) return;
    var b = document.createElement("button");
    b.type = "button";
    b.className = "lvv-bulb";
    b.setAttribute("data-uid", uid);
    b.setAttribute("aria-pressed", hasVoted(uid) ? "true" : "false");
    if (hasVoted(uid)) b.classList.add("voted");
    b.innerHTML = '<span class="lvv-ico" aria-hidden="true">💡</span>' +
      '<span class="lvv-lbl">m\'a aidé à décider</span>' +
      '<span class="lvv-n"></span>';
    if (!API) {
      b.classList.add("lvv-soon");
      b.title = "Vote communautaire bientôt activé";
    }
    b.addEventListener("click", onVote);
    el.appendChild(b);
    refreshBulb(b);
  }

  function refreshBulb(b) {
    var uid = b.getAttribute("data-uid");
    var n = counts[uid] || 0;
    var span = b.querySelector(".lvv-n");
    span.textContent = API ? fmt(n) : "";
    b.classList.toggle("has-count", API && n > 0);
  }

  function onVote(e) {
    e.preventDefault();
    var b = e.currentTarget;
    var uid = b.getAttribute("data-uid");
    if (!API) { flash(b, "Bientôt disponible"); return; }
    var voting = !hasVoted(uid);
    // Optimiste : on met à jour l'affichage tout de suite.
    counts[uid] = Math.max(0, (counts[uid] || 0) + (voting ? 1 : -1));
    setVoted(uid, voting);
    b.classList.toggle("voted", voting);
    b.setAttribute("aria-pressed", voting ? "true" : "false");
    refreshBulb(b);
    fetch(API + (voting ? "/vote" : "/unvote"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ uid: uid }),
    }).then(function (r) { return r.json(); }).then(function (d) {
      if (d && typeof d.count === "number") { counts[uid] = d.count; refreshBulb(b); }
    }).catch(function () { /* réseau : on garde l'estimation optimiste */ });
  }

  function flash(b, msg) {
    var t = document.createElement("span");
    t.className = "lvv-flash";
    t.textContent = msg;
    b.appendChild(t);
    setTimeout(function () { t.remove(); }, 1800);
  }

  function scan(root) {
    var nodes = (root || document).querySelectorAll("[data-vote-id]");
    for (var i = 0; i < nodes.length; i++) bulbFor(nodes[i]);
  }

  function loadCounts() {
    if (!API) return Promise.resolve();
    return fetch(API + "/counts").then(function (r) { return r.json(); })
      .then(function (d) { counts = d || {}; loaded = true; refreshAll(); })
      .catch(function () { /* service indisponible : ampoules sans compteur */ });
  }
  function refreshAll() {
    var b = document.querySelectorAll(".lvv-bulb");
    for (var i = 0; i < b.length; i++) refreshBulb(b[i]);
  }

  // ── Classement (page Communauté) ────────────────────────────────────────────
  function renderClassement() {
    var box = document.getElementById("lvv-classement");
    if (!box) return;
    if (!API) {
      box.innerHTML = '<p class="lvv-vide">Le vote communautaire s\'active très bientôt. ' +
        'Revenez pour découvrir les lois que les visiteurs jugent les plus utiles pour se décider.</p>';
      return;
    }
    Promise.all([
      fetch("../data.json").then(function (r) { return r.json(); }).catch(function () { return null; }),
      fetch(API + "/counts").then(function (r) { return r.json(); }).catch(function () { return {}; }),
    ]).then(function (res) {
      var data = res[0], c = res[1] || {};
      if (!data || !data.votes) { box.innerHTML = '<p class="lvv-vide">Classement momentanément indisponible.</p>'; return; }
      var votesBase = box.getAttribute("data-votes") || "";
      var rows = data.votes.map(function (v) {
        return { slug: v.slug, uid: v.uid, titre: v.titre, theme: v.theme, n: c[v.uid] || 0 };
      }).filter(function (r) { return r.n > 0; })
        .sort(function (a, b) { return b.n - a.n; });
      if (!rows.length) {
        box.innerHTML = '<p class="lvv-vide">Personne n\'a encore signalé de loi utile. ' +
          'Soyez le premier : cliquez sur l\'ampoule 💡 à côté d\'un vote clé.</p>';
        return;
      }
      box.innerHTML = rangHtml(rows, 25, votesBase);
    });
  }
  function esc(s) { var d = document.createElement("div"); d.textContent = s == null ? "" : s; return d.innerHTML; }

  // Construit le <ol> du classement. Chaque ligne devient un lien vers la page
  // détail du vote (votesBase + slug) quand ces infos sont disponibles.
  function rangHtml(rows, limit, votesBase, extraClass) {
    var max = rows[0].n;
    var out = '<ol class="lvv-rang' + (extraClass ? " " + extraClass : "") + '">';
    rows.slice(0, limit).forEach(function (r) {
      var pct = Math.round(100 * r.n / max);
      var inner = '<div class="lvv-rang-tete"><span class="lvv-rang-titre">' + esc(r.titre) +
        '</span><span class="lvv-rang-n">' + fmt(r.n) + '</span></div>' +
        '<div class="lvv-rang-theme">' + esc(r.theme || "") + '</div>' +
        '<div class="lvv-jauge"><span style="width:' + pct + '%"></span></div>';
      var href = (votesBase && r.slug) ? (votesBase + r.slug + "/") : null;
      out += "<li>" + (href ? '<a class="lvv-rang-lien" href="' + href + '">' + inner + "</a>" : inner) + "</li>";
    });
    return out + "</ol>";
  }

  // ── Aperçu « top votes » (page d'accueil) ────────────────────────────────────
  function renderAccueil() {
    var box = document.getElementById("lvv-accueil");
    if (!box) return;
    if (!API) { box.style.display = "none"; return; } // service non branché : rien sur l'accueil
    var src = box.getAttribute("data-src") || "data.json";
    var lien = box.getAttribute("data-lien") || "communaute/";
    var tete = '<div class="accueil-top-tete"><h2>Les votes qui aident le plus à se décider</h2>' +
      '<a class="accueil-top-lien" href="' + lien + '">Voir le classement complet →</a></div>';
    Promise.all([
      fetch(src).then(function (r) { return r.json(); }).catch(function () { return null; }),
      fetch(API + "/counts").then(function (r) { return r.json(); }).catch(function () { return {}; }),
    ]).then(function (res) {
      var data = res[0], c = res[1] || {};
      if (!data || !data.votes) { box.style.display = "none"; return; } // data.json injoignable : on masque
      var votesBase = box.getAttribute("data-votes") || "";
      var rows = data.votes.map(function (v) {
        return { slug: v.slug, titre: v.titre, theme: v.theme, n: c[v.uid] || 0 };
      }).filter(function (r) { return r.n > 0; })
        .sort(function (a, b) { return b.n - a.n; }).slice(0, 10);
      if (!rows.length) {
        box.innerHTML = tete + '<p class="lvv-vide">Personne n\'a encore signalé de vote utile. ' +
          'Cliquez sur l\'ampoule 💡 « m\'a aidé à décider » à côté d\'un vote pour lancer le classement.</p>';
        return;
      }
      box.innerHTML = tete + rangHtml(rows, 10, votesBase, "lvv-rang-accueil");
    });
  }

  // ── Init ─────────────────────────────────────────────────────────────────────
  function init() {
    scan(document);
    loadCounts();
    renderClassement();
    renderAccueil();
    // Cartes ajoutées dynamiquement (comparateur) : on pose les ampoules à la volée.
    if (window.MutationObserver) {
      var mo = new MutationObserver(function (muts) {
        for (var i = 0; i < muts.length; i++) {
          var added = muts[i].addedNodes;
          for (var j = 0; j < added.length; j++) {
            var n = added[j];
            if (n.nodeType !== 1) continue;
            if (n.matches && n.matches("[data-vote-id]")) bulbFor(n);
            if (n.querySelectorAll) scan(n);
          }
        }
      });
      mo.observe(document.body, { childList: true, subtree: true });
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
