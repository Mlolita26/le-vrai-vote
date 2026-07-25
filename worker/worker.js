/**
 * Le Vrai Vote — service « Communauté » (Cloudflare Worker + D1).
 *
 * Compteur d'utilité par vote clé : les visiteurs signalent les lois qui les
 * ont aidés à se décider. Un seul compteur par loi (clé = uid officiel du
 * scrutin). Anti-abus : format d'uid validé (on ne peut pas créer de clé
 * arbitraire) + 1 vote par appareil géré côté client. Signal indicatif,
 * non représentatif — voir la page Méthode du site.
 *
 * Routes :
 *   GET  /counts        -> { "<uid>": <nombre>, ... }
 *   POST /vote {uid}     -> { uid, count }   (incrémente)
 *   POST /unvote {uid}   -> { uid, count }   (décrémente, min 0)
 *
 * Déploiement : voir worker/README.md.
 */
const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
  "Access-Control-Max-Age": "86400",
};

// uid officiels acceptés : Assemblée (VTANR/VTCGR), Parlement européen (PE-HTV),
// Sénat (SEN). Empêche l'écriture de clés fantaisistes.
const UID_RE = /^(VTANR5L\d+V\d+|VTCGR5L\d+V\d+|PE-HTV-\d+|SEN-\d{4}-\d+)$/;

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { ...CORS, "Content-Type": "application/json; charset=utf-8" },
  });
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") return new Response(null, { headers: CORS });
    const url = new URL(request.url);
    try {
      if (request.method === "GET" && url.pathname === "/counts") {
        const { results } = await env.DB.prepare("SELECT uid, count FROM votes").all();
        const out = {};
        for (const r of results) out[r.uid] = r.count;
        return json(out);
      }
      if (request.method === "POST" && (url.pathname === "/vote" || url.pathname === "/unvote")) {
        const body = await request.json().catch(() => ({}));
        const uid = String(body.uid || "");
        if (!UID_RE.test(uid)) return json({ error: "uid invalide" }, 400);
        if (url.pathname === "/vote") {
          await env.DB.prepare(
            "INSERT INTO votes (uid, count) VALUES (?1, 1) " +
            "ON CONFLICT(uid) DO UPDATE SET count = count + 1"
          ).bind(uid).run();
        } else {
          await env.DB.prepare(
            "UPDATE votes SET count = MAX(0, count - 1) WHERE uid = ?1"
          ).bind(uid).run();
        }
        const row = await env.DB.prepare("SELECT count FROM votes WHERE uid = ?1").bind(uid).first();
        return json({ uid, count: row ? row.count : 0 });
      }
      return json({ error: "route inconnue" }, 404);
    } catch (e) {
      return json({ error: String(e) }, 500);
    }
  },
};
