# stdlayout

> [English](README.md) · 中文

一个脚本,给任何项目补全**标准目录结构**和**完整的 `.gitignore`**。

```bash
cp init_project.py /path/to/your/project/
cd /path/to/your/project && python3 init_project.py
```

就这样。只用 Python 3 标准库;可重复运行(不覆盖已有文件,只补缺少的)。

## 它做什么

- 创建 `data/ db/ upload/ logs/ tmp/ private-docs/`(全部 gitignore)、`deploy/`、`config-ops-template/`、`data-ops/`、`tests/`、`manual-tests/`、`third-party/`、`reference-data/`(这几个提交;`third-party/` 放现成的库和程序,`reference-data/` 放编码表之类的静态数据,两者里面一律不忽略)。
- 追加 `.gitignore`:密钥、运行时数据、系统/编辑器,以及 Python / Node & TypeScript / Rust / Go / Java & Kotlin / C & C++ / Swift / C# & .NET / Visual Studio / Android / Flutter / CUDA / ActionScript / Julia / Ada / Fortran / Haskell / Lua / OCaml / Perl / Qt / R / Ruby / Delphi。脚本写的内容都在同一个有标记的块里(`# >>> BEGIN stdlayout` … `# <<< END stdlayout`),块外你自己的行绝不改动,你已经有的规则不会重复写。
- 项目还是空的时,生成 `PROJECT_STRUCTURE.md` 和 `PROJECT_STRUCTURE.zh-CN.md`(目录介绍,带回本项目 [docs/](docs/PROJECT_STRUCTURE.zh-CN.md) 的链接)。
- 目录**不是 git 仓库**时什么都不做并提示(多半是复制错了位置);加 `--git-init` 则先执行 `git init -b main` 再继续。提交、关联远端、推送由你自己做,见 [Git 与 GitHub 使用指南](docs/GIT_GITHUB.zh-CN.md)。
- 用 `git check-ignore` 实测:该忽略的忽略了,`deploy/` `data-ops/` `config-ops-template/` 没被忽略,没有已被跟踪的敏感文件。

选项:`--data DIR...` 额外数据目录 · `--lang python go ...` 只加指定语言 · `--docs yes|no|auto` · `--no-deploy` `--no-config` `--no-data-ops` `--no-tests` `--no-manual-tests` `--no-third-party` `--no-reference-data` · `--name-prefix P` 仓库名不以该前缀开头时提示 · `--git-init` · `--undo` 撤销脚本生成的内容,只撤销你没改过的(可先用 `--dry-run` 预览) · `--dry-run`。详见 `python3 init_project.py -h`。

目录与规则见 [docs/PROJECT_STRUCTURE.zh-CN.md](docs/PROJECT_STRUCTURE.zh-CN.md)。

发布前:确认 `init_project.py` 顶部的 `PUBLIC_REPO` 和 `LICENSE` 里的版权人。
