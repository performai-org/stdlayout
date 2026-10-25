# Git & GitHub Guide

> English · [中文](GIT_GITHUB.zh-CN.md) · Part of [stdlayout](https://github.com/performai-org/stdlayout)

`init_project.py` only prepares a project (directories, `.gitignore`, docs). Everything about commits, remotes and GitHub is **yours to do** — this guide lists the commands, in the order you will need them.

## 0. One-time setup

```bash
git --version                                   # git installed?
git config --global user.name  "Your Name"
git config --global user.email "you@example.com"
git config --global init.defaultBranch main     # new repos start on "main"
```

**Authenticate to GitHub** (pick one):

| Way | Setup |
|---|---|
| SSH (recommended) | `ssh-keygen -t ed25519 -C "you@example.com"`, then add `~/.ssh/id_ed25519.pub` at GitHub → Settings → SSH and GPG keys. Test: `ssh -T git@github.com` |
| GitHub CLI | Install [`gh`](https://cli.github.com/), then `gh auth login` (also sets up HTTPS credentials) |
| HTTPS + token | Create a personal access token at GitHub → Settings → Developer settings; use it as the password |

Remote URL forms: SSH `git@github.com:OWNER/REPO.git`, HTTPS `https://github.com/OWNER/REPO.git`.

## 1. Start from an empty directory

```bash
mkdir myproject && cd myproject
cp /path/to/init_project.py .
python3 init_project.py --git-init     # git init -b main + directories + .gitignore + docs
```

`--git-init` is the only way the script creates a repository. Without it, a directory that is not a git repository is left untouched and the script tells you so (you probably copied it to the wrong place). If you prefer, run `git init -b main` yourself and then `python3 init_project.py`.

First commit:

```bash
git status                              # look before you add: nothing secret, nothing huge
git add .
git commit -m "init"
```

If `git status` lists a file you did not expect, fix `.gitignore` first (see [section 7](#7-files-that-are-ignored-but-you-want-to-commit)).

## 2. Put it on GitHub — new project

**Option A: `gh` (one step)**

```bash
gh repo create OWNER/REPO --private --source=. --remote=origin --push
# use --public instead of --private for an open-source project
```

**Option B: website + git**

1. GitHub → New repository. Name it; leave **"Add a README / .gitignore / license" unchecked** so the repo is empty.
2. Then:

```bash
git remote add origin git@github.com:OWNER/REPO.git
git push -u origin main
```

`-u` remembers `origin/main`, so later `git push` / `git pull` need no arguments.

## 3. Connect to an existing GitHub project

**Best: clone first, then run the script inside the clone.**

```bash
git clone git@github.com:OWNER/REPO.git
cd REPO
cp /path/to/init_project.py .
python3 init_project.py                 # already a git repo, no --git-init needed
git add . && git commit -m "add stdlayout structure"
git push
```

**Already have local commits and want to attach the remote:**

```bash
git remote add origin git@github.com:OWNER/REPO.git
git fetch origin
git pull origin main --allow-unrelated-histories   # merge; resolve conflicts if any
git push -u origin main
```

If you skip the `pull` and the remote already has commits (README, LICENSE), `git push` is rejected with `non-fast-forward`. Do **not** reach for `--force` — it deletes the remote's history.

## 4. Daily workflow

```bash
git status                  # what changed
git diff                    # see the changes (unstaged)
git add path/to/file        # stage specific files (prefer this over `git add .`)
git commit -m "message"     # record
git pull --rebase           # get others' work first
git push                    # publish
git log --oneline --graph   # history
```

Undo, safely:

```bash
git restore path/to/file            # discard unstaged edits to a file
git restore --staged path/to/file   # unstage
git revert <commit>                 # new commit that undoes an old one (safe for shared branches)
```

## 5. Branches and pull requests

```bash
git switch -c feature/xyz           # create + switch
# ...edit, commit...
git push -u origin feature/xyz
gh pr create --fill                 # or open the PR on github.com
# after merge:
git switch main && git pull --rebase
git branch -d feature/xyz
```

## 6. Remotes, tags

```bash
git remote -v                                   # list remotes
git remote set-url origin NEW_URL               # change the URL
git tag -a v1.0.0 -m "release 1.0.0"
git push origin v1.0.0                          # tags are pushed explicitly
```

## 7. Files that are ignored but you want to commit

stdlayout ignores generated output such as `*.exe`, `*.dll`, `*.jar`. If you really need one in git (a vendored tool, a test fixture):

```bash
git add -f tools/foo.exe            # one-off; once tracked, later changes commit normally
```

or un-ignore it permanently. The script keeps everything it writes between the `# >>> BEGIN stdlayout` and `# <<< END stdlayout` lines of `.gitignore` and never touches lines outside them, so add your own rules **below the END line**:

```
!tools/foo.exe
```

Rules of thumb: the `!` line must come **after** the ignore rule it overrides (that is why it goes below the END line), and a file cannot be re-included if its **parent directory** is ignored. In VS Code, ignored files do not show in Source Control, so use the terminal command or the `!` line. For a rule only you need, put it in `.git/info/exclude` instead of `.gitignore`.

## 8. If a secret or data file was committed

```bash
git rm -r --cached config-ops/      # stop tracking, keep the file on disk
git commit -m "stop tracking config-ops"
```

Removing it from the latest commit does **not** remove it from history. If it was ever pushed, treat the secret as leaked and **rotate it**. To erase it from history use [`git filter-repo`](https://github.com/newren/git-filter-repo) (then force-push, coordinate with your team).

## 9. Quick troubleshooting

| Message | Meaning / fix |
|---|---|
| `not a git repository` | Wrong directory, or run `git init -b main` / `init_project.py --git-init` |
| `Permission denied (publickey)` | SSH key not added to GitHub; `ssh -T git@github.com` to test |
| `remote origin already exists` | `git remote set-url origin NEW_URL` instead of `add` |
| `rejected ... non-fast-forward` | Remote has commits you lack: `git pull --rebase`, then push |
| `refusing to merge unrelated histories` | Add `--allow-unrelated-histories` to the pull (section 3) |
| File still tracked after adding it to `.gitignore` | `git rm --cached <path>`; ignoring never un-tracks a file |
