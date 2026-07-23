import React, { useState, useMemo } from "react";

// ── DÉMONSTRATION ──────────────────────────────────────────────────────────
// Candidats FICTIFS. Aucune donnée réelle. Ils illustrent les archétypes
// définis (parlementaire, ministre non-élu, société civile…) et la logique
// d'affichage à trois états : position connue / non concerné / indisponible.
// Le pipeline réel remplacera ces données par les scrutins officiels vérifiés.

const THEMES = [
  { id: "eco", label: "Écologie & agriculture", icon: "🌱" },
  { id: "pouvoir", label: "Pouvoir d'achat & fiscalité", icon: "💶" },
  { id: "secu", label: "Sécurité & justice", icon: "⚖️" },
  { id: "immig", label: "Immigration", icon: "🛂" },
  { id: "societe", label: "Questions de société", icon: "🏛️" },
  { id: "europe", label: "Europe & international", icon: "🌍" },
];

// Votes clés par thème (fictifs mais plausibles)
const VOTES = {
  // resume : phrase neutre décrivant ce que contient le texte (pas de jugement).
  // sourceResume : lien vers le dossier législatif officiel, pour vérification.
  eco: [
    { id: "duplomb", titre: "Loi Duplomb (néonicotinoïdes)", date: "2025-07-08",
      resume: "Autorise à titre dérogatoire la réintroduction d'un pesticide néonicotinoïde interdit depuis 2018.",
      sourceResume: "https://www.assemblee-nationale.fr/dyn/17/dossiers" },
    { id: "climat", titre: "Loi Climat et Résilience", date: "2021-05-04",
      resume: "Traduit une partie des propositions de la Convention citoyenne : rénovation des logements, encadrement de la publicité, artificialisation des sols.",
      sourceResume: "https://www.assemblee-nationale.fr/dyn/15/dossiers" },
    { id: "ceta", titre: "Ratification du CETA", date: "2019-07-23",
      resume: "Approuve l'accord de libre-échange entre l'Union européenne et le Canada.",
      sourceResume: "https://www.assemblee-nationale.fr/dyn/15/dossiers" },
  ],
  pouvoir: [
    { id: "retraites", titre: "Réforme des retraites (64 ans)", date: "2023-03-16",
      resume: "Repousse progressivement l'âge légal de départ de 62 à 64 ans et allonge la durée de cotisation.",
      sourceResume: "https://www.assemblee-nationale.fr/dyn/16/dossiers" },
    { id: "zucman", titre: "Taxe Zucman sur les hauts patrimoines", date: "2025-10-20",
      resume: "Instaure un impôt plancher sur les patrimoines supérieurs à 100 millions d'euros.",
      sourceResume: "https://www.assemblee-nationale.fr/dyn/17/dossiers" },
    { id: "isf", titre: "Suppression de l'ISF", date: "2017-10-23",
      resume: "Remplace l'impôt sur la fortune par un impôt limité au seul patrimoine immobilier (IFI).",
      sourceResume: "https://www.assemblee-nationale.fr/dyn/15/dossiers" },
  ],
  secu: [
    { id: "legdef", titre: "Présomption de légitime défense (police)", date: "2026-01-14",
      resume: "Étend les conditions dans lesquelles l'usage de leur arme par les forces de l'ordre est présumé légitime.",
      sourceResume: "https://www.assemblee-nationale.fr/dyn/17/dossiers" },
    { id: "narco", titre: "Loi narcotrafic", date: "2025-03-27",
      resume: "Renforce les moyens d'enquête et crée un parquet national dédié à la lutte contre le trafic de stupéfiants.",
      sourceResume: "https://www.assemblee-nationale.fr/dyn/17/dossiers" },
  ],
  immig: [
    { id: "immig23", titre: "Loi immigration (version durcie)", date: "2023-12-19",
      resume: "Modifie les conditions de séjour, de regroupement familial et d'accès à certaines prestations pour les étrangers.",
      sourceResume: "https://www.assemblee-nationale.fr/dyn/16/dossiers" },
    { id: "ame", titre: "Suppression de l'AME", date: "2024-11-05",
      resume: "Propose de remplacer l'aide médicale d'État par un dispositif d'aide d'urgence au périmètre réduit.",
      sourceResume: "https://www.assemblee-nationale.fr/dyn/17/dossiers" },
  ],
  societe: [
    { id: "ivg", titre: "IVG dans la Constitution", date: "2024-03-04",
      resume: "Inscrit la liberté de recourir à l'interruption volontaire de grossesse dans la Constitution.",
      sourceResume: "https://www.assemblee-nationale.fr/dyn/16/dossiers" },
    { id: "finvie", titre: "Droit à l'aide à mourir", date: "2025-05-27",
      resume: "Crée un droit encadré à l'aide à mourir pour les personnes atteintes d'une maladie grave et incurable.",
      sourceResume: "https://www.assemblee-nationale.fr/dyn/17/dossiers" },
  ],
  europe: [
    { id: "ukraine", titre: "Soutien militaire à l'Ukraine", date: "2025-03-12",
      resume: "Approuve la poursuite du soutien militaire et financier de la France à l'Ukraine.",
      sourceResume: "https://www.assemblee-nationale.fr/dyn/17/dossiers" },
    { id: "mercosur", titre: "Opposition à l'accord Mercosur", date: "2024-11-26",
      resume: "Résolution demandant au gouvernement de s'opposer à la signature de l'accord commercial UE-Mercosur.",
      sourceResume: "https://www.assemblee-nationale.fr/dyn/17/dossiers" },
  ],
};

