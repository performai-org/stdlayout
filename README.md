# stdlayout

> English · [中文](README.zh-CN.md)

One script that gives any project a **standard directory layout** and a **complete `.gitignore`**, the same in every project, from day one.

```bash
cp init_project.py /path/to/your/project/
cd /path/to/your/project && python3 init_project.py
```

That's it. Python 3 standard library only; safe to re-run (never overwrites, only fills in what is missing). Not sure yet? Preview first with `python3 init_project.py --dry-run`: it changes nothing.

## Why we made it

Every new repo starts the same way: make a few folders, copy a `.gitignore` from the last project, call it close enough. The trouble shows up later.

- **One language, one template, many languages.** GitHub's `.gitignore` templates are written for a single language, but real projects mix them: a Python backend, a TypeScript frontend, a Rust extension, a Go tool. Build output from every language the template doesn't know ends up in git.
- **The copied `.gitignore` belongs to another project.** The old one was Python, the new one has a frontend; the old one had no sqlite, the new one does. Nothing warns you. One `git add .` later, the database is in history, and deleting the file doesn't take it out.
- **Git touches your data directories.** If `data/` or `logs/` isn't fully ignored, switching branches can delete those files or overwrite them with another branch's copy.
- **Config and secrets live somewhere different every time.** `config/`, `conf/`, a `.env` in the root: what may be committed and what must never be depends on someone remembering. The same kind of file also lands in a different directory in every project, sometimes in several directories within one, so finding it takes a while.
- **Handover and operations run on asking around.** Where's the database? Where do uploads go? Which directories need a backup? Every project answers differently, and a directory missing from a backup is usually found on the day you need to restore.

stdlayout gives every project the same layout and a `.gitignore` covering 30+ languages from day one, with a fixed place for real config (`config-ops/`), for templates (`config-ops-template/`), and for a `data-ops/sources.yaml` that says where the data lives, which is all a backup or ops person needs to read.

It is more than a `.gitignore` template: it also creates the directories, keeps real config and templates in separate places, and checks the result by asking git.

## What it does

- Creates the directories below. Project-specific data directories can be added with `--data`.
  - **Gitignored:** `data/ db/ upload/ logs/ tmp/ private-docs/` (plus `config-ops/` for real config and secrets).
  - **Committed:** `deploy/`, `config-ops-template/`, `data-ops/`, `tests/`, `manual-tests/`, `third-party/`, `reference-data/`, `assets/`. `third-party/` holds prebuilt libraries/tools, `reference-data/` holds static lookup data such as code tables, `assets/` holds images, icons, animations and videos the program shows (ready-made `images/ icons/ animations/ video/`; GitHub rejects files over 100 MB, how to handle those is up to you); all three are fully un-ignored. `tests/fixtures/` is created too.
- Appends a `.gitignore` for secrets, runtime data, OS/editors, and Python / Node & TypeScript / Rust / Go / Java & Kotlin / C & C++ / Swift / C# & .NET / Visual Studio / Android / Flutter / CUDA / ActionScript / Julia / Ada / Fortran / Haskell / Lua / OCaml / Perl / Qt / R / Ruby / Delphi (32 language options in all, listed in `--help`). **All are on by default**, so a mixed-language project is covered from the first commit; use `--lang python go ...` to limit them. Everything the script writes sits in one marked block (`# >>> BEGIN stdlayout` … `# <<< END stdlayout`); your own lines outside it are never touched, and rules you already have are not duplicated. Lock files such as `package-lock.json`, `Cargo.lock` and `go.sum` are deliberately not ignored, because they should be committed.
- If the project is still empty, writes `PROJECT_STRUCTURE.md` and `PROJECT_STRUCTURE.zh-CN.md` explaining the layout, linking back to [docs/](docs/PROJECT_STRUCTURE.md).
- If the directory is **not a git repository**, it does nothing and says so (you probably copied it to the wrong place). Add `--git-init` to let it run `git init -b main` first. Commits, remotes and pushing are left to you: see the [Git & GitHub guide](docs/GIT_GITHUB.md).
- Verifies with `git check-ignore` that ignored dirs are ignored, `deploy/` `data-ops/` `config-ops-template/` are not, and nothing sensitive is already tracked. If a check fails the exit code is 1, so it can run in CI.

## Options

- `--data DIR...` extra data dirs (created and gitignored)
- `--lang python go ...` limit language ignores (default: all)
- `--docs yes|no|auto` generate the structure docs
- `--no-deploy` `--no-config` `--no-data-ops` `--no-tests` `--no-manual-tests` `--no-third-party` `--no-reference-data` skip individual directories
- `--name-prefix P` warn if the repo name lacks the prefix
- `--gitignore-only` only write the `.gitignore` block, no directories or other files; an existing block is left untouched
- `--git-init` run `git init` first if the directory is not a repository
- `--undo` remove what the script generated, but only what you have not changed (preview with `--dry-run`)
- `--dry-run` show what would be done, change nothing
- `--version`

See `python3 init_project.py -h`.

See [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md) for the layout and rules.

## Part of a larger effort

stdlayout is the first open-source project of [performai.org](https://www.performai.org/)'s Zero-Ops plan, a series of tools that aim to bring the operations workload of a software project as close to zero as possible. The other automated-operations projects will be open-sourced one by one as they are completed. To be notified when they are released, follow the organization on GitHub: <https://github.com/performai-org/>

## Feedback

Found a problem or have a question? Please [open an issue](../../issues).

Made by [performai.org](https://www.performai.org/).
