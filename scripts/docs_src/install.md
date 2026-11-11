# Install

gitmotive needs Python 3.10 or newer and git. It is pure standard library, with no runtime dependencies, no network calls and no telemetry.

## With pipx

```sh
pipx install gitmotive
```

pipx puts `gitmotive` and `git-motive` on your PATH. Because git runs `git-motive` for `git motive`, both spellings work.

## With the install script

```sh
curl -fsSL https://gitmotive.tech/install.sh | sh
```

The script checks for Python 3.10 or newer. If pipx is present it runs `pipx install gitmotive`. Otherwise it creates a venv at `~/.gitmotive/venv` and writes `gitmotive` and `git-motive` wrappers to `~/.local/bin`. Any arguments after `sh -s --` are passed to `gitmotive install`:

```sh
curl -fsSL https://gitmotive.tech/install.sh | sh -s -- --agent claude --scope user
```

## From a clone

```sh
git clone https://github.com/rvasqz86/gitmotive
cd gitmotive
sh install.sh
```

`install.sh` installs this checkout into `~/.gitmotive/venv` and writes the same two wrappers to `~/.local/bin`. Arguments are passed to `gitmotive install`, for example `sh install.sh --agent claude,cursor --scope user`.

Check the install:

```sh
gitmotive --version
```