// Positions : "pour" | "contre" | "abstention" | "absent" | "nc" (non concerné)
// | null (donnée indisponible — jamais parlementaire)
// nuance : texte optionnel expliquant un vote contre-intuitif
const CANDIDATS = [
  {
    id: "perrin",
    nom: "Camille Perrin",
    parti: "Parti Vert-Démocrate (fictif)",
    archetype: "Députée 2017–2026",
    initiales: "CP",
    couleur: "#2E7D5B",
    presence: { scrutins: 74, medianeScrutins: 71, commission: 62, medianeCommission: 65 },
    votes: {
      duplomb: { pos: "contre" },
      climat: { pos: "contre", nuance: "Jugeait le texte insuffisant (explication de vote en séance)." },
      ceta: { pos: "contre" },
      retraites: { pos: "contre" },
      zucman: { pos: "pour" },
      isf: { pos: "nc" },
      legdef: { pos: "contre" },
      narco: { pos: "abstention" },
      immig23: { pos: "contre" },
      ame: { pos: "contre" },
      ivg: { pos: "pour" },
      finvie: { pos: "pour" },
      ukraine: { pos: "pour" },
      mercosur: { pos: "pour" },
    },
    judiciaire: [],
  },
  {
    id: "dubois",
    nom: "Antoine Dubois",
    parti: "Rassemblement Conservateur (fictif)",
    archetype: "Sénateur, ancien ministre",
    initiales: "AD",
    couleur: "#3A5A8C",
    presence: { scrutins: 81, medianeScrutins: 71, commission: 70, medianeCommission: 65 },
    votes: {
      duplomb: { pos: "pour" },
      climat: { pos: "pour" },
      ceta: { pos: "pour" },
      retraites: { pos: "pour" },
      zucman: { pos: "contre" },
      isf: { pos: "pour" },
      legdef: { pos: "pour" },
      narco: { pos: "pour" },
      immig23: { pos: "pour" },
      ame: { pos: "pour" },
      ivg: { pos: "abstention" },
      finvie: { pos: "contre" },
      ukraine: { pos: "pour" },
      mercosur: { pos: "abstention" },
    },
    judiciaire: [
      { statut: "Relaxe", date: "2019", detail: "Relaxé dans une affaire de financement (jugement définitif).", presomption: false },
    ],
  },
  {
    id: "nguyen",
    nom: "Léa Nguyen",
    parti: "Horizon Citoyen (fictif)",
    archetype: "Ministre non-parlementaire",
    initiales: "LN",
    couleur: "#8C5A3A",
    presence: null, // jamais parlementaire → pas de données de vote/présence
    votes: null,
    declarations: {
      eco: "Défend une transition « pragmatique », favorable au nucléaire (discours publics).",
      pouvoir: "Prône la baisse des charges plutôt que la hausse des impôts.",
      europe: "Europhile affirmée, pour un soutien accru à l'Ukraine.",
    },
    judiciaire: [],
  },
  {
    id: "moreau",
    nom: "Sacha Moreau",
    parti: "Sans étiquette (fictif)",
    archetype: "Société civile",
    initiales: "SM",
    couleur: "#6B4A8C",
    presence: null,
    votes: null,
    declarations: {
      pouvoir: "Programme axé sur le revenu universel (pas d'historique parlementaire).",
      societe: "Position pro-fin de vie exprimée publiquement.",
    },
    judiciaire: [
      { statut: "Information judiciaire en cours", date: "2026", detail: "Visé par une enquête pour un litige commercial. Présumé innocent.", presomption: true },
    ],
  },
];

