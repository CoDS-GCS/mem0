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
let _timer = null;
function clearTimer() { if (_timer) { clearInterval(_timer); _timer = null; } }

async function route() {
  clearTimer();
  const h = location.hash.replace(/^#\/?/, "");
  const [kind, ...rest] = h.split("/").map(decodeURIComponent);
  const arg = rest.join("/");
  app().innerHTML = `<div class="loading">loading…</div>`;
  try {
    if (kind === "type") await renderType(arg);
    else if (kind === "q") await renderQuestion(arg);
    else if (kind === "s") await renderSession(arg);
    else if (kind === "runs") await renderRuns();
    else if (kind === "run") {
      if (rest.length >= 3 && rest[1] === "q") await renderRunQuestion(rest[0], rest.slice(2).join("/"));
      else await renderRunBoard(rest[0]);
    } else await renderHome();
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

// ===========================================================================
// RUN VIEW (tracer)
// ===========================================================================

function verdictPill(v) {
  if (!v) return `<span class="pill dim">—</span>`;
  const up = String(v).toUpperCase();
  const cls = up === "PASS" ? "pass" : up === "FAIL" ? "fail" : "dim";
  return `<span class="pill ${cls}">${esc(up)}</span>`;
}

async function renderRuns() {
  crumbs([{ label: "home", href: "#/" }, { label: "runs" }]);
  const d = await api("/api/runs");
  if (!d.runs.length) {
    app().innerHTML = `<h1>Runs</h1><div class="card dim">No LongMemEval runs yet under
      <span class="mono">experiments/runs/</span>. Launch one with
      <span class="mono">experiments/run_longmemeval.sh &lt;name&gt; 94c3fe9 --per-type 5 --seed 42</span>.</div>`;
    return;
  }
  const rows = d.runs.map((r) => {
    const m = r.manifest || {};
    return `<tr class="click" onclick="location.hash='#/run/${encodeURIComponent(r.name)}'">
      <td class="mono">${esc(r.name)}</td>
      <td class="mono">${esc((m.mem0_commit || "").slice(0, 7))}</td>
      <td>${esc(m.extraction_llm || "")}/${esc(m.answerer_model || "")}</td>
      <td>${esc(m.sample_args || "")}</td>
      <td>${esc((m.started_utc || "").replace("T", " ").replace("Z", ""))}</td>
    </tr>`;
  }).join("");
  app().innerHTML = `<h1>Runs</h1>
    <table><thead><tr><th>run</th><th>mem0</th><th>extraction/answerer</th><th>sample</th><th>started (UTC)</th></tr></thead>
    <tbody>${rows}</tbody></table>`;
}

function manifestBar(m) {
  const items = [
    ["mem0", (m.mem0_ref || "") + " · " + (m.mem0_commit || "").slice(0, 7)],
    ["extraction", m.extraction_llm], ["answerer", m.answerer_model], ["judge", m.judge_model],
    ["effort", m.reasoning_effort], ["embedder", m.embedder],
    ["top_k", m.top_k], ["cutoffs", m.top_k_cutoffs],
    ["forward_ts", m.forward_timestamp], ["trace", m.trace_enabled], ["sample", m.sample_args],
  ];
  return `<div class="card manifest"><div class="kpi">` +
    items.filter(([, v]) => v != null && v !== "").map(([k, v]) =>
      `<span><span class="dim">${esc(k)}</span> <b>${esc(v)}</b></span>`).join("") +
    `</div></div>`;
}

async function renderRunBoard(name) {
  crumbs([{ label: "home", href: "#/" }, { label: "runs", href: "#/runs" }, { label: name }]);
  async function draw() {
    let d;
    try { d = await api(`/api/run/${encodeURIComponent(name)}/board`); }
    catch (e) { clearTimer(); app().innerHTML = `<div class="card">Error: ${esc(e.message)}</div>`; return; }
    const cutoffHdr = d.cutoffs.map((c) => `<th>${esc(c.replace("top_", "J@"))}</th>`).join("");
    const rows = d.rows.map((r) => {
      const pct = r.adds_total ? Math.round(100 * r.adds_done / r.adds_total) : 0;
      const bar = `<div class="bar"><div class="fill" style="width:${pct}%"></div>
        <span class="barlab">${r.adds_done}/${r.adds_total}</span></div>`;
      const verds = d.cutoffs.map((c) => `<td>${verdictPill(r.verdicts[c])}</td>`).join("");
      return `<tr class="click" onclick="location.hash='#/run/${encodeURIComponent(name)}/q/${encodeURIComponent(r.question_id)}'">
        <td class="mono">${esc(r.question_id)}${r.is_abstention ? ' <span class="badge abs">ABS</span>' : ""}</td>
        <td>${esc(r.question_type || "")}</td>
        <td><span class="stage s-${r.stage.split(" ")[0]}">${esc(r.stage)}</span></td>
        <td>${bar}</td>${verds}
        <td>${verdictPill(r.mem0_gpt5_verdict)}</td>
      </tr>`;
    }).join("");
    const live = d.running
      ? `<span class="pill live">● LIVE</span> auto-refresh 3s`
      : `<span class="dim">idle</span>`;
    app().innerHTML = `
      <h1>${esc(name)} <span class="dim" style="font-size:.9rem">${d.counts.done}/${d.counts.total} judged · ${live}</span>
        <a class="btn" href="#/runs" style="float:right">← runs</a>
        <button class="btn" style="float:right;margin-right:.4rem" onclick="showSummary('${esc(name)}')">summary ▾</button></h1>
      ${manifestBar(d.manifest)}
      <div id="summaryHost"></div>
      <table><thead><tr><th>question_id</th><th>type</th><th>stage</th><th>add progress</th>
        ${cutoffHdr}<th>Mem0 gpt5<br><span class="dim">(top_200)</span></th></tr></thead>
      <tbody>${rows}</tbody></table>`;
    if (!d.running) clearTimer();
  }
  await draw();
  clearTimer();
  _timer = setInterval(draw, 3000);
}

async function showSummary(name) {
  const host = document.getElementById("summaryHost");
  if (!host) return;
  if (host.dataset.open === "1") { host.innerHTML = ""; host.dataset.open = "0"; return; }
  host.dataset.open = "1";
  host.innerHTML = `<div class="card dim">loading summary…</div>`;
  const d = await api(`/api/run/${encodeURIComponent(name)}/summary`);
  const cuts = d.cutoffs;
  const head = `<th>type</th>` + cuts.map((c) => `<th>ours ${esc(c.replace("top_", "@"))}</th>`).join("") +
    `<th>Mem0 gpt5 @200</th>`;
  const cell = (o) => (o && o.pct != null ? `${o.pct}% <span class="dim">(${o.n})</span>` : "—");
  const body = d.by_type.map((t) =>
    `<tr><td>${esc(t.type)}</td>` + cuts.map((c) => `<td>${cell(t.ours[c])}</td>`).join("") +
    `<td>${cell(t.mem0_gpt5_top200)}</td></tr>`).join("");
  const ov = `<tr class="total"><td><b>overall</b></td>` +
    cuts.map((c) => `<td><b>${cell(d.overall.ours[c])}</b></td>`).join("") +
    `<td><b>${cell(d.overall.mem0_gpt5_top200)}</b></td></tr>`;
  host.innerHTML = `<div class="card"><h3>Summary — J per type per cutoff (ours vs Mem0 published gpt-5)</h3>
    <table><thead><tr>${head}</tr></thead><tbody>${body}${ov}</tbody></table>
    <p class="dim" style="margin:.5rem 0 0">${esc(d.note)}</p></div>`;
}

function panelText(s, max = 1500) {
  const t = String(s ?? "");
  if (!t) return `<span class="dim">—</span>`;
  if (t.length <= max) return `<pre class="pre">${esc(t)}</pre>`;
  return `<pre class="pre">${esc(t.slice(0, max))}<span class="rest" hidden>${esc(t.slice(max))}</span>` +
    `<span class="more" onclick="showMore(this)">… show more</span></pre>`;
}

async function renderRunQuestion(name, qid) {
  crumbs([{ label: "home", href: "#/" }, { label: "runs", href: "#/runs" },
          { label: name, href: `#/run/${encodeURIComponent(name)}` }, { label: qid }]);
  const d = await api(`/api/run/${encodeURIComponent(name)}/question/${encodeURIComponent(qid)}`);

  // ADD panel
  const addRows = (d.add || []).map((a, i) => {
    const sess = a.session_id
      ? `<a href="#/s/${encodeURIComponent(a.session_id)}" title="dataset session">${esc(a.session_id)}</a>${a.is_evidence ? ' <span class="badge ev">EVIDENCE</span>' : ""}`
      : `<span class="dim">unmatched</span>`;
    const mems = (a.stored_memories || []).map((m) =>
      `<li>[${esc(m.event || "")}] ${esc(m.memory || "")}</li>`).join("") || "<li class='dim'>none</li>";
    const tu = a.token_usage ? `${a.token_usage.total_tokens} tok` : "—";
    return `<details class="addunit"><summary>add #${i + 1} · ${sess}
      · ts sent <span class="mono">${a.timestamp_sent ?? "—"}</span> · ${tu}
      · ${a.add_latency_ms != null ? Math.round(a.add_latency_ms) + "ms" : "—"}</summary>
      <div class="pcol"><b>messages sent</b>${panelText((a.messages || []).map((m) => m.role + ": " + m.content).join("\n\n"))}</div>
      <div class="pcol"><b>extraction prompt</b>${panelText((a.extraction_prompt || []).map((m) => m.role + ": " + m.content).join("\n\n"))}</div>
      <div class="pcol"><b>extraction response</b>${panelText(a.extraction_response)}</div>
      <div class="pcol"><b>stored memories</b><ul class="mems">${mems}</ul></div>
    </details>`;
  }).join("") || `<div class="dim">No ADD events traced yet.</div>`;

  // SEARCH panel
  let searchHtml = `<div class="dim">No SEARCH trace yet.</div>`;
  if (d.search) {
    const s = d.search;
    const evline = Object.entries(s.evidence_in || {}).map(([k, v]) =>
      `${k.replace("top_", "≤")}: <b>${v}</b>`).join(" · ");
    const cands = (s.candidates || []).slice(0, 200).map((c) =>
      `<tr class="${c.is_evidence ? "evrow" : ""}">
        <td class="num">${c.rank}</td>
        <td><div class="cellclip">${esc(c.memory || c.id)}</div>${c.is_evidence ? ' <span class="badge ev">EV</span>' : ""}</td>
        <td class="num">${c.final_score != null ? c.final_score.toFixed(3) : "—"}</td>
        <td class="num">${c.semantic != null ? c.semantic.toFixed(3) : "—"}</td>
        <td class="num">${c.bm25 != null ? c.bm25.toFixed(3) : "—"}</td>
        <td class="num">${c.entity_boost != null ? c.entity_boost.toFixed(3) : "—"}</td>
      </tr>`).join("");
    searchHtml = `<p><b>query:</b> ${esc(s.query || "")}</p>
      <p class="dim">${s.n_candidates} candidates · evidence at ranks [${(s.evidence_ranks || []).join(", ") || "none"}] · in cutoff — ${evline}</p>
      <table class="cand"><thead><tr><th>#</th><th>memory</th><th>final</th><th>sem</th><th>bm25</th><th>entity</th></tr></thead>
      <tbody>${cands}</tbody></table>`;
  }

  // ANSWER + JUDGE panels
  const ans = (d.answer || []).map((a) =>
    `<details class="addunit"><summary>${esc(a.cutoff)} — answer${a.token_usage ? " · " + a.token_usage.total_tokens + " tok" : ""}</summary>
      <div class="pcol"><b>answer prompt (with question_date)</b>${panelText(a.prompt)}</div>
      <div class="pcol"><b>generated answer</b>${panelText(a.answer, 4000)}</div></details>`).join("");
  const jud = (d.judge || []).map((j) =>
    `<tr><td>${esc(j.cutoff)}</td><td>${verdictPill(j.verdict)}</td>
      <td><div class="cellclip">${esc(j.judge_raw || "")}</div></td></tr>`).join("");

  app().innerHTML = `
    <div class="card">
      <h1 class="mono">${esc(qid)} ${d.is_abstention ? '<span class="badge abs">ABSTENTION</span>' : ""}
        <span class="badge type">${esc(d.question_type || "")}</span></h1>
      <div class="qmeta"><b>question_date:</b> <span class="mono">${esc(d.question_date || "")}</span>
        · ${d.n_add_units} add-units · ${d.n_evidence} evidence session(s)</div>
      <div style="margin:.3rem 0">${esc(d.question || "")}</div>
      <div class="answer"><b>gold:</b> ${esc(d.gold_answer || "")}</div>
      <div class="qmeta" style="margin-top:.4rem"><b>Mem0 published gpt-5 (${esc(d.mem0_gpt5.cutoff || "top_200")}):</b>
        ${verdictPill(d.mem0_gpt5.verdict)} — ${esc(d.mem0_gpt5.answer || "—")}</div>
    </div>

    <h2>① ADD <span class="dim">— ${(d.add || []).length} add-units (click to expand)</span></h2>${addRows}
    <h2>② SEARCH <span class="dim">— top-200 candidates, evidence highlighted</span></h2>
      <div class="card">${searchHtml}</div>
    <h2>③ ANSWER <span class="dim">— per cutoff</span></h2>${ans || '<div class="dim">No ANSWER trace yet.</div>'}
    <h2>④ JUDGE <span class="dim">— per cutoff, vs gold &amp; Mem0 published</span></h2>
      <div class="card"><table><thead><tr><th>cutoff</th><th>ours</th><th>judge raw</th></tr></thead>
      <tbody>${jud || ""}</tbody></table></div>`;
}

// expose handlers used in inline onclick
window.toggleSession = toggleSession;
window.jumpTo = jumpTo;
window.showMore = showMore;
window.showSummary = showSummary;
