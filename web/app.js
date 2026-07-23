// Le Vrai Vote — v0. Rend data.json (généré depuis la base sourcée).
"use strict";

function el(tag, classe, texte) {
  const e = document.createElement(tag);
  if (classe) e.className = classe;
  if (texte !== undefined) e.textContent = texte;
  return e;
}

function dateFr(iso) {
  if (!iso) return null;
  const [a, m, j] = iso.split("-");
  return `${j}/${m}/${a}`;
}

function ligneCandidat(c) {
  const li = el("li");
  const nom = el("span", "nom", c.nom);
  li.appendChild(nom);
  if (c.donnees_disponibles) {
    li.appendChild(document.createTextNode(" "));
    li.appendChild(el("span", "badge badge-neutre", "données ci-dessous"));
  }
  const detail = el("span", "detail",
    c.detail.split(" — ")[0] + (c.date_declaration ? ` · déclaré(e) le ${dateFr(c.date_declaration)}` : " · date non fournie par la source"));
  li.appendChild(detail);
  const source = el("span", "source");
  const a = el("a", null, "source");
  a.href = c.source;
  a.rel = "noopener";
  source.appendChild(a);
  li.appendChild(source);
  return li;
}

function badge(libelle, classe, valeur) {
  return el("span", `badge ${classe}`, `${libelle} : ${valeur}`);
}

function carteProfil(slug, p) {
  const carte = el("article", "profil");
  carte.id = slug;
  carte.appendChild(el("h3", null, p.nom));
  carte.appendChild(el("p", "naissance",
    p.naissance ? `Né(e) le ${dateFr(p.naissance)} — source : open data officiel (AN, HATVP ou PE)` : "Date de naissance : à importer"));

  carte.appendChild(el("h4", null, "Mandats (sources officielles, datés)"));
  const ul = el("ul", "mandats");
  for (const m of p.mandats) {
    const li = el("li");
    li.appendChild(el("strong", null, m.libelle));
    const fin = m.fin ? dateFr(m.fin) : "en cours";
    const precision = m.precision === "mois" ? " (précision au mois)" : "";
    li.appendChild(el("span", "dates", ` — ${dateFr(m.debut)} → ${fin}${precision}`));
    ul.appendChild(li);
  }
  carte.appendChild(ul);

  carte.appendChild(el("h4", null, "Positions de vote en base (Assemblée nationale, 2017-2026)"));
  const badges = el("div", "badges");
  const d = p.positions.detail;
  if (p.positions.exprimees === 0 && p.positions.absences_inferees === 0) {
    badges.appendChild(el("span", "badge badge-neutre",
      "non concerné sur la période couverte (aucun mandat de député actif entre 2017 et 2026)"));
  } else {
    if (d.pour) badges.appendChild(badge("pour", "badge-pour", d.pour));
    if (d.contre) badges.appendChild(badge("contre", "badge-contre", d.contre));
    if (d.abstention) badges.appendChild(badge("abstention", "badge-abstention", d.abstention));
    if (d.non_votant) badges.appendChild(badge("non-votant", "badge-nonvotant", d.non_votant));
    if (d.absent) badges.appendChild(badge("absent (déduit)", "badge-absent", d.absent));
  }
  carte.appendChild(badges);

  if (p.solennels_l17) {
    const taux = (100 * p.solennels_l17.present / p.solennels_l17.total).toFixed(1).replace(".", ",");
    carte.appendChild(el("p", "naissance",
      `Participation aux scrutins solennels de la législature en cours : ${p.solennels_l17.present}/${p.solennels_l17.total} (${taux} %). Les scrutins solennels sont les votes d'ensemble annoncés à l'avance, référence usuelle de l'assiduité.`));
  }
  return carte;
}

fetch("data.json")
  .then((r) => r.json())
  .then((donnees) => {
    document.getElementById("avertissement").textContent = donnees.meta.avertissement;
    document.getElementById("note-bardella").textContent = donnees.note_bardella;

    const declares = document.getElementById("liste-declares");
    const primaires = document.getElementById("liste-primaires");
    for (const c of donnees.candidats) {
      (c.statut === "declaree" ? declares : primaires).appendChild(ligneCandidat(c));
    }

    const profils = document.getElementById("profils");
    for (const [slug, p] of Object.entries(donnees.profils)) {
      profils.appendChild(carteProfil(slug, p));
    }

    document.getElementById("meta-maj").textContent =
      `Données générées le ${dateFr(donnees.meta.genere_le)} — ${donnees.meta.scrutins_en_base.toLocaleString("fr-FR")} scrutins en base. ` +
      donnees.meta.perimetre_scrutins;
  })
  .catch(() => {
    document.getElementById("profils").textContent =
      "Impossible de charger les données (data.json). Réessayez plus tard.";
  });