const POS_STYLE = {
  pour: { bg: "#E1F5EE", fg: "#0F6E56", label: "Pour" },
  contre: { bg: "#FCEBEB", fg: "#A32D2D", label: "Contre" },
  abstention: { bg: "#FAEEDA", fg: "#854F0B", label: "Abstention" },
  absent: { bg: "#F1EFE8", fg: "#5F5E5A", label: "Absent" },
  nc: { bg: "transparent", fg: "#B4B2A9", label: "Non concerné" },
};

function Badge({ pos }) {
  if (pos == null) return <span style={{ fontSize: 12, color: "#B4B2A9", fontStyle: "italic" }}>indisponible</span>;
  const s = POS_STYLE[pos];
  return (
    <span style={{ fontSize: 12, padding: "3px 10px", borderRadius: 999, background: s.bg, color: s.fg, whiteSpace: "nowrap", border: pos === "nc" ? "0.5px dashed #D3D1C7" : "none" }}>
      {s.label}
    </span>
  );
}

function coverage(c) {
  if (!c.votes) return { pct: 0, label: "Aucun historique de vote" };
  const all = Object.values(VOTES).flat();
  const known = all.filter((v) => { const p = c.votes[v.id]; return p && p.pos !== "nc"; }).length;
  return { pct: Math.round((known / all.length) * 100), known, total: all.length };
}

