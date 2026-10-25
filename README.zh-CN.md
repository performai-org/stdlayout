# stdlayout

> [English](README.md) · 中文

一个脚本,给任何项目补全**标准目录结构**和**完整的 `.gitignore`**。

```bash
cp init_project.py /path/to/your/project/
cd /path/to/your/project && python3 init_project.py
```

就这样。只用 Python 3 标准库;可重复运行(不覆盖已有文件,只补缺少的)。

## 为什么做这个

每个新仓库的开头都差不多:建几个目录,从上一个项目复制一份 `.gitignore`,觉得够用了。问题是后来才冒出来的。

- **抄来的 `.gitignore` 是别的项目的。** 旧项目是 Python,新项目加了前端;旧项目没用 sqlite,新项目用了。没有任何提示,一次 `git add .`,数据库就进了历史,删文件也删不掉它。
- **数据目录被 git 碰了。** `data/`、`logs/` 没忽略干净,切分支时里面的文件可能被删掉,或者被另一个分支的版本覆盖。
- **配置和密钥每次放的地方都不一样。** `config/`、`conf/`、根目录的 `.env`:什么能提交、什么绝对不能提交,全靠有人记得。
- **交接和运维靠问。** 数据库在哪?上传的文件放哪?哪些目录要备份?每个项目答案都不同,漏备一个目录,往往等到要恢复的那天才发现。

stdlayout 让每个项目从第一天起就有同一套目录和覆盖 30 多种语言的 `.gitignore`:真实配置固定放 `config-ops/`,模板放 `config-ops-template/`,`data-ops/sources.yaml` 写明数据在哪,做备份和运维的人只读它就够了。

## 它做什么

- 创建 `data/ db/ upload/ logs/ tmp/ private-docs/`(全部 gitignore)、`deploy/`、`config-ops-template/`、`data-ops/`、`tests/`、`manual-tests/`、`third-party/`、`reference-data/`(这几个提交;`third-party/` 放现成的库和程序,`reference-data/` 放编码表之类的静态数据,两者里面一律不忽略)。
- 追加 `.gitignore`:密钥、运行时数据、系统/编辑器,以及 Python / Node & TypeScript / Rust / Go / Java & Kotlin / C & C++ / Swift / C# & .NET / Visual Studio / Android / Flutter / CUDA / ActionScript / Julia / Ada / Fortran / Haskell / Lua / OCaml / Perl / Qt / R / Ruby / Delphi。脚本写的内容都在同一个有标记的块里(`# >>> BEGIN stdlayout` … `# <<< END stdlayout`),块外你自己的行绝不改动,你已经有的规则不会重复写。
- 项目还是空的时,生成 `PROJECT_STRUCTURE.md` 和 `PROJECT_STRUCTURE.zh-CN.md`(目录介绍,带回本项目 [docs/](docs/PROJECT_STRUCTURE.zh-CN.md) 的链接)。
- 目录**不是 git 仓库**时什么都不做并提示(多半是复制错了位置);加 `--git-init` 则先执行 `git init -b main` 再继续。提交、关联远端、推送由你自己做,见 [Git 与 GitHub 使用指南](docs/GIT_GITHUB.zh-CN.md)。
- 用 `git check-ignore` 实测:该忽略的忽略了,`deploy/` `data-ops/` `config-ops-template/` 没被忽略,没有已被跟踪的敏感文件。

选项:`--data DIR...` 额外数据目录 · `--lang python go ...` 只加指定语言 · `--docs yes|no|auto` · `--no-deploy` `--no-config` `--no-data-ops` `--no-tests` `--no-manual-tests` `--no-third-party` `--no-reference-data` · `--name-prefix P` 仓库名不以该前缀开头时提示 · `--gitignore-only` 只写 `.gitignore` 块,不建目录和其他文件;已有该块则不动 · `--git-init` · `--undo` 撤销脚本生成的内容,只撤销你没改过的(可先用 `--dry-run` 预览) · `--dry-run` · `--version`。详见 `python3 init_project.py -h`。

目录与规则见 [docs/PROJECT_STRUCTURE.zh-CN.md](docs/PROJECT_STRUCTURE.zh-CN.md)。

由 [performai.org](https://www.performai.org/) 出品。
