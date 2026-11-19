"use strict";

// ---- helpers --------------------------------------------------------------
const $ = (sel, root = document) => root.querySelector(sel);
const app = () => $("#app");
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const num = (n) => (n == null ? "—" : Number(n).toLocaleString());
const f1 = (n) => (n == null ? "—" : Number(n).toFixed(1));
// compact token/count: 1234 -> 1.2k, 1234567 -> 1.23M
const kmg = (n) => {
  if (n == null) return "—";
  n = Number(n);
  if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(2) + "M";
  if (Math.abs(n) >= 1e3) return (n / 1e3).toFixed(1) + "k";
  return String(n);
};
const ms2s = (ms) => (ms == null ? "—" : (ms >= 60000
  ? `${Math.floor(ms / 3600000)}h${Math.floor((ms % 3600000) / 60000)}m`
  : `${(ms / 1000).toFixed(1)}s`));

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
    else if (kind === "compare") await renderCompare(arg);
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
  // Dataset counts only — question + abstention + sessions. No add-unit figure here is
  // computed from the dataset; add counts come from what runs actually added (below).
  const cards = d.types.map((x) => `
    <div class="card click" onclick="location.hash='#/type/${encodeURIComponent(x.type)}'">
      <h3>${esc(x.type)}</h3>
      <div class="kpi">
        <span><b>${num(x.count)}</b> questions</span>
        <span><b>${num(x.abstention)}</b> abstention</span>
        <span>mean <b>${f1(x.mean_sessions)}</b> sessions</span>
      </div>
    </div>`).join("");

  app().innerHTML = `
    <h1>LongMemEval dataset <span class="dim" style="font-size:1rem">(longmemeval_s_cleaned)</span></h1>
    <p class="statline">
      <span class="dim">(dataset)</span>
      <b>${num(t.questions)}</b> questions · <b>${num(t.abstention)}</b> abstention ·
      overall mean <b>${f1(t.mean_sessions)}</b> sessions/question
    </p>
    <h2>Question types <span class="dim" style="font-size:.9rem">(dataset)</span></h2>
    <div class="grid">${cards}</div>

    <h2>Add calls actually made <span class="dim" style="font-size:.9rem">(measured, per run — from traces)</span></h2>
    <div id="runAdds"><div class="card dim">loading measured add calls…</div></div>

    <h2>Session overlap <span class="dim" style="font-size:.9rem">(dataset)</span></h2>
    <div class="card"><div class="kpi">
      <span><b>${num(o.unique_sessions)}</b> unique sessions</span>
      <span><b>${num(o.total_links)}</b> (question, session) links</span>
      <span><b>${num(o.reused_sessions)}</b> sessions in &gt;1 haystack</span>
      <span>max reuse <b>${num(o.max_reuse)}</b>×</span>
      <span>mean <b>${f1(o.mean_haystacks_per_session)}</b> haystacks/session</span>
    </div>
    <p class="dim" style="margin:.6rem 0 0">A session's turns are identical across haystacks, but its
    date &amp; evidence status are per-haystack.</p></div>

    ${homeNote()}

    <p class="dim" style="margin-top:1rem">Index built ${esc(d.meta.built_at || "")} from
    <span class="mono">${esc(d.meta.dataset_path || "")}</span>.</p>`;

  renderRunAdds();
}

async function renderRunAdds() {
  const host = document.getElementById("runAdds");
  if (!host) return;
  let d;
  try { d = await api("/api/home/runs_add_calls"); }
  catch (e) { host.innerHTML = `<div class="card dim">measured add calls unavailable: ${esc(e.message)}</div>`; return; }
  if (!d.runs.length) {
    host.innerHTML = `<div class="card dim">No traced runs under <span class="mono">experiments/runs/</span> yet.</div>`;
    return;
  }
  // Union of types across runs, in a stable order.
  const typeSet = new Set();
  d.runs.forEach((r) => Object.keys(r.by_type).forEach((k) => typeSet.add(k)));
  const types = [...typeSet].sort();
  const head = `<th>run</th><th class="dim">extraction</th>` +
    types.map((ty) => `<th class="num">${esc(ty)}</th>`).join("") +
    `<th class="num">total</th>`;
  const body = d.runs.map((r) => `
    <tr class="click" onclick="location.hash='#/run/${encodeURIComponent(r.name)}'">
      <td class="mono">${esc(r.name)}</td>
      <td class="dim">${esc(r.extraction_llm || "")}</td>
      ${types.map((ty) => `<td class="num">${num(r.by_type[ty] || 0)}</td>`).join("")}
      <td class="num"><b>${num(r.total)}</b></td>
    </tr>`).join("");
  host.innerHTML = `<div class="card"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>
    <p class="dim" style="margin:.5rem 0 0">Each cell is the number of <span class="mono">mem0.add()</span>
    calls traced for that run and question type — what was really added, not a dataset estimate.</p></div>`;
}