export default function App() {
  const [view, setView] = useState({ page: "home" });
  const [q, setQ] = useState("");
  const [themeFilter, setThemeFilter] = useState("eco");
  const [cmp, setCmp] = useState(["perrin", "dubois"]);

  const filtered = useMemo(
    () => CANDIDATS.filter((c) => c.nom.toLowerCase().includes(q.toLowerCase()) || c.parti.toLowerCase().includes(q.toLowerCase())),
    [q]
  );

  return (
    <div style={{ fontFamily: "'Inter', system-ui, sans-serif", color: "#1A1A18", background: "#FBFAF7", minHeight: "100vh" }}>
      {/* Bandeau démo */}
      <div style={{ background: "#412402", color: "#FAC775", fontSize: 13, padding: "8px 16px", textAlign: "center", letterSpacing: 0.2 }}>
        Prototype — candidats fictifs, données illustratives. Aucune information ne concerne de personnes réelles.
      </div>

      {/* Header */}
      <header style={{ borderBottom: "0.5px solid #E0DDD3", padding: "16px 20px", display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap", background: "#fff" }}>
        <button onClick={() => setView({ page: "home" })} style={{ border: "none", background: "none", cursor: "pointer", padding: 0, textAlign: "left" }}>
          <div style={{ fontSize: 19, fontWeight: 700, letterSpacing: -0.4 }}>Le Vrai Vote</div>
          <div style={{ fontSize: 12, color: "#73726C" }}>Ce qu'ils votent, pas ce qu'ils disent · 2027</div>
        </button>
        <nav style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
          <NavBtn active={view.page === "home"} onClick={() => setView({ page: "home" })}>Candidats</NavBtn>
          <NavBtn active={view.page === "theme"} onClick={() => setView({ page: "theme" })}>Par thème</NavBtn>
          <NavBtn active={view.page === "compare"} onClick={() => setView({ page: "compare" })}>Comparer</NavBtn>
          <NavBtn active={view.page === "method"} onClick={() => setView({ page: "method" })}>Méthode</NavBtn>
        </nav>
      </header>

      <main style={{ maxWidth: 960, margin: "0 auto", padding: "28px 20px 80px" }}>
        {view.page === "home" && <Home q={q} setQ={setQ} filtered={filtered} open={(id) => setView({ page: "candidate", id })} />}
        {view.page === "candidate" && <Candidate c={CANDIDATS.find((x) => x.id === view.id)} onCompare={() => setView({ page: "compare" })} />}
        {view.page === "theme" && <ThemePage themeFilter={themeFilter} setThemeFilter={setThemeFilter} />}
        {view.page === "compare" && <Compare cmp={cmp} setCmp={setCmp} />}
        {view.page === "method" && <Method />}
      </main>

      <footer style={{ borderTop: "0.5px solid #E0DDD3", padding: "20px", textAlign: "center", fontSize: 12, color: "#9C9A92" }}>
        Données de démonstration · Dans la version réelle : « à jour au JJ/MM/AAAA », chaque vote lié à son scrutin officiel.
      </footer>
    </div>
  );
}

function NavBtn({ active, children, onClick }) {
  return (
    <button onClick={onClick} style={{ fontSize: 14, padding: "7px 14px", borderRadius: 999, cursor: "pointer", border: active ? "none" : "0.5px solid #E0DDD3", background: active ? "#1A1A18" : "transparent", color: active ? "#fff" : "#3D3D3A" }}>
      {children}
    </button>
  );
}

// ── ACCUEIL ──────────────────────────────────────────────────────────────
function Home({ q, setQ, filtered, open }) {
  return (
    <>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 32, fontWeight: 800, letterSpacing: -1, margin: "0 0 6px", lineHeight: 1.1 }}>
          Regardez leurs votes,<br />pas leurs promesses.
        </h1>
        <p style={{ fontSize: 15, color: "#73726C", margin: 0, maxWidth: 560 }}>
          Pour chaque candidat : ce qu'il a réellement voté à l'Assemblée, sa présence, son parcours — avec le lien vers chaque scrutin officiel.
        </p>
      </div>

      <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Rechercher un candidat ou un parti…"
        style={{ width: "100%", boxSizing: "border-box", padding: "12px 16px", fontSize: 15, borderRadius: 10, border: "0.5px solid #D3D1C7", marginBottom: 20, background: "#fff" }} />

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 14 }}>
        {filtered.map((c) => {
          const cov = coverage(c);
          return (
            <button key={c.id} onClick={() => open(c.id)}
              style={{ textAlign: "left", cursor: "pointer", background: "#fff", border: "0.5px solid #E0DDD3", borderRadius: 14, padding: 16 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
                <div style={{ width: 44, height: 44, borderRadius: "50%", background: c.couleur, color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: 15 }}>{c.initiales}</div>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 15 }}>{c.nom}</div>
                  <div style={{ fontSize: 12, color: "#73726C" }}>{c.archetype}</div>
                </div>
              </div>
              <div style={{ fontSize: 12, color: "#9C9A92", marginBottom: 8 }}>{c.parti}</div>
              <div style={{ fontSize: 12, color: c.votes ? "#0F6E56" : "#854F0B", background: c.votes ? "#E1F5EE" : "#FAEEDA", padding: "4px 10px", borderRadius: 999, display: "inline-block" }}>
                {c.votes ? `${cov.known}/${cov.total} votes documentés` : "Sans mandat parlementaire"}
              </div>
            </button>
          );
        })}
      </div>
    </>
  );
}

