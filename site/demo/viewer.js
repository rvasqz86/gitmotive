// gitmotive demo viewer: DOM wiring. All data-derived text goes in through textContent
// (via h() below); no markup is assembled from strings and no inline styles are set.
import { indexData, colorFor, parseHash, detailModel } from "./viewer-core.mjs";

const $ = (id) => document.getElementById(id);
const S = { data: null, idx: null, file: null, rows: [], active: -1 };

// --- tiny DOM builder: strings become text nodes, never markup ----------------------------

function h(tag, props, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v == null || v === false) continue;
    if (k === "style" || k.startsWith("on")) throw new Error(`refusing attribute ${k}`);
    if (k === "class") el.className = v;
    else if (k === "text") el.textContent = String(v);
    else el.setAttribute(k, v === true ? "" : String(v));
  }
  for (const kid of kids.flat()) {
    if (kid == null || kid === false) continue;
    el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  return el;
}

const omitted = (s) => typeof s === "string" && s.startsWith("[omitted:");
const val = (s, cls) => h("span", { class: [cls, omitted(s) && "omit"].filter(Boolean).join(" ") || null, text: s });
const plural = (n, one, many = one + "s") => `${n.toLocaleString()} ${n === 1 ? one : many}`;
const short = (sha) => (sha ? String(sha).slice(0, 8) : "");

