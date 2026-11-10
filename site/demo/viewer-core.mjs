// gitmotive demo viewer: pure functions, no DOM. Tested by tests/js/viewer-core.test.mjs.

export const PALETTE_SIZE = 12;

/** Index an exported data.json: files by path, prompts by id. Tolerates missing sections. */
export function indexData(data) {
  const files = new Map();
  const prompts = new Map();
  const list = data && Array.isArray(data.files) ? data.files : [];
  for (const f of list) {
    if (f && typeof f.path === "string") files.set(f.path, f);
  }
  const ps = data && data.prompts && typeof data.prompts === "object" ? data.prompts : {};
  for (const [id, p] of Object.entries(ps)) prompts.set(id, p);
  return { files, prompts };
}

/** A stable palette index (0..PALETTE_SIZE-1) for a prompt id, used as the class "p<n>". */
export function colorFor(promptId) {
  const s = String(promptId ?? "");
  let h = 0x811c9dc5; // FNV-1a, 32-bit
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h % PALETTE_SIZE;
}

/**
 * "#<file>:<line>" -> { file, line }. Splits on the LAST ':' so paths may contain colons.
 * A suffix that is not a positive integer is part of the file name (line null).
 */
export function parseHash(hash) {
  let s = String(hash ?? "");
  if (s.startsWith("#")) s = s.slice(1);
  try {
    s = decodeURIComponent(s);
  } catch {
    // keep the raw text when it is not valid percent-encoding
  }
  if (!s) return { file: null, line: null };
  const i = s.lastIndexOf(":");
  if (i > 0 && /^[1-9]\d*$/.test(s.slice(i + 1))) {
    return { file: s.slice(0, i), line: Number(s.slice(i + 1)) };
  }
  return { file: s, line: null };
}

const ESC = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

export function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ESC[c]);
}

/**
 * The detail-panel model for one line. `file` is a file object from indexData (or its path).
 * No line, or a line without a match -> { kind: "none" }.
 */
export function detailModel(file, lineNo, idx) {
  const f = typeof file === "string" ? idx.files.get(file) : file;
  if (!f || !Array.isArray(f.lines)) return { kind: "none" };
  const line = f.lines.find((l) => l && l.n === lineNo);
  const m = line && line.match;
  if (!m) return { kind: "none" };
  const p = idx.prompts.get(m.prompt_id) || null;
  const siblings = p && Array.isArray(p.files) ? p.files.filter((x) => x !== f.path) : [];
  return {
    kind: "intent",
    prompt: p && p.text != null ? p.text : null,
    reasoning: m.reasoning ?? null,
    session: m.session ?? (p ? p.session ?? null : null),
    agent: m.agent ?? null,
    model: m.model ?? "unknown",
    ts: typeof m.ts === "number" ? m.ts : null,
    tool: m.tool ?? null,
    commit: m.commit ?? null,
    why: m.why ?? null,
    siblings,
    hq: (p && p.hq) || null,
  };
}