// ── FICHE CANDIDAT ─────────────────────────────────────────────────────────
function Candidate({ c, onCompare }) {
  const [tab, setTab] = useState("votes");
  const cov = coverage(c);
  return (
    <>
      <div style={{ background: "#fff", border: "0.5px solid #E0DDD3", borderRadius: 16, padding: 22 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
          <div style={{ width: 56, height: 56, borderRadius: "50%", background: c.couleur, color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: 18 }}>{c.initiales}</div>
          <div style={{ flex: 1, minWidth: 180 }}>
            <div style={{ fontSize: 20, fontWeight: 700 }}>{c.nom}</div>
            <div style={{ fontSize: 13, color: "#73726C" }}>{c.parti} · {c.archetype}</div>
          </div>
          <button onClick={onCompare} style={{ fontSize: 13, padding: "8px 16px", borderRadius: 999, border: "0.5px solid #E0DDD3", background: "transparent", cursor: "pointer" }}>Comparer →</button>
        </div>

        {/* Indicateurs */}
        {c.presence ? (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 12, marginTop: 18 }}>
            <Stat label="Présence scrutins solennels" value={`${c.presence.scrutins} %`} sub={`médiane : ${c.presence.medianeScrutins} %`} />
            <Stat label="Présence en commission" value={`${c.presence.commission} %`} sub={`médiane : ${c.presence.medianeCommission} %`} />
            <Stat label="Votes clés documentés" value={`${cov.known} / ${cov.total}`} sub="reste : hors mandat" />
          </div>
        ) : (
          <div style={{ marginTop: 18, background: "#FAEEDA", borderRadius: 10, padding: "12px 16px", fontSize: 13, color: "#854F0B" }}>
            Ce candidat n'a jamais exercé de mandat parlementaire. Ses positions sont issues de ses déclarations publiques, non de votes.
          </div>
        )}
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: 6, margin: "18px 0 14px", flexWrap: "wrap" }}>
        {["votes", "justice"].map((t) => (
          <button key={t} onClick={() => setTab(t)} style={{ fontSize: 13, padding: "6px 14px", borderRadius: 999, cursor: "pointer", border: tab === t ? "none" : "0.5px solid #E0DDD3", background: tab === t ? "#1A1A18" : "transparent", color: tab === t ? "#fff" : "#3D3D3A" }}>
            {t === "votes" ? (c.votes ? "Votes clés" : "Positions déclarées") : "Parcours judiciaire"}
          </button>
        ))}
      </div>

      {tab === "votes" && (
        c.votes ? (
          THEMES.filter((t) => VOTES[t.id]).map((t) => (
            <div key={t.id} style={{ marginBottom: 18 }}>
              <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>{t.icon} {t.label}</div>
              <div style={{ background: "#fff", border: "0.5px solid #E0DDD3", borderRadius: 10 }}>
                {VOTES[t.id].map((v, i) => {
                  const p = c.votes[v.id];
                  return (
                    <div key={v.id} style={{ padding: "12px 14px", borderBottom: i < VOTES[t.id].length - 1 ? "0.5px solid #EDEBE3" : "none" }}>
                      <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
                        <div style={{ flex: 1, fontSize: 14, fontWeight: 600 }}>{v.titre}</div>
                        <Badge pos={p?.pos ?? null} />
                      </div>
                      <div style={{ fontSize: 13, color: "#5F5E5A", lineHeight: 1.5, marginTop: 5 }}>{v.resume}</div>
                      <div style={{ fontSize: 12, color: "#9C9A92", marginTop: 5 }}>
                        {p?.nuance && <span style={{ color: "#854F0B" }}>ⓘ {p.nuance}<br /></span>}
                        Scrutin du {fmtDate(v.date)} · <a href={v.sourceResume} target="_blank" rel="noreferrer" style={{ color: "#185FA5", textDecoration: "none" }}>dossier officiel</a>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))
        ) : (
          <div style={{ background: "#fff", border: "0.5px solid #E0DDD3", borderRadius: 10, padding: 16 }}>
            {Object.entries(c.declarations).map(([tid, txt]) => {
              const th = THEMES.find((x) => x.id === tid);
              return (
                <div key={tid} style={{ marginBottom: 12 }}>
                  <div style={{ fontSize: 13, fontWeight: 600 }}>{th?.icon} {th?.label}</div>
                  <div style={{ fontSize: 13, color: "#5F5E5A" }}>{txt}</div>
                </div>
              );
            })}
          </div>
        )
      )}

      {tab === "justice" && (
        <div>
          {c.judiciaire.some((a) => a.presomption) && (
            <div style={{ background: "#F1EFE8", borderRadius: 8, padding: "10px 14px", fontSize: 12, color: "#5F5E5A", marginBottom: 12 }}>
              Les procédures en cours sont mentionnées dans le respect de la présomption d'innocence.
            </div>
          )}
          {c.judiciaire.length === 0 ? (
            <div style={{ fontSize: 14, color: "#73726C", padding: 16 }}>Aucune affaire judiciaire recensée dans les sources publiques.</div>
          ) : (
            c.judiciaire.map((a, i) => (
              <div key={i} style={{ background: "#fff", border: "0.5px solid #E0DDD3", borderRadius: 10, padding: "12px 16px", marginBottom: 8 }}>
                <div style={{ fontSize: 13, fontWeight: 600 }}>{a.statut} <span style={{ color: "#9C9A92", fontWeight: 400 }}>· {a.date}</span></div>
                <div style={{ fontSize: 13, color: "#5F5E5A" }}>{a.detail}</div>
              </div>
            ))
          )}
        </div>
      )}
    </>
  );
}

function Stat({ label, value, sub }) {
  return (
    <div style={{ background: "#F6F4EE", borderRadius: 8, padding: 14 }}>
      <div style={{ fontSize: 12, color: "#9C9A92" }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 700, margin: "2px 0" }}>{value}</div>
      <div style={{ fontSize: 12, color: "#73726C" }}>{sub}</div>
    </div>
  );
}

// ── PAR THÈME ──────────────────────────────────────────────────────────────
function ThemePage({ themeFilter, setThemeFilter }) {
  const votes = VOTES[themeFilter] || [];
  return (
    <>
      <h1 style={{ fontSize: 24, fontWeight: 700, margin: "0 0 14px" }}>Qui vote quoi, thème par thème</h1>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 20 }}>
        {THEMES.filter((t) => VOTES[t.id]).map((t) => (
          <button key={t.id} onClick={() => setThemeFilter(t.id)} style={{ fontSize: 13, padding: "7px 14px", borderRadius: 999, cursor: "pointer", border: themeFilter === t.id ? "none" : "0.5px solid #E0DDD3", background: themeFilter === t.id ? "#1A1A18" : "transparent", color: themeFilter === t.id ? "#fff" : "#3D3D3A" }}>
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      <div style={{ overflowX: "auto" }}>
        <table style={{ borderCollapse: "collapse", width: "100%", minWidth: 560, background: "#fff", borderRadius: 10, overflow: "hidden" }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", padding: "12px 14px", fontSize: 12, color: "#73726C", borderBottom: "0.5px solid #E0DDD3" }}>Vote clé</th>
              {CANDIDATS.map((c) => (
                <th key={c.id} style={{ padding: "12px 8px", fontSize: 12, borderBottom: "0.5px solid #E0DDD3", minWidth: 90 }}>
                  <div style={{ width: 30, height: 30, borderRadius: "50%", background: c.couleur, color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: 11, margin: "0 auto 4px" }}>{c.initiales}</div>
                  <div style={{ fontSize: 11, color: "#5F5E5A" }}>{c.nom.split(" ")[0]}</div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {votes.map((v, i) => (
              <tr key={v.id} style={{ borderBottom: i < votes.length - 1 ? "0.5px solid #EDEBE3" : "none" }}>
                <td style={{ padding: "11px 14px", fontSize: 13, maxWidth: 260 }}>
                  <div style={{ fontWeight: 600 }}>{v.titre}</div>
                  <div style={{ fontSize: 12, color: "#9C9A92", lineHeight: 1.45, marginTop: 3 }}>{v.resume}</div>
                </td>
                {CANDIDATS.map((c) => (
                  <td key={c.id} style={{ padding: "11px 8px", textAlign: "center" }}>
                    <Badge pos={c.votes ? (c.votes[v.id]?.pos ?? null) : null} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

// ── COMPARATEUR ────────────────────────────────────────────────────────────
function Compare({ cmp, setCmp }) {
  const set = (i, id) => { const n = [...cmp]; n[i] = id; setCmp(n); };
  const cands = cmp.map((id) => CANDIDATS.find((c) => c.id === id));
  const allVotes = THEMES.filter((t) => VOTES[t.id]);

  return (
    <>
      <h1 style={{ fontSize: 24, fontWeight: 700, margin: "0 0 6px" }}>Comparer deux candidats</h1>
      <p style={{ fontSize: 14, color: "#73726C", margin: "0 0 20px" }}>Positions côte à côte sur chaque vote clé.</p>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 24 }}>
        {[0, 1].map((i) => (
          <select key={i} value={cmp[i]} onChange={(e) => set(i, e.target.value)}
            style={{ padding: "10px 12px", fontSize: 14, borderRadius: 10, border: "0.5px solid #D3D1C7", background: "#fff" }}>
            {CANDIDATS.map((c) => <option key={c.id} value={c.id}>{c.nom}</option>)}
          </select>
        ))}
      </div>

      {allVotes.map((t) => (
        <div key={t.id} style={{ marginBottom: 18 }}>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>{t.icon} {t.label}</div>
          <div style={{ background: "#fff", border: "0.5px solid #E0DDD3", borderRadius: 10 }}>
            {VOTES[t.id].map((v, i) => {
              const a = cands[0]?.votes ? (cands[0].votes[v.id]?.pos ?? null) : null;
              const b = cands[1]?.votes ? (cands[1].votes[v.id]?.pos ?? null) : null;
              const diff = a && b && a !== b && a !== "nc" && b !== "nc";
              return (
                <div key={v.id} style={{ padding: "11px 14px", borderBottom: i < VOTES[t.id].length - 1 ? "0.5px solid #EDEBE3" : "none", background: diff ? "#FDF9F0" : "transparent" }}>
                  <div style={{ fontSize: 14, fontWeight: 600 }}>{v.titre}{diff && <span style={{ fontSize: 11, color: "#854F0B", marginLeft: 6, fontWeight: 400 }}>● divergent</span>}</div>
                  <div style={{ fontSize: 12, color: "#9C9A92", lineHeight: 1.45, margin: "4px 0 8px" }}>{v.resume}</div>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
                    <div style={{ flex: 1 }}><Badge pos={a} /></div>
                    <div style={{ flex: 1, textAlign: "right" }}><Badge pos={b} /></div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </>
  );
}

// ── MÉTHODE ────────────────────────────────────────────────────────────────
function Method() {
  return (
    <div style={{ maxWidth: 620 }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, margin: "0 0 14px" }}>Notre méthode</h1>
      {[
        ["D'où viennent les données ?", "Les votes proviennent de l'open data officiel de l'Assemblée nationale, du Sénat et du Parlement européen. Chaque position affichée renvoie au scrutin public correspondant, vérifiable en un clic."],
        ["Comment choisit-on les votes clés ?", "Selon des critères objectifs et publics : scrutins solennels, textes ayant fait l'objet d'un large débat public, votes clivants au sein des groupes. La grille de sélection est identique pour tous."],
        ["Les résumés de loi sont-ils neutres ?", "Chaque résumé décrit ce que contient le texte, sans jugement de valeur. Il est relu et renvoie au dossier législatif officiel, consultable en un clic sous chaque vote."],
        ["Pourquoi certaines cases sont vides ?", "Trois états distincts : position connue, « non concerné » (le candidat n'était pas en poste lors du vote), et « indisponible » (candidat n'ayant jamais été parlementaire). On ne comble jamais un vide par une supposition."],
        ["Et le volet judiciaire ?", "Uniquement des faits publics et sourcés. Les condamnations définitives sont distinguées des procédures en cours, ces dernières étant présentées dans le strict respect de la présomption d'innocence."],
      ].map(([q, a]) => (
        <div key={q} style={{ marginBottom: 18, paddingBottom: 18, borderBottom: "0.5px solid #EDEBE3" }}>
          <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>{q}</div>
          <div style={{ fontSize: 14, color: "#5F5E5A", lineHeight: 1.6 }}>{a}</div>
        </div>
      ))}
    </div>
  );
}

function fmtDate(iso) {
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}
