// node --test tests/js/viewer-core.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  PALETTE_SIZE, indexData, colorFor, parseHash, escapeHtml, detailModel,
} from "../../site/demo/viewer-core.mjs";

const fixture = JSON.parse(readFileSync(new URL("./fixture.json", import.meta.url), "utf8"));
const idx = indexData(fixture);

test("PALETTE_SIZE matches the twelve .p classes", () => {
  assert.equal(PALETTE_SIZE, 12);
});

test("indexData indexes files by path and prompts by id", () => {
  assert.ok(idx.files instanceof Map && idx.prompts instanceof Map);
  assert.deepEqual([...idx.files.keys()], ["gitmotive/cli.py", "dir/a:b.py"]);
  assert.equal(idx.files.get("gitmotive/cli.py").lines.length, 5);
  assert.deepEqual([...idx.prompts.keys()].sort(), ["16d846335950", "7e0c1d2b3a49"]);
  assert.equal(idx.prompts.get("16d846335950").hq.kind, "implement");
});

test("indexData tolerates empty or partial data (zero-match export)", () => {
  for (const d of [null, {}, { files: [] }, { files: [{ path: "a.py", lines: [] }], prompts: {} }]) {
    const i = indexData(d);
    assert.ok(i.files instanceof Map && i.prompts instanceof Map);
    assert.equal(i.prompts.size, 0);
  }
});

test("colorFor is stable and in range", () => {
  const ids = ["16d846335950", "7e0c1d2b3a49", "", "a", "b", "ffffffffffff"];
  for (const id of ids) {
    const c = colorFor(id);
    assert.ok(Number.isInteger(c) && c >= 0 && c < PALETTE_SIZE, `${id} -> ${c}`);
    assert.equal(colorFor(id), c, "same id, same colour");
  }
  assert.equal(colorFor(null), colorFor(""));
  const seen = new Set();
  for (let i = 0; i < 500; i++) seen.add(colorFor(`prompt-${i}`));
  assert.equal(seen.size, PALETTE_SIZE, "a spread of ids reaches every palette slot");
});

test("parseHash", () => {
  assert.deepEqual(parseHash(""), { file: null, line: null });
  assert.deepEqual(parseHash("#"), { file: null, line: null });
  assert.deepEqual(parseHash("#a.py"), { file: "a.py", line: null });
  assert.deepEqual(parseHash("#a.py:x"), { file: "a.py:x", line: null });
  assert.deepEqual(parseHash("#dir/a:b.py:7"), { file: "dir/a:b.py", line: 7 });
  assert.deepEqual(parseHash("#gitmotive/cli.py:42"), { file: "gitmotive/cli.py", line: 42 });
  assert.deepEqual(parseHash("gitmotive/cli.py:42"), { file: "gitmotive/cli.py", line: 42 });
  assert.deepEqual(parseHash("#a.py:0"), { file: "a.py:0", line: null });
  assert.deepEqual(parseHash("#my%20dir/a.py:3"), { file: "my dir/a.py", line: 3 });
  assert.deepEqual(parseHash("#bad%zz.py:3"), { file: "bad%zz.py", line: 3 });
});

test("escapeHtml", () => {
  assert.equal(escapeHtml(`<script>alert('x')</script> & "q"`),
    "&lt;script&gt;alert(&#39;x&#39;)&lt;/script&gt; &amp; &quot;q&quot;");
  assert.equal(escapeHtml(null), "");
  assert.equal(escapeHtml(42), "42");
  assert.equal(escapeHtml("plain"), "plain");
});

test("detailModel with a match (hq block, siblings)", () => {
  const f = idx.files.get("gitmotive/cli.py");
  const m = detailModel(f, 3, idx);
  assert.equal(m.kind, "intent");
  assert.equal(m.prompt, "Implement .hq/tasks/14-demo-viewer.md, round 1.");
  assert.equal(m.reasoning, "Adding the why subcommand; it resolves a file:line through git blame.");
  assert.equal(m.session, "01a1c67b");
  assert.equal(m.agent, "claude");
  assert.equal(m.model, "claude-opus-5-5");
  assert.equal(m.ts, 1794331334.96);
  assert.equal(m.tool, "Edit");
  assert.equal(m.commit, "5934f9c1ab");
  assert.equal(m.why, "same commit, line text in edit");
  assert.deepEqual(m.siblings, ["dir/a:b.py", "site/demo/viewer.js"]);
  assert.equal(m.hq.task_title, "Task 14: Live demo viewer");
  assert.equal(m.hq.goal, "Build /demo/, a client-side viewer for data.json.");
  assert.deepEqual(detailModel("gitmotive/cli.py", 3, idx), m, "a path works like the file object");
});

test("detailModel without a match", () => {
  const f = idx.files.get("gitmotive/cli.py");
  assert.deepEqual(detailModel(f, 1, idx), { kind: "none" });
  assert.deepEqual(detailModel(f, 999, idx), { kind: "none" });
  assert.deepEqual(detailModel("nope.py", 1, idx), { kind: "none" });
  assert.deepEqual(detailModel(f, 1, indexData({})), { kind: "none" });
});

test("detailModel with a null model shows unknown; hostile text is returned raw", () => {
  const m = detailModel(idx.files.get("gitmotive/cli.py"), 4, idx);
  assert.equal(m.kind, "intent");
  assert.equal(m.model, "unknown");
  assert.equal(m.agent, null);
  assert.equal(m.reasoning, null);
  assert.equal(m.hq, null);
  assert.deepEqual(m.siblings, []);
  // the model carries data, not markup: escaping happens at render time
  assert.equal(m.prompt, `render <script>alert(1)</script> & "quotes" safely`);
});

test("matched lines on one prompt share a colour", () => {
  const lines = idx.files.get("gitmotive/cli.py").lines.filter((l) => l.match);
  const byPrompt = new Map();
  for (const l of lines) {
    const c = colorFor(l.match.prompt_id);
    if (byPrompt.has(l.match.prompt_id)) assert.equal(byPrompt.get(l.match.prompt_id), c);
    byPrompt.set(l.match.prompt_id, c);
  }
});