function homeNote() {
  return `<div class="card" style="margin-top:1rem">
    <h3>How Mem0 is run on LongMemEval</h3>
    <p>Each question comes with its own chat history (its haystack: dated user-assistant
    sessions). Questions are handled independently, several at a time:</p>
    <ol>
      <li><b>Add:</b> the question gets its own empty memory space. Its sessions go to Mem0 in
        date order, one user→assistant turn-pair per <span class="mono">add()</span> call. Each call is one LLM
        extraction that turns the pair into memories, stored in Qdrant with Qwen
        embeddings. Default Mem0 (94c3fe9) does not pass the session date; the
        session-date branch does.</li>
      <li><b>Search:</b> once the whole haystack is in, Mem0 is searched once with the question
        (top 200 memories, scored on meaning, keywords and entities).</li>
      <li><b>Answer:</b> for each cutoff (200, 50, 20, 10), the top memories in date order plus
        the question date go to the answerer.</li>
      <li><b>Judge:</b> the judge compares each answer with the gold answer.</li>
    </ol>
    <p>Unlike LoCoMo, where one conversation is added once and all its questions search
    the same memories, LongMemEval adds a full haystack for every question. Sessions
    that appear in several haystacks are added again each time, because each question
    has its own memory space and the same session carries a different date in each
    haystack.</p>
  </div>`;
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
    const gw = m.extraction_endpoint && /gateway/i.test(m.extraction_endpoint)
      ? ` <span class="badge" title="${esc(m.extraction_endpoint)}">gateway</span>` : "";
    return `<tr>
      <td><input type="checkbox" class="cmpsel" value="${esc(r.name)}" onclick="event.stopPropagation()"></td>
      <td class="mono click" onclick="location.hash='#/run/${encodeURIComponent(r.name)}'">${esc(r.name)}</td>
      <td class="mono">${esc((m.mem0_commit || "").slice(0, 7))}</td>
      <td><b>${esc(m.extraction_llm || "?")}</b>${gw} <span class="dim">→ ${esc(m.answerer_model || "")}</span></td>
      <td>${esc(m.sample_args || "")}</td>
      <td>${esc((m.started_utc || "").replace("T", " ").replace("Z", ""))}</td>
    </tr>`;
  }).join("");
  app().innerHTML = `<h1>Runs <span class="dim" style="font-size:.9rem">— pick 2+ by extraction model, then Compare</span></h1>
    <div class="toolbar">
      <button class="btn" onclick="compareSelected()">Compare selected →</button>
      <span class="dim">tick the runs to compare on their shared questions</span>
    </div>
    <table><thead><tr><th></th><th>run</th><th>mem0</th><th>extraction → answerer</th><th>sample</th><th>started (UTC)</th></tr></thead>
    <tbody>${rows}</tbody></table>`;
}

function compareSelected() {
  const names = [...document.querySelectorAll(".cmpsel:checked")].map((c) => c.value);
  if (names.length < 2) { alert("Pick at least two runs to compare."); return; }
  location.hash = "#/compare/" + names.map(encodeURIComponent).join(",");
}

