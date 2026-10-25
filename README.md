# stdlayout

> English · [中文](README.zh-CN.md)

One script that gives any project a **standard directory layout** and a **complete `.gitignore`**.

```bash
cp init_project.py /path/to/your/project/
cd /path/to/your/project && python3 init_project.py
```

That's it. Python 3 standard library only; safe to re-run (never overwrites, only fills in what is missing).

## What it does

- Creates `data/ db/ upload/ logs/ tmp/ private-docs/` (all gitignored), `deploy/`, `config-ops-template/`, `data-ops/`, `tests/`, `manual-tests/`, `third-party/`, `reference-data/` (committed; `third-party/` holds prebuilt libraries/tools, `reference-data/` holds static lookup data such as code tables; both are fully un-ignored).
- Appends a `.gitignore` for secrets, runtime data, OS/editors, and Python / Node & TypeScript / Rust / Go / Java & Kotlin / C & C++ / Swift / C# & .NET / Visual Studio / Android / Flutter / CUDA / ActionScript / Julia / Ada / Fortran / Haskell / Lua / OCaml / Perl / Qt / R / Ruby / Delphi. Everything the script writes sits in one marked block (`# >>> BEGIN stdlayout` … `# <<< END stdlayout`); your own lines outside it are never touched, and rules you already have are not duplicated.
- If the project is still empty, writes `PROJECT_STRUCTURE.md` and `PROJECT_STRUCTURE.zh-CN.md` explaining the layout, linking back to [docs/](docs/PROJECT_STRUCTURE.md).
- If the directory is **not a git repository**, it does nothing and says so (you probably copied it to the wrong place). Add `--git-init` to let it run `git init -b main` first. Commits, remotes and pushing are left to you: see the [Git & GitHub guide](docs/GIT_GITHUB.md).
- Verifies with `git check-ignore` that ignored dirs are ignored, `deploy/` `data-ops/` `config-ops-template/` are not, and nothing sensitive is already tracked.

Options: `--data DIR...` extra data dirs · `--lang python go ...` limit language ignores · `--docs yes|no|auto` · `--no-deploy` `--no-config` `--no-data-ops` `--no-tests` `--no-manual-tests` `--no-third-party` `--no-reference-data` · `--name-prefix P` warn if the repo name lacks the prefix · `--gitignore-only` only write the `.gitignore` block, no directories or other files; an existing block is left untouched · `--git-init` · `--undo` remove what the script generated, but only what you have not changed (preview with `--dry-run`) · `--dry-run`. See `python3 init_project.py -h`.

See [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md) for the layout and rules.

Before publishing: check `PUBLIC_REPO` at the top of `init_project.py` and the copyright holder in `LICENSE`.
