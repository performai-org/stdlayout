# About the standard layout / 关于标准目录结构

This project was completed by [stdlayout](https://github.com/performai-org/stdlayout)'s `init_project.py`.
本项目的目录结构和 `.gitignore` 由 [stdlayout](https://github.com/performai-org/stdlayout) 的 `init_project.py` 补全。

## English

`init_project.py` is a single, dependency-free Python script. Run `python3 init_project.py` in a project root and it:

- creates the standard directories `data/ db/ upload/ logs/ tmp/` (runtime data, gitignored), `private-docs/` (private notes, gitignored), `deploy/`, `config-ops-template/`, `data-ops/`, `tests/`, `manual-tests/`, `third-party/`, `reference-data/` (committed);
- makes sure `.gitignore` covers real config and secrets (`config-ops/`, `.env*`), runtime data, and build output of Python, Node/TypeScript, Rust, Go, Java/Kotlin, C/C++, Swift, C#/VB.NET/.NET, Visual Studio, Android, Flutter/Dart, CUDA, ActionScript, Julia, Ada, Fortran, Haskell, Lua, OCaml, Perl, Qt, R, Ruby and Delphi;
- never overwrites existing files; re-running only fills in what is missing;
- does nothing in a directory that is not a git repository, unless `--git-init` is given (it then runs `git init -b main` first).

Read what the layout is and why:
- [Standard project structure (English)](https://github.com/performai-org/stdlayout/blob/main/docs/PROJECT_STRUCTURE.md)
- [项目标准目录结构(中文)](https://github.com/performai-org/stdlayout/blob/main/docs/PROJECT_STRUCTURE.zh-CN.md)

## 中文

`init_project.py` 是一个无依赖的 Python 脚本。在项目根目录运行 `python3 init_project.py`,它会:

- 创建标准目录:`data/ db/ upload/ logs/ tmp/`(运行时数据,不提交)、`private-docs/`(私有笔记,不提交)、`deploy/`、`config-ops-template/`、`data-ops/`、`tests/`、`manual-tests/`、`third-party/`、`reference-data/`(提交);
- 确保 `.gitignore` 覆盖真实配置与密钥(`config-ops/`、`.env*`)、运行时数据,以及 Python、Node/TypeScript、Rust、Go、Java/Kotlin、C/C++、Swift、C#/VB.NET/.NET、Visual Studio、Android、Flutter/Dart、CUDA、ActionScript、Julia、Ada、Fortran、Haskell、Lua、OCaml、Perl、Qt、R、Ruby、Delphi 的构建产物;
- 绝不覆盖已有文件,重复运行只补缺少的;
- 目录不是 git 仓库时什么都不做,除非加 `--git-init`(此时先执行 `git init -b main`)。

目录是什么、为什么这样:
- [项目标准目录结构(中文)](https://github.com/performai-org/stdlayout/blob/main/docs/PROJECT_STRUCTURE.zh-CN.md)
- [Standard project structure (English)](https://github.com/performai-org/stdlayout/blob/main/docs/PROJECT_STRUCTURE.md)
- [Git 与 GitHub 使用指南](https://github.com/performai-org/stdlayout/blob/main/docs/GIT_GITHUB.zh-CN.md) · [Git & GitHub guide](https://github.com/performai-org/stdlayout/blob/main/docs/GIT_GITHUB.md)
