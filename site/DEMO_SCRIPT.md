# gitmotive: 60-second demo script

A screen recording of one real loop: install, let Claude Code make an edit, commit, then ask
`git motive` why a line exists. Every command below is real. The sample output was captured from a
real run of these steps, so expect your own session id, times and wording.

Tagline: **git blame tells you who. git motive tells you why.**
URL: **gitmotive.tech**

## Before recording

- [ ] **Clean terminal:** new window, empty scrollback (`clear`), short prompt (`PS1='$ '`), no
      personal paths, hostnames or tokens on screen, notifications off.
- [ ] **Font size:** 20 pt or larger in the terminal, browser zoom at 125 %, window about 1280×720
      so text stays readable on a phone.
- [ ] **Prepared sample repo:** a throwaway repo with one small file and nothing private in it:

  ```sh
  mkdir -p ~/demo/fetcher/src && cd ~/demo/fetcher && git init -q
  printf 'import urllib.request\n\n\ndef fetch(url):\n    return urllib.request.urlopen(url, timeout=10).read()\n' > src/fetch.py
  git add . && git commit -qm "initial fetch"
  ```

- [ ] **`GITMOTIVE_STORE` unset:** run `unset GITMOTIVE_STORE` so events go to the repo's own
      `.gitmotive/` store, where `git motive` reads them.
- [ ] **Dry run once:** do the whole loop off camera, then `git reset --hard HEAD~1` and
      `rm -rf .gitmotive .claude` to start clean. If `gitmotive` is already installed, keep the
      install beat as is: it only reinstalls.
- [ ] **Demo viewer:** open `https://gitmotive.tech/demo/#gitmotive/cli.py:42` in a browser tab and
      check that the line is selected and the panel is filled. If that line shows `none recorded`,
      pick a line with a coloured gutter and use its link instead.

## Script

### 0:00–0:08 · Hook

**Screen:** `git blame` on a line nobody remembers writing.

```sh
git blame -L 5,5 src/fetch.py
```

**Voice-over:** "Agents write more code than reviewers can absorb. `git blame` tells you who. It
can't tell you why."

### 0:08–0:18 · Install

**Screen:** two commands, typed live.

```sh
pipx install gitmotive
gitmotive install --agent claude
```

Real output of the second command (paths shortened):

```text
wrote .../fetcher/.claude/settings.json
wrote .../fetcher/.git/hooks/post-commit
excluded .gitmotive/ from git
```

**Voice-over:** "Install it, hook it into Claude Code. One command each."

### 0:18–0:30 · A Claude Code edit

**Screen:** start `claude` in the repo and type the prompt. Let the edit land; cut the wait if it
runs long.

```text
add retry with exponential backoff to fetch() in src/fetch.py. First say in one sentence why, then edit.
```

**Voice-over:** "Now I work as usual. gitmotive records the prompt, the agent's reasoning and the
model as the edit happens."

### 0:30–0:36 · Commit

**Screen:** quit Claude Code and commit.

```sh
git add src/fetch.py
git commit -m "add retry to fetch"
```

**Voice-over:** "Commit like always. The post-commit hook stamps the edit to this commit."

### 0:36–0:46 · Ask why

**Screen:** point at the backoff line. Use the line number of
`delay = min(...)` in your own run.

```sh
git motive src/fetch.py:28
```

Real output from the dry run:

```text
src/fetch.py:28
  |         delay = min(max_delay, base_delay * (2 ** attempt))
  commit   1b3c66a5ee  demo  2026-11-10  add retry to fetch
  edited   2026-11-10 21:32  by Edit  session 3053553e  [same commit, line text in edit]  via claude  model claude-haiku-5-5
  prompt
    add retry with exponential backoff to fetch() in src/fetch.py. First say in one
    sentence why, then edit.
  reasoning
    Retrying transient network failures with exponential backoff keeps one flaky
    response from failing the whole call.
  (1 older candidate(s); use --all)
```

**Voice-over:** "`git motive`, file and line. The prompt, the reasoning and the model behind that
exact line."

### 0:46–0:54 · The live demo

**Screen:** switch to the browser tab on the deep link
`https://gitmotive.tech/demo/#gitmotive/cli.py:42`. The line is selected and the panel shows the
prompt, reasoning, agent and model. Press `j` twice to move down a line or two.

**Voice-over:** "The site runs on gitmotive's own history. Every coloured line links back to the
prompt that wrote it."

### 0:54–1:00 · Close

**Screen:** the gitmotive.tech home page hero, held still.

**Voice-over:** "git blame tells you who. git motive tells you why. gitmotive.tech."

## After recording

- Watch the whole take for anything private: paths, hostnames, other tabs, notifications.
- Delete the sample repo when done: `rm -rf ~/demo/fetcher`.