function timeEl(date) {
  if (!(date instanceof Date) || Number.isNaN(date.getTime())) return h("span", { class: "muted", text: "unknown" });
  const iso = date.toISOString();
  const local = date.toLocaleString(undefined, {
    year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
  return h("time", { datetime: iso, title: iso, text: local });
}

function hashFor(path, n) {
  // readable deep links: keep "/" and ":" (parseHash splits on the last ':'), escape "#", "?", "%"
  const p = encodeURI(path).replace(/[#?]/g, encodeURIComponent);
  return "#" + p + (n ? ":" + n : "");
}

// --- states ----------------------------------------------------------------------------------

function setState(kind, ...kids) {
  const box = $("state");
  box.className = `state state-${kind}`;
  box.setAttribute("role", kind === "err" ? "alert" : "status");
  box.replaceChildren(...kids);
  box.hidden = kids.length === 0;
}

function showError(detail) {
  $("viewer").hidden = true;
  $("keys").hidden = true;
  const retry = h("button", { type: "button", class: "btn ghost" }, "Try again");
  retry.addEventListener("click", load);
  setState("err",
    h("p", { class: "state-msg" }, h("span", { class: "err", text: "fatal:" }), " could not load ",
      h("code", { text: "data.json" }), ` (${detail}).`),
    h("p", { class: "state-sub" },
      "The demo is a static page that reads one JSON file from this site; nothing else is fetched. Reload, or try again."),
    retry);
}

function summaryBanner(totalLines, matched) {
  if (matched > 0) return setState("ok");
  if (totalLines === 0) {
    return setState("empty",
      h("p", { class: "hunk-line", "aria-hidden": "true", text: "@@ 0 lines @@" }),
      h("p", { class: "state-msg" }, h("strong", { text: "This snapshot has no source lines." })),
      h("p", { class: "state-sub" },
        "The exported files are empty, so there is nothing to blame and no intent to show."));
  }
  setState("empty",
    h("p", { class: "hunk-line", "aria-hidden": "true", text: `@@ intent: 0 of ${totalLines.toLocaleString()} lines @@` }),
    h("p", { class: "state-msg" }, h("strong", { text: "No intent is recorded in this snapshot yet." })),
    h("p", { class: "state-sub" },
      "Every line below still has its blame, but none matched a recorded edit, so the gutter shows ",
      h("code", { text: "·" }), " and each line answers ", h("q", { text: "none recorded" }),
      ". That is the same answer ", h("code", { text: "git motive" }),
      " gives for a line no hook saw: it never guesses."));
}

// --- rendering -------------------------------------------------------------------------------

function renderMeta(data, totalLines, matched) {
  const meta = $("meta");
  const kids = [];
  if (data.repo) kids.push(h("span", null, h("span", { class: "k", text: "repo" }), " ", data.repo,
    data.rev ? h("span", { class: "muted", text: ` @ ${short(data.rev)}` }) : null));
  if (data.generated_at) kids.push(h("span", null, h("span", { class: "k", text: "exported" }), " ",
    timeEl(new Date(data.generated_at))));
  kids.push(h("span", null, h("span", { class: "k", text: "lines" }), " ",
    `${matched.toLocaleString()} of ${totalLines.toLocaleString()} with intent`));
  kids.push(h("span", null, h("span", { class: "k", text: "prompts" }), " ", S.idx.prompts.size.toLocaleString()));
  meta.replaceChildren(...kids);
  meta.hidden = false;
}

function renderFiles() {
  const items = [];
  for (const [path, f] of S.idx.files) {
    const lines = Array.isArray(f.lines) ? f.lines : [];
    const m = lines.filter((l) => l && l.match).length;
    const a = h("a", { href: hashFor(path), "data-path": path },
      h("span", { class: "fp", text: path }),
      h("span", { class: m ? "fc has" : "fc", text: `${plural(lines.length, "line")} · ${m} intent` }));
    items.push(h("li", null, a));
  }
  $("files").replaceChildren(...items);
}

function renderFile(path) {
  const f = S.idx.files.get(path);
  S.file = f;
  S.active = -1;
  $("blame-path").textContent = path;
  for (const a of $("files").querySelectorAll("a")) {
    if (a.getAttribute("data-path") === path) a.setAttribute("aria-current", "true");
    else a.removeAttribute("aria-current");
  }
  const lines = Array.isArray(f.lines) ? f.lines : [];
  S.rows = lines.map((l, i) => {
    const m = l && l.match;
    const cls = m ? `m p${colorFor(m.prompt_id)}` : null;
    const gutter = m ? h("td", { class: "g", title: `prompt ${m.prompt_id}`, text: short(m.commit || l.commit) || "·" })
                     : h("td", { class: "g", text: "·" });
    const tr = h("tr", { class: cls, tabindex: i === 0 ? "0" : "-1", "data-i": i },
      gutter, h("td", { class: "n", text: l.n }), h("td", { class: "c", text: l.text ?? "" }));
    return tr;
  });
  $("rows").replaceChildren(...S.rows);
  if (!S.rows.length) $("rows").append(h("tr", null, h("td", { class: "c empty", colspan: "3", text: "(empty file)" })));
  $("scroll").scrollTop = 0;
  renderDetail(null);
}

function row(dt, ...dd) {
  return h("div", null, h("dt", { text: dt }), h("dd", null, ...dd));
}

function block(dt, text, cls) {
  return h("div", { class: "wide" }, h("dt", { text: dt }),
    h("dd", null, text == null ? h("span", { class: "muted", text: "(not recorded)" }) : val(text, cls || "prose")));
}

function renderDetail(lineIdx) {
  const det = $("detail");
  const head = $("detail-path");
  if (lineIdx == null || !S.file) {
    head.textContent = "intent";
    det.replaceChildren(h("p", { class: "hint" },
      S.idx && S.idx.prompts.size
        ? "Select a line to see why it exists. Coloured lines carry recorded intent; each colour is one prompt."
        : "Select a line to see what gitmotive knows about it."));
    return;
  }
  const line = S.file.lines[lineIdx];
  const model = detailModel(S.file, line.n, S.idx);
  head.textContent = `intent for line ${line.n}`;
  const kids = [
    h("p", { class: "loc" }, h("span", { class: "prompt", "aria-hidden": "true", text: "$ " }),
      "git motive ", h("span", { text: `${S.file.path}:${line.n}` })),
    h("pre", { class: "src" }, h("code", { text: `  | ${line.text ?? ""}` })),
  ];
  const dl = h("dl", { class: "kv" },
    row("blame", h("span", { text: short(line.commit) || "uncommitted" }),
      line.author ? `  ${line.author}` : "", line.date ? `  ${line.date}` : ""));
  if (model.kind === "none") {
    dl.append(row("intent", h("span", { class: "none", text: "none recorded" })));
    kids.push(dl, h("p", { class: "hint" },
      "No recorded edit matches this line, so gitmotive says so instead of guessing."));
  } else {
    const m = line.match;
    const pc = `p${colorFor(m.prompt_id)}`;
    dl.append(
      row("prompt id", h("span", { class: `sw ${pc}`, text: m.prompt_id })),
      row("edited", timeEl(model.ts == null ? null : new Date(model.ts * 1000)),
        model.tool ? "  by " : "", model.tool ? val(model.tool) : ""),
      row("commit", model.commit ? val(model.commit) : h("span", { class: "muted", text: "uncommitted" })),
      row("session", model.session ? val(model.session) : h("span", { class: "muted", text: "unknown" })),
      row("agent", model.agent ? val(model.agent) : h("span", { class: "muted", text: "unknown" })),
      row("model", model.model === "unknown" ? h("span", { class: "muted", text: "unknown" }) : val(model.model)),
      row("match", model.why ? val(model.why) : h("span", { class: "muted", text: "unknown" })),
    );
    if (model.hq) {
      const q = model.hq;
      const where = [q.task || q.review || q.role, q.round ? `round ${q.round}` : null].filter(Boolean).join(" · ");
      dl.append(row("hq", val(q.kind || "task"), where ? "  " : "", where ? val(where) : ""));
      if (q.task_title) dl.append(row("task", val(q.task_title)));
      if (q.goal) dl.append(block("goal", q.goal));
    }
    dl.append(block("prompt", model.prompt), block("reasoning", model.reasoning));
    dl.append(h("div", { class: "wide" }, h("dt", { text: "also changed for same prompt" }),
      h("dd", null, model.siblings.length
        ? h("ul", { class: "sib" }, model.siblings.map((s) =>
          h("li", null, S.idx.files.has(s) ? h("a", { href: hashFor(s), text: s }) : val(s))))
        : h("span", { class: "muted", text: "(no other files)" }))));
    kids.push(dl);
  }
  det.replaceChildren(...kids);
}

// --- selection and keyboard --------------------------------------------------------------

function setActive(i, { focus = true } = {}) {
  if (!S.rows.length) return;
  i = Math.max(0, Math.min(S.rows.length - 1, i));
  const prev = S.rows[S.active] || S.rows[0];
  prev.setAttribute("tabindex", "-1");
  if (S.active >= 0) S.rows[S.active].removeAttribute("aria-current");
  S.active = i;
  const tr = S.rows[i];
  tr.setAttribute("tabindex", "0");
  tr.setAttribute("aria-current", "true");
  if (focus) tr.focus();
  else {
    // centre the row inside the code pane without scrolling the page itself
    const box = $("scroll");
    const dy = tr.getBoundingClientRect().top - box.getBoundingClientRect().top;
    box.scrollTop += dy - (box.clientHeight - tr.offsetHeight) / 2;
  }
}

function open(i, { focusPanel = false } = {}) {
  setActive(i, { focus: !focusPanel });
  renderDetail(i);
  const n = S.file.lines[i].n;
  if (history.replaceState) history.replaceState(null, "", hashFor(S.file.path, n));
  if (focusPanel) $("detail").focus();
}

function onKey(e) {
  if (e.altKey || e.ctrlKey || e.metaKey) return;
  const tr = e.target.closest && e.target.closest("tr[data-i]");
  if (!tr) return;
  const i = Number(tr.getAttribute("data-i"));
  const page = Math.max(1, Math.floor($("scroll").clientHeight / tr.offsetHeight) - 1);
  const moves = { ArrowDown: 1, j: 1, ArrowUp: -1, k: -1, PageDown: page, PageUp: -page };
  if (e.key in moves) setActive(i + moves[e.key]);
  else if (e.key === "Home") setActive(0);
  else if (e.key === "End") setActive(S.rows.length - 1);
  else if (e.key === "Enter") open(i, { focusPanel: true });
  else return;
  e.preventDefault();
}

function backToTable(e) {
  if (e.key !== "Escape" || !S.rows.length) return;
  e.preventDefault();
  setActive(S.active >= 0 ? S.active : 0);
}

function applyHash() {
  const { file, line } = parseHash(location.hash);
  const first = S.idx.files.keys().next().value;
  const path = file && S.idx.files.has(file) ? file : first;
  if (!S.file || S.file.path !== path) renderFile(path);
  if (file && !S.idx.files.has(file)) {
    $("detail").replaceChildren(h("p", { class: "hint" }, "No file ", h("code", { text: file }),
      " in this export; showing ", h("code", { text: path }), "."));
    return;
  }
  if (line != null) {
    const i = S.file.lines.findIndex((l) => l.n === line);
    if (i >= 0) {
      setActive(i, { focus: false });
      renderDetail(i);
      return;
    }
    $("detail").replaceChildren(h("p", { class: "hint" }, `Line ${line} is not in this export of `,
      h("code", { text: path }), "."));
  }
}

// --- load ------------------------------------------------------------------------------------

async function load() {
  setState("loading", h("p", { class: "state-msg" }, h("span", { class: "prompt", "aria-hidden": "true", text: "$ " }),
    "loading data.json", h("span", { class: "dots", "aria-hidden": "true" })));
  let data;
  try {
    const res = await fetch(new URL("data.json", import.meta.url), { credentials: "same-origin" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    data = await res.json();
  } catch (err) {
    showError(err instanceof SyntaxError ? "not valid JSON" : err.message || "network error");
    return;
  }
  try {
    S.data = data;
    S.idx = indexData(data);
    if (!S.idx.files.size) {
      showError("it lists no files");
      return;
    }
    let total = 0, matched = 0;
    for (const f of S.idx.files.values()) {
      for (const l of f.lines || []) { total++; if (l && l.match) matched++; }
    }
    renderMeta(data, total, matched);
    summaryBanner(total, matched);
    renderFiles();
    $("viewer").hidden = false;
    $("keys").hidden = false;
    S.file = null;
    applyHash();
  } catch (err) {
    S.idx = null;
    $("meta").hidden = true;
    showError("unreadable data");
  }
}

function wire() {
  const rows = $("rows");
  rows.addEventListener("keydown", onKey);
  rows.addEventListener("click", (e) => {
    const tr = e.target.closest("tr[data-i]");
    if (tr) open(Number(tr.getAttribute("data-i")));
  });
  $("viewer").addEventListener("keydown", backToTable);
  window.addEventListener("hashchange", () => S.idx && applyHash());
  load();
}

wire();
