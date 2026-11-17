"use strict";

// ---- helpers --------------------------------------------------------------
const $ = (sel, root = document) => root.querySelector(sel);
const app = () => $("#app");
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const num = (n) => (n == null ? "—" : Number(n).toLocaleString());
const f1 = (n) => (n == null ? "—" : Number(n).toFixed(1));

async function api(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json();
}

function crumbs(parts) {
  $("#crumbs").innerHTML = parts
    .map((p) => (p.href ? `<a href="${p.href}">${esc(p.label)}</a>` : esc(p.label)))
    .join(" › ");
}

const CLIP = 600; // collapse turns longer than this

// ---- router ---------------------------------------------------------------
async function route() {
  const h = location.hash.replace(/^#\/?/, "");
  const [kind, ...rest] = h.split("/");
  const arg = rest.map(decodeURIComponent).join("/");
  app().innerHTML = `<div class="loading">loading…</div>`;
  try {
    if (kind === "type") await renderType(arg);
    else if (kind === "q") await renderQuestion(arg);
    else if (kind === "s") await renderSession(arg);
    else await renderHome();
  } catch (e) {
    app().innerHTML = `<div class="card"><b>Error.</b> ${esc(e.message)}</div>`;
  }
}
window.addEventListener("hashchange", route);
window.addEventListener("DOMContentLoaded", route);

// ---- home -----------------------------------------------------------------
async function renderHome() {
  crumbs([{ label: "home" }]);
  const d = await api("/api/overview");
  const t = d.totals, o = d.overlap;
  const cards = d.types.map((x) => `
    <div class="card click" onclick="location.hash='#/type/${encodeURIComponent(x.type)}'">
      <h3>${esc(x.type)}</h3>
      <div class="kpi">
        <span><b>${num(x.count)}</b> questions</span>
        <span><b>${num(x.abstention)}</b> abstention</span>
        <span>mean <b>${f1(x.mean_sessions)}</b> sessions</span>
        <span>mean <b>${f1(x.mean_add_units)}</b> add-units</span>
        <span><b>${num(x.total_add_units)}</b> total adds</span>
      </div>
    </div>`).join("");

  app().innerHTML = `
    <h1>LongMemEval dataset <span class="dim" style="font-size:1rem">(longmemeval_s_cleaned)</span></h1>
    <p class="statline">
      <b>${num(t.questions)}</b> questions · <b>${num(t.abstention)}</b> abstention ·
      overall mean <b>${f1(t.mean_add_units)}</b> add-units/question ·
      <b>${num(t.total_add_units)}</b> total add-units if the whole set is ingested
    </p>
    <h2>Question types</h2>
    <div class="grid">${cards}</div>
    <h2>Session overlap</h2>
    <div class="card"><div class="kpi">
      <span><b>${num(o.unique_sessions)}</b> unique sessions</span>
      <span><b>${num(o.total_links)}</b> (question, session) links</span>
      <span><b>${num(o.reused_sessions)}</b> sessions in &gt;1 haystack</span>
      <span>max reuse <b>${num(o.max_reuse)}</b>×</span>
      <span>mean <b>${f1(o.mean_haystacks_per_session)}</b> haystacks/session</span>
    </div>
    <p class="dim" style="margin:.6rem 0 0">A session's turns are identical across haystacks, but its
    date &amp; evidence status are per-haystack.</p></div>
    <p class="dim" style="margin-top:1rem">Index built ${esc(d.meta.built_at || "")} from
    <span class="mono">${esc(d.meta.dataset_path || "")}</span>.</p>`;
}

// ---- type page ------------------------------------------------------------
const typeState = { sort: "question_id", dir: 1, q: "", absOnly: false };

async function renderType(type) {
  crumbs([{ label: "home", href: "#/" }, { label: type }]);
  const d = await api(`/api/type/${encodeURIComponent(type)}`);
  typeState.all = d.questions;
  typeState.type = type;
  app().innerHTML = `
    <h1>${esc(type)} <span class="dim" style="font-size:1rem">· ${num(d.questions.length)} questions</span></h1>
    <div class="toolbar">
      <input type="search" id="q" placeholder="search question + answer…" value="${esc(typeState.q)}">
      <label><input type="checkbox" id="abs" ${typeState.absOnly ? "checked" : ""}> abstention only</label>
      <span class="dim" id="count"></span>
    </div>
    <table id="tbl"><thead><tr>
      ${th("question_id", "question_id")}${th("question", "question")}
      ${th("answer", "gold answer")}${th("question_date", "date")}
      ${th("n_sessions", "sessions", true)}${th("n_evidence", "evid", true)}
      ${th("n_add_units", "add-units", true)}
    </tr></thead><tbody></tbody></table>`;
  $("#q").addEventListener("input", (e) => { typeState.q = e.target.value; drawRows(); });
  $("#abs").addEventListener("change", (e) => { typeState.absOnly = e.target.checked; drawRows(); });
  $("#tbl thead").addEventListener("click", (e) => {
    const thEl = e.target.closest("th"); if (!thEl) return;
    const k = thEl.dataset.k;
    if (typeState.sort === k) typeState.dir *= -1; else { typeState.sort = k; typeState.dir = 1; }
    drawRows();
  });
  drawRows();
}

function th(k, label, n) {
  const a = typeState.sort === k ? `<span class="arrow">${typeState.dir > 0 ? "▲" : "▼"}</span>` : "";
  return `<th data-k="${k}" class="${n ? "num" : ""}">${esc(label)} ${a}</th>`;
}

function drawRows() {
  let rows = typeState.all.slice();
  const q = typeState.q.trim().toLowerCase();
  if (q) rows = rows.filter((r) =>
    (r.question + " " + r.answer).toLowerCase().includes(q));
  if (typeState.absOnly) rows = rows.filter((r) => r.is_abstention);
  const k = typeState.sort, dir = typeState.dir;
  rows.sort((a, b) => {
    const x = a[k], y = b[k];
    if (typeof x === "number") return (x - y) * dir;
    return String(x).localeCompare(String(y)) * dir;
  });
  $("#count").textContent = `${rows.length} shown`;
  $("#tbl tbody").innerHTML = rows.map((r) => `
    <tr class="click" onclick="location.hash='#/q/${encodeURIComponent(r.question_id)}'">
      <td class="mono">${esc(r.question_id)} ${r.is_abstention ? '<span class="badge abs">ABS</span>' : ""}</td>
      <td><div class="cellclip">${esc(r.question)}</div></td>
      <td><div class="cellclip">${esc(r.answer)}</div></td>
      <td class="mono">${esc(r.question_date)}</td>
      <td class="num">${num(r.n_sessions)}</td>
      <td class="num">${num(r.n_evidence)}</td>
      <td class="num">${num(r.n_add_units)}</td>
    </tr>`).join("");
}

// ---- question page --------------------------------------------------------
async function renderQuestion(qid) {
  const d = await api(`/api/question/${encodeURIComponent(qid)}`);
  const q = d.question, sessions = d.sessions;
  crumbs([{ label: "home", href: "#/" },
          { label: q.question_type, href: `#/type/${encodeURIComponent(q.question_type)}` },
          { label: qid }]);

  app().innerHTML = `
    <div class="card">
      <h1 class="mono">${esc(qid)}
        ${q.is_abstention ? '<span class="badge abs">ABSTENTION</span>' : ""}
        <span class="badge type">${esc(q.question_type)}</span></h1>
      <div class="qmeta"><b>question_date:</b> <span class="mono">${esc(q.question_date)}</span></div>
      <div style="margin:.4rem 0">${esc(q.question)}</div>
      <div class="answer"><b>gold answer:</b> ${esc(q.answer)}</div>
      <p class="dim" style="margin:.6rem 0 0">${num(q.n_sessions)} sessions ·
        ${num(q.n_evidence)} evidence · <b>${num(q.n_add_units)}</b> add-units</p>
    </div>
    <div class="toolbar">
      <button class="btn" id="evOnly">evidence only</button>
      <button class="btn" id="nextEv">jump to next evidence ↓</button>
      <span class="dim">click a timeline tick to jump to a session</span>
    </div>
    <div class="timeline" id="tl"></div>
    <div id="sessions"></div>`;

  renderTimeline(q, sessions);
  const host = $("#sessions");
  host.innerHTML = sessions.map((s) => sessionRow(qid, s)).join("");

  let evOnly = false;
  $("#evOnly").addEventListener("click", (e) => {
    evOnly = !evOnly; e.target.classList.toggle("active", evOnly);
    host.querySelectorAll(".session").forEach((el) => {
      el.style.display = (!evOnly || el.dataset.ev === "1") ? "" : "none";
    });
  });
  let evCursor = -1;
  $("#nextEv").addEventListener("click", () => {
    const evs = sessions.filter((s) => s.is_evidence);
    if (!evs.length) return;
    evCursor = (evCursor + 1) % evs.length;
    jumpTo(evs[evCursor].session_id);
  });
}

function renderTimeline(q, sessions) {
  const tl = $("#tl");
  const epochs = sessions.map((s) => s.epoch).filter((e) => e != null);
  if (q.question_epoch) epochs.push(q.question_epoch);
  if (!epochs.length) { tl.innerHTML = `<div class="tl-ends">no parseable dates</div>`; return; }
  const lo = Math.min(...epochs), hi = Math.max(...epochs), span = (hi - lo) || 1;
  const x = (e) => 1.5 + 97 * (e - lo) / span;
  let html = `<div class="tl-axis"></div>`;
  for (const s of sessions) {
    if (s.epoch == null) continue;
    html += `<div class="tl-tick ${s.is_evidence ? "ev" : ""}" style="left:${x(s.epoch)}%"
               title="${esc(s.date)}${s.is_evidence ? " · EVIDENCE" : ""}"
               onclick="jumpTo('${esc(s.session_id)}')"></div>`;
  }
  if (q.question_epoch) {
    html += `<div class="tl-q" style="left:${x(q.question_epoch)}%">question</div>`;
  }
  const d = (e) => new Date(e * 1000).toISOString().slice(0, 10);
  html += `<div class="tl-ends" style="left:1.5%">${d(lo)}</div>
           <div class="tl-ends" style="right:1.5%">${d(hi)}</div>`;
  tl.innerHTML = html;
}

function sessionRow(qid, s) {
  const db = s.days_before == null ? "" :
    (s.days_before > 0 ? `${s.days_before} days before question`
     : s.days_before < 0 ? `${-s.days_before} days after question` : "same day as question");
  const also = s.n_haystacks > 1
    ? `<a href="#/s/${encodeURIComponent(s.session_id)}" onclick="event.stopPropagation()">also in ${s.n_haystacks - 1} other haystack${s.n_haystacks - 1 > 1 ? "s" : ""}</a>`
    : `<span class="dim">unique to this haystack</span>`;
  return `
    <div class="session ${s.is_evidence ? "ev" : ""}" id="s-${esc(s.session_id)}" data-ev="${s.is_evidence}">
      <div class="shead" onclick="toggleSession('${esc(qid)}','${esc(s.session_id)}')">
        <span class="sid mono">#${s.position} · ${esc(s.session_id)}</span>
        <span class="dim mono">${esc(s.date)}</span>
        <span class="dim">${db}</span>
        ${s.is_evidence ? '<span class="badge ev">EVIDENCE</span>' : ""}
        <span class="spacer"></span>
        <span class="dim">${num(s.n_turns)} turns · ${num(s.n_add_units)} adds · ${also}</span>
      </div>
      <div class="sbody hidden" id="b-${esc(s.session_id)}"><div class="dim">loading…</div></div>
    </div>`;
}

async function toggleSession(qid, sid) {
  const body = document.getElementById("b-" + sid);
  if (!body) return;
  const hidden = body.classList.toggle("hidden");
  if (hidden) return;
  if (body.dataset.loaded) return;
  const d = await api(`/api/session/${encodeURIComponent(sid)}/turns?question_id=${encodeURIComponent(qid)}`);
  body.dataset.loaded = "1";
  const ts = d.timestamp != null
    ? `timestamp=<span class="mono">${d.timestamp}</span> <span class="dim">(${esc(d.date)})</span>`
    : `<span class="dim">no timestamp (unparseable date)</span>`;
  body.innerHTML = d.units.map((u) => unitHtml(u, ts)).join("");
}

function unitHtml(u, ts) {
  const head = u.skipped
    ? `<span class="dim">skipped — empty content, not added</span>`
    : `<span class="addno">add #${u.add_no}</span> · ${ts}`;
  const turns = u.turns.map(turnHtml).join("");
  return `<div class="unit ${u.skipped ? "skipped" : ""}"><div class="unit-head">${head}</div>${turns}</div>`;
}

function turnHtml(t) {
  const cls = t.role === "user" ? "user" : "assistant";
  const needle = t.has_answer ? '<span class="badge needle">needle</span> ' : "";
  const content = String(t.content || "");
  let body;
  if (content.length > CLIP) {
    body = `${esc(content.slice(0, CLIP))}<span class="rest" hidden>${esc(content.slice(CLIP))}</span>` +
      `<span class="more" onclick="showMore(this)">… show more</span>`;
  } else {
    body = esc(content);
  }
  return `<div class="turn ${cls} ${t.has_answer ? "needle" : ""}">
    <span class="role">${needle}${esc(t.role)}</span>${body}</div>`;
}

function showMore(a) {
  const rest = a.previousElementSibling; // the hidden .rest span
  if (rest && rest.classList.contains("rest")) rest.hidden = false;
  a.remove();
}

function jumpTo(sid) {
  const el = document.getElementById("s-" + sid);
  if (!el) return;
  el.scrollIntoView({ behavior: "smooth", block: "center" });
  el.style.transition = "box-shadow .2s";
  el.style.boxShadow = "0 0 0 3px rgba(33,85,205,.4)";
  setTimeout(() => (el.style.boxShadow = ""), 900);
}

// ---- session page ---------------------------------------------------------
async function renderSession(sid) {
  const d = await api(`/api/session/${encodeURIComponent(sid)}`);
  crumbs([{ label: "home", href: "#/" }, { label: `session ${sid}` }]);
  const s = d.session;
  app().innerHTML = `
    <div class="card">
      <h1 class="mono">${esc(sid)}</h1>
      <div class="kpi">
        <span><b>${num(s.n_turns)}</b> turns</span>
        <span><b>${num(s.n_add_units)}</b> add-units</span>
        <span>appears in <b>${num(s.n_haystacks)}</b> haystack(s)</span>
      </div>
      <p class="dim" style="margin:.5rem 0 0">Same turns everywhere; the date differs per haystack below.</p>
    </div>
    <h2>Questions whose haystack uses this session</h2>
    <table><thead><tr><th>question_id</th><th>type</th><th>date here</th><th>evidence?</th><th>question</th></tr></thead>
    <tbody>${d.used_by.map((u) => `
      <tr class="click" onclick="location.hash='#/q/${encodeURIComponent(u.question_id)}'">
        <td class="mono">${esc(u.question_id)}</td>
        <td>${esc(u.question_type)}</td>
        <td class="mono">${esc(u.date)}</td>
        <td>${u.is_evidence ? '<span class="badge ev">EVIDENCE</span>' : ""}</td>
        <td><div class="cellclip">${esc(u.question)}</div></td>
      </tr>`).join("")}</tbody></table>`;
}

// expose handlers used in inline onclick
window.toggleSession = toggleSession;
window.jumpTo = jumpTo;
window.showMore = showMore;