function manifestBar(m) {
  const items = [
    ["mem0", (m.mem0_ref || "") + " · " + (m.mem0_commit || "").slice(0, 7)],
    ["extraction", m.extraction_llm], ["answerer", m.answerer_model], ["judge", m.judge_model],
    ["effort", m.reasoning_effort], ["embedder", m.embedder_label || m.embedder],
    ["top_k", m.top_k], ["cutoffs", m.top_k_cutoffs],
    ["forward_ts", m.forward_timestamp], ["trace", m.trace_enabled], ["sample", m.sample_args],
  ];
  return `<div class="card manifest"><div class="kpi">` +
    items.filter(([, v]) => v != null && v !== "").map(([k, v]) =>
      `<span><span class="dim">${esc(k)}</span> <b>${esc(v)}</b></span>`).join("") +
    `</div>${embedderCompare(m)}</div>`;
}

// Ours (from our manifest) vs Mem0's published OSS embedder.
const MEM0_PUBLISHED_EMBEDDER = "Qwen 600M via SageMaker (README L242)";
function embedderCompare(m) {
  const ours = m.embedder_label || m.embedder || "(unknown)";
  return `<div class="embcmp"><span class="dim">embedder —</span>
    <b>ours:</b> ${esc(ours)} &nbsp;·&nbsp;
    <b>Mem0 published:</b> ${esc(MEM0_PUBLISHED_EMBEDDER)}</div>`;
}

