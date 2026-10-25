# Git 与 GitHub 使用指南

> [English](GIT_GITHUB.md) · 中文 · 属于 [stdlayout](https://github.com/performai-org/stdlayout)

`init_project.py` 只负责把项目准备好(目录、`.gitignore`、文档)。提交、远端、GitHub 的操作**都由你自己做**,本文按先后顺序列出需要的命令。

## 0. 一次性准备

```bash
git --version                                   # 装了 git 吗
git config --global user.name  "你的名字"
git config --global user.email "you@example.com"
git config --global init.defaultBranch main     # 新仓库默认分支叫 main
```

**登录 GitHub**(任选一种):

| 方式 | 做法 |
|---|---|
| SSH(推荐) | `ssh-keygen -t ed25519 -C "you@example.com"`,把 `~/.ssh/id_ed25519.pub` 加到 GitHub → Settings → SSH and GPG keys。测试:`ssh -T git@github.com` |
| GitHub CLI | 安装 [`gh`](https://cli.github.com/),`gh auth login`(同时配好 HTTPS 凭据) |
| HTTPS + token | 在 GitHub → Settings → Developer settings 创建 personal access token,当密码用 |

远端地址两种写法:SSH `git@github.com:OWNER/REPO.git`,HTTPS `https://github.com/OWNER/REPO.git`。

## 1. 从空目录开始

```bash
mkdir myproject && cd myproject
cp /path/to/init_project.py .
python3 init_project.py --git-init     # git init -b main + 目录 + .gitignore + 文档
```

`--git-init` 是脚本创建仓库的唯一方式。不加它时,不是 git 仓库的目录**什么都不会改**,脚本只提示你(多半是复制错了位置)。你也可以自己先 `git init -b main`,再运行 `python3 init_project.py`。

第一次提交:

```bash
git status                              # 先看再加:不要有密钥、不要有大文件
git add .
git commit -m "init"
```

`git status` 里如果出现你不想要的文件,先改 `.gitignore`(见[第 7 节](#7-被忽略但你想提交的文件))。

## 2. 推到 GitHub — 新项目

**方式 A:用 `gh`(一步)**

```bash
gh repo create OWNER/REPO --private --source=. --remote=origin --push
# 开源项目把 --private 换成 --public
```

**方式 B:网页 + git**

1. GitHub → New repository。起名字,**不要勾选** "Add a README / .gitignore / license",让仓库保持为空。
2. 然后:

```bash
git remote add origin git@github.com:OWNER/REPO.git
git push -u origin main
```

`-u` 记住 `origin/main`,以后 `git push` / `git pull` 不用再带参数。

## 3. 连接 GitHub 上已有的项目

**最稳妥:先 clone,再在 clone 出来的目录里运行脚本。**

```bash
git clone git@github.com:OWNER/REPO.git
cd REPO
cp /path/to/init_project.py .
python3 init_project.py                 # 已经是 git 仓库,不需要 --git-init
git add . && git commit -m "add stdlayout structure"
git push
```

**本地已经有提交,想关联远端:**

```bash
git remote add origin git@github.com:OWNER/REPO.git
git fetch origin
git pull origin main --allow-unrelated-histories   # 合并,有冲突就解决
git push -u origin main
```

跳过 `pull` 而远端已有提交(README、LICENSE 之类)时,`git push` 会因 `non-fast-forward` 被拒绝。**不要**用 `--force` 硬推,那会删掉远端历史。

## 4. 日常流程

```bash
git status                  # 改了什么
git diff                    # 看具体改动(未暂存)
git add path/to/file        # 暂存指定文件(比 `git add .` 更稳妥)
git commit -m "说明"        # 提交
git pull --rebase           # 先拿别人的更新
git push                    # 推送
git log --oneline --graph   # 看历史
```

安全地撤销:

```bash
git restore path/to/file            # 丢弃某文件未暂存的修改
git restore --staged path/to/file   # 取消暂存
git revert <commit>                 # 用新提交抵消旧提交(共享分支上用这个)
```

## 5. 分支与 Pull Request

```bash
git switch -c feature/xyz           # 新建并切换
# ……修改、提交……
git push -u origin feature/xyz
gh pr create --fill                 # 或在 github.com 网页上开 PR
# 合并之后:
git switch main && git pull --rebase
git branch -d feature/xyz
```

## 6. 远端与标签

```bash
git remote -v                                   # 查看远端
git remote set-url origin NEW_URL               # 改远端地址
git tag -a v1.0.0 -m "release 1.0.0"
git push origin v1.0.0                          # 标签要单独推送
```

## 7. 被忽略但你想提交的文件

stdlayout 会忽略 `*.exe`、`*.dll`、`*.jar` 这类生成物。确实需要提交某个(自带的工具、测试夹具)时:

```bash
git add -f tools/foo.exe            # 一次性;一旦被跟踪,以后的修改正常提交
```

或者永久放行。脚本写的所有规则都在 `.gitignore` 的 `# >>> BEGIN stdlayout` 与 `# <<< END stdlayout` 两行之间,块外的行脚本绝不会碰,所以请把你自己的规则写在 **END 行下面**:

```
!tools/foo.exe
```

经验:`!` 行必须写在被它覆盖的忽略规则**之后**(所以放在 END 行下面);如果文件的**父目录**被忽略,放行单个文件无效。VS Code 的源代码管理面板看不到被忽略的文件,所以用终端命令或 `!` 行。只想自己本机生效的规则,写进 `.git/info/exclude`,不要写进 `.gitignore`。

## 8. 误提交了密钥或数据文件

```bash
git rm -r --cached config-ops/      # 不再跟踪,磁盘上的文件保留
git commit -m "stop tracking config-ops"
```

从最新提交里删掉**不等于**从历史里删掉。只要推送过,就把这个密钥当作已泄露并**更换**。要从历史里彻底清除用 [`git filter-repo`](https://github.com/newren/git-filter-repo)(之后需要强推,并通知团队)。

## 9. 常见报错

| 提示 | 含义 / 处理 |
|---|---|
| `not a git repository` | 目录不对;或运行 `git init -b main` / `init_project.py --git-init` |
| `Permission denied (publickey)` | SSH 公钥没加到 GitHub;用 `ssh -T git@github.com` 测试 |
| `remote origin already exists` | 用 `git remote set-url origin NEW_URL`,不要再 `add` |
| `rejected ... non-fast-forward` | 远端有你没有的提交:`git pull --rebase` 后再推 |
| `refusing to merge unrelated histories` | pull 时加 `--allow-unrelated-histories`(见第 3 节) |
| 加进 `.gitignore` 后文件仍被跟踪 | `git rm --cached <路径>`;忽略规则不会让已跟踪的文件脱离跟踪 |