async function renderRunBoard(name) {
  crumbs([{ label: "home", href: "#/" }, { label: "runs", href: "#/runs" }, { label: name }]);
  async function draw() {
    let d;
    try { d = await api(`/api/run/${encodeURIComponent(name)}/board`); }
    catch (e) { clearTimer(); app().innerHTML = `<div class="card">Error: ${esc(e.message)}</div>`; return; }
    const cutoffHdr = d.cutoffs.map((c) => `<th>${esc(c.replace("top_", "J@"))}</th>`).join("");
    const pubLabel = (d.published && d.published.label) || "published";
    const pubShort = pubLabel.replace(/^Mem0 /, "Mem0<br>");
    const rows = d.rows.map((r) => {
      const pct = r.adds_total ? Math.round(100 * r.adds_done / r.adds_total) : 0;
      const bar = `<div class="bar"><div class="fill" style="width:${pct}%"></div>
        <span class="barlab">${r.adds_done}/${r.adds_total}</span></div>`;
      const verds = d.cutoffs.map((c) => `<td>${verdictPill(r.verdicts[c])}</td>`).join("");
      const me = r.measured || {};
      const fail = me.add_failed ? ` <span style="color:#c0392b">+${me.add_failed}✗</span>` : "";
      const badExt = (me.cutoffs || 0) + (me.parse_fail || 0);
      const cutCell = badExt
        ? `<span style="color:#c0392b">${me.cutoffs || 0}/${me.parse_fail || 0}</span>` : "0/0";
      return `<tr class="click" onclick="location.hash='#/run/${encodeURIComponent(name)}/q/${encodeURIComponent(r.question_id)}'">
        <td class="mono">${esc(r.question_id)}${r.is_abstention ? ' <span class="badge abs">ABS</span>' : ""}</td>
        <td>${esc(r.question_type || "")}</td>
        <td><span class="stage s-${r.stage.split(" ")[0]}">${esc(r.stage)}</span></td>
        <td>${bar}</td>
        <td class="num">${kmg(me.add_calls)}${fail}</td>
        <td class="num" title="${me.mem_per_add != null ? me.mem_per_add + " per add" : ""}${me.add_zero ? " · " + me.add_zero + " adds stored 0" : ""}">${kmg(me.mem_stored)}${me.add_zero ? ` <span style="color:#c0392b">${me.add_zero}∅</span>` : ""}</td>
        <td class="num">${kmg(me.tok_in)}/${kmg(me.tok_out)}</td>
        <td class="num">${cutCell}</td>
        <td class="num">${me.search_ms != null ? Math.round(me.search_ms) + "ms" : "—"}</td>
        <td class="num">${ms2s(me.wall_ms)}</td>
        ${verds}
        <td>${verdictPill(r.published_verdict)}</td>
      </tr>`;
    }).join("");
    const live = d.running
      ? `<span class="pill live">● LIVE</span> auto-refresh 3s`
      : `<span class="dim">idle</span>`;
    const ex = d.extraction || {};
    const exColor = ((ex.cutoffs || 0) + (ex.parse_fail || 0) + (ex.errors || 0)) > 0 ? "#c0392b" : "#2e7d32";
    const zeroPct = ex.add_resp ? (100 * (ex.add_zero || 0) / ex.add_resp).toFixed(1) : "0.0";
    const zeroColor = (ex.add_zero || 0) > 0 ? "#c0392b" : "#2e7d32";
    const exBadge = `<span style="font-size:.8rem;color:${exColor}" title="measured from the mem0 trace — cut off = finish_reason=length (hit max_tokens); parse✗ = output not valid JSON; err = LLM error">· measured: ${num(ex.add_calls)} add calls${ex.add_failed ? " (" + ex.add_failed + " no-resp)" : ""}, ${num(ex.mem_stored)} mems (${ex.mem_per_add != null ? ex.mem_per_add : "—"}/add), ${kmg(ex.tok_in)}/${kmg(ex.tok_out)} tok in/out, ${ex.cutoffs || 0} cut off, ${ex.parse_fail || 0} parse✗, ${ex.errors || 0} err · wall ${ms2s(ex.wall_ms)}</span>
      <span style="font-size:.8rem;color:${zeroColor}" title="adds whose extraction stored 0 memories — a silent empty extraction (e.g. wrong JSON key from a gateway model) spikes this">· ${num(ex.add_zero || 0)} zero-memory adds (${zeroPct}%)</span>`;
    const mr = d.models_reported || { extraction: [], answerer: [] };
    const modelsLine = `<p class="dim" style="margin:.3rem 0"><b>reported models</b> (what the API/gateway actually returned) —
      extraction: <b>${(mr.extraction.length ? mr.extraction : ["—"]).map(esc).join(", ")}</b> ·
      answerer: <b>${(mr.answerer.length ? mr.answerer : ["—"]).map(esc).join(", ")}</b></p>`;
    const pubUsed = d.published && d.published.path
      ? `<div class="embcmp"><span class="dim">compared vs —</span> <b>${esc(pubLabel)}</b>
          <span class="mono dim">(${esc(d.published.file)})</span>, matched to extraction model
          <b>${esc(d.published.model)}</b></div>`
      : `<div class="embcmp"><span class="dim">compared vs —</span> <b>no published row</b>
          for extraction model <b>${esc((d.published && d.published.model) || "?")}</b></div>`;
    app().innerHTML = `
      <h1>${esc(name)} <span class="dim" style="font-size:.9rem">${d.counts.done}/${d.counts.total} judged · ${live} ${exBadge}</span>
        <a class="btn" href="#/runs" style="float:right">← runs</a>
        <button class="btn" style="float:right;margin-right:.4rem" onclick="showSummary('${esc(name)}')">summary ▾</button></h1>
      ${manifestBar(d.manifest)}
      ${modelsLine}
      ${pubUsed}
      <p class="dim" style="margin:.3rem 0">Per-question numbers below are <b>measured from this run's traces</b>
        — add calls (✗ = no response), memories stored, extraction tokens (in/out), cut-offs/parse✗,
        search latency, and wall time. "add progress" is against the dataset's planned add-units.</p>
      <div id="summaryHost"></div>
      <table><thead><tr><th>question_id</th><th>type</th><th>stage</th><th>add progress</th>
        <th>add<br>calls</th><th>mems</th><th>tok<br>in/out</th><th>cut/<br>parse✗</th><th>search</th><th>wall</th>
        ${cutoffHdr}<th>${pubShort}<br><span class="dim">(top_200)</span></th></tr></thead>
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
  const pubLabel = (d.published && d.published.label) || "published";
  const head = `<th>type</th>` + cuts.map((c) => `<th>ours ${esc(c.replace("top_", "@"))}</th>`).join("") +
    `<th>${esc(pubLabel)} @200</th>`;
  const cell = (o) => (o && o.pct != null ? `${o.pct}% <span class="dim">(${o.n})</span>` : "—");
  const body = d.by_type.map((t) =>
    `<tr><td>${esc(t.type)}</td>` + cuts.map((c) => `<td>${cell(t.ours[c])}</td>`).join("") +
    `<td>${cell(t.published_top200)}</td></tr>`).join("");
  const ov = `<tr class="total"><td><b>overall</b></td>` +
    cuts.map((c) => `<td><b>${cell(d.overall.ours[c])}</b></td>`).join("") +
    `<td><b>${cell(d.overall.published_top200)}</b></td></tr>`;

  // Measured per type + total (from the trace, never projected).
  const mhead = `<th>type</th><th>add calls</th><th>no-resp</th><th>mems stored</th><th>mem/add</th>
    <th title="adds whose extraction stored 0 memories">0-mem adds</th>
    <th>tok in</th><th>tok out</th><th>tok total</th><th>cut off</th><th>parse✗</th><th>search avg</th>`;
  const mrow = (label, m, bold) => {
    const b = bold ? "<b>" : "", e = bold ? "</b>" : "";
    const bad = (n, red) => (red && n ? `<span style="color:#c0392b">${num(n)}</span>` : num(n));
    const zpct = m.add_resp ? ` <span class="dim">(${(100 * (m.add_zero || 0) / m.add_resp).toFixed(1)}%)</span>` : "";
    return `<tr${bold ? ' class="total"' : ""}><td>${b}${esc(label)}${e}</td>
      <td class="num">${num(m.add_calls)}</td><td class="num">${bad(m.add_failed, true)}</td>
      <td class="num">${num(m.mem_stored)}</td>
      <td class="num">${m.mem_per_add != null ? m.mem_per_add : "—"}</td>
      <td class="num">${bad(m.add_zero, true)}${zpct}</td>
      <td class="num">${num(m.tok_in)}</td><td class="num">${num(m.tok_out)}</td><td class="num">${num(m.tok_total)}</td>
      <td class="num">${bad(m.cutoffs, true)}</td><td class="num">${bad(m.parse_fail, true)}</td>
      <td class="num">${m.search_ms_avg != null ? Math.round(m.search_ms_avg) + "ms" : "—"}</td></tr>`;
  };
  const mbody = d.by_type.map((t) => mrow(t.type, t.measured, false)).join("");
  const mov = mrow("overall", d.overall.measured, true);
  const wall = d.overall.measured && d.overall.measured.wall_ms;

  host.innerHTML = `<div class="card"><h3>Accuracy — judge PASS per type per cutoff (ours vs ${esc(pubLabel)})</h3>
    <table><thead><tr>${head}</tr></thead><tbody>${body}${ov}</tbody></table>
    <p class="dim" style="margin:.5rem 0 0">${esc(d.note)}</p>
    <h3 style="margin-top:1rem">Measured per type + total (from the run's traces)</h3>
    <table><thead><tr>${mhead}</tr></thead><tbody>${mbody}${mov}</tbody></table>
    <p class="dim" style="margin:.5rem 0 0">Whole-run wall time (first→last trace event): <b>${ms2s(wall)}</b>.
      Reasoning tokens are folded into "tok out" (GPT-OSS does not break them out). Per-question wall
      time is in the board; it is not summed here because questions run in parallel.</p></div>`;
}

// ---- compare two+ runs ----------------------------------------------------
async function renderCompare(arg) {
  const names = (arg || "").split(",").map(decodeURIComponent).filter(Boolean);
  crumbs([{ label: "home", href: "#/" }, { label: "runs", href: "#/runs" }, { label: "compare" }]);
  if (names.length < 2) { app().innerHTML = `<div class="card">Pick at least two runs from <a href="#/runs">Runs</a>.</div>`; return; }
  let d;
  try { d = await api(`/api/compare?runs=${names.map(encodeURIComponent).join(",")}`); }
  catch (e) { app().innerHTML = `<div class="card">Error: ${esc(e.message)}</div>`; return; }

  const cuts = d.cutoffs;
  const cell = (o) => (o && o.pct != null ? `${o.pct}% <span class="dim">(${o.n})</span>` : "—");
  const runHdrTop = d.runs.map((r) =>
    `<th colspan="${cuts.length}">${esc(r.name)}<br><span class="dim">${esc(r.extraction_llm || "?")}${/gateway/i.test(r.extraction_endpoint || "") ? " · gateway" : ""}</span></th>`).join("");
  const runHdrSub = d.runs.map(() => cuts.map((c) => `<th class="num">${esc(c.replace("top_", "@"))}</th>`).join("")).join("");
  const accRow = (label, pick, bold) => `<tr${bold ? ' class="total"' : ""}><td>${bold ? "<b>" + esc(label) + "</b>" : esc(label)}</td>` +
    d.accuracy.map((a) => cuts.map((c) => `<td class="num">${cell(pick(a)[c])}</td>`).join("")).join("") + `</tr>`;
  const body = d.types.map((t) => accRow(t, (a) => a.by_type[t])).join("") +
    accRow("overall", (a) => a.overall, true);

  // published rows (top_200 on shared qids), where a match exists
  const pubLine = d.published.map((p) =>
    p.has ? `<li><b>${esc(p.name)}</b> vs ${esc(p.label)}: ${p.pct}% <span class="dim">(${p.n} shared)</span></li>`
          : `<li><b>${esc(p.name)}</b>: ${esc(p.label)}</li>`).join("");

  // per-question flip grid
  const vpill = (v) => verdictPill(v);
  const gridRows = (flipsOnly) => d.grid.filter((g) => !flipsOnly || g.flip).map((g) =>
    `<tr class="${g.flip ? "evrow" : ""}">
      <td class="mono">${esc(g.question_id)}${g.flip ? ' <span class="badge" style="background:#c0392b;color:#fff">FLIP</span>' : ""}</td>
      <td>${esc(g.question_type || "")}</td>
      ${g.verdicts.map((v) => `<td>${vpill(v)}</td>`).join("")}
    </tr>`).join("");
  const gridHead = `<th>question_id</th><th>type</th>` + d.runs.map((r) => `<th>${esc(r.extraction_llm || r.name)}<br><span class="dim">@200</span></th>`).join("");

  app().innerHTML = `
    <h1>Compare <span class="dim" style="font-size:.9rem">— ${d.runs.map((r) => esc(r.extraction_llm || r.name)).join(" vs ")} · ${d.shared_count} shared questions · ${d.flips} flips @200</span>
      <a class="btn" href="#/runs" style="float:right">← runs</a></h1>
    <div class="card">
      <h3>Accuracy on shared question_ids — per type, per cutoff</h3>
      <table><thead>
        <tr><th rowspan="2">type</th>${runHdrTop}</tr>
        <tr>${runHdrSub}</tr>
      </thead><tbody>${body}</tbody></table>
      <h3 style="margin-top:1rem">Published rows (top_200, on shared questions)</h3>
      <ul class="dim">${pubLine}</ul>
    </div>
    <div class="card">
      <h3>Per-question verdict grid @top_200 <span class="dim">— flips highlighted</span>
        <label style="float:right;font-weight:normal"><input type="checkbox" id="flipsOnly"> flips only</label></h3>
      <table><thead><tr>${gridHead}</tr></thead><tbody id="gridBody">${gridRows(false)}</tbody></table>
    </div>`;
  const cb = document.getElementById("flipsOnly");
  if (cb) cb.addEventListener("change", (e) => { document.getElementById("gridBody").innerHTML = gridRows(e.target.checked); });
}

function panelText(s, max = 1500) {
  const t = String(s ?? "");
  if (!t) return `<span class="dim">—</span>`;
  if (t.length <= max) return `<pre class="pre">${esc(t)}</pre>`;
  return `<pre class="pre">${esc(t.slice(0, max))}<span class="rest" hidden>${esc(t.slice(max))}</span>` +
    `<span class="more" onclick="showMore(this)">… show more</span></pre>`;
}

async function renderRunQuestion(name, qid, page = 0) {
  crumbs([{ label: "home", href: "#/" }, { label: "runs", href: "#/runs" },
          { label: name, href: `#/run/${encodeURIComponent(name)}` }, { label: qid }]);
  const d = await api(`/api/run/${encodeURIComponent(name)}/question/${encodeURIComponent(qid)}?page=${page}&page_size=25`);

  // ADD panel (paginated — this page's add-units only)
  const addRows = (d.add || []).map((a, i) => {
    const sess = a.session_id
      ? `<a href="#/s/${encodeURIComponent(a.session_id)}" title="dataset session">${esc(a.session_id)}</a>${a.is_evidence ? ' <span class="badge ev">EVIDENCE</span>' : ""}`
      : `<span class="dim">unmatched</span>`;
    const mems = (a.stored_memories || []).map((m) =>
      `<li>[${esc(m.event || "")}] ${esc(m.memory || "")}</li>`).join("") || "<li class='dim'>none</li>";
    const tu = a.token_usage ? `${a.token_usage.total_tokens} tok` : "—";
    return `<details class="addunit"><summary>add #${a.n ?? i + 1} · ${sess}
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

  // ADD pager
  const addTotal = d.add_total ?? (d.add || []).length;
  const addPs = d.add_page_size ?? 25;
  const addPg = d.add_page ?? 0;
  const nPages = Math.max(1, Math.ceil(addTotal / addPs));
  const lo = addTotal ? addPg * addPs + 1 : 0;
  const hi = Math.min(addTotal, (addPg + 1) * addPs);
  const goto = (p) => `gotoAddPage('${esc(name)}','${esc(qid)}',${p})`;
  const pager = nPages > 1
    ? `<div class="toolbar">
        <button class="btn" ${addPg <= 0 ? "disabled" : ""} onclick="${goto(addPg - 1)}">← prev</button>
        <span class="dim">add-units ${lo}–${hi} of ${addTotal} · page ${addPg + 1}/${nPages}</span>
        <button class="btn" ${addPg >= nPages - 1 ? "disabled" : ""} onclick="${goto(addPg + 1)}">next →</button>
      </div>`
    : "";

  app().innerHTML = `
    <div class="card">
      <h1 class="mono">${esc(qid)} ${d.is_abstention ? '<span class="badge abs">ABSTENTION</span>' : ""}
        <span class="badge type">${esc(d.question_type || "")}</span></h1>
      <div class="qmeta"><b>question_date:</b> <span class="mono">${esc(d.question_date || "")}</span>
        · ${d.n_add_units} add-units · ${d.n_evidence} evidence session(s)</div>
      <div style="margin:.3rem 0">${esc(d.question || "")}</div>
      <div class="answer"><b>gold:</b> ${esc(d.gold_answer || "")}</div>
      <div class="qmeta" style="margin-top:.4rem"><b>${esc((d.published && d.published.label) || "published")} (${esc(d.published_result.cutoff || "top_200")}):</b>
        ${verdictPill(d.published_result.verdict)} — ${esc(d.published_result.answer || "—")}</div>
    </div>

    <h2>① ADD <span class="dim">— ${addTotal} add-units (click to expand)</span></h2>
    ${pager}${addRows}${pager}
    <h2>② SEARCH <span class="dim">— top-200 candidates, evidence highlighted</span></h2>
      <div class="card">${searchHtml}</div>
    <h2>③ ANSWER <span class="dim">— per cutoff</span></h2>${ans || '<div class="dim">No ANSWER trace yet.</div>'}
    <h2>④ JUDGE <span class="dim">— per cutoff, vs gold &amp; Mem0 published</span></h2>
      <div class="card"><table><thead><tr><th>cutoff</th><th>ours</th><th>judge raw</th></tr></thead>
      <tbody>${jud || ""}</tbody></table></div>`;
}

function gotoAddPage(name, qid, p) {
  renderRunQuestion(name, qid, p).catch((e) => {
    app().innerHTML = `<div class="card"><b>Error.</b> ${esc(e.message)}</div>`;
  });
  window.scrollTo({ top: 0 });
}

// expose handlers used in inline onclick
window.toggleSession = toggleSession;
window.jumpTo = jumpTo;
window.showMore = showMore;
window.showSummary = showSummary;
window.gotoAddPage = gotoAddPage;
window.compareSelected = compareSelected;
