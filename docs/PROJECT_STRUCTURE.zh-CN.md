# 项目标准目录结构

> 由 [stdlayout](https://github.com/performai-org/stdlayout) 生成。本文最新版:
> [English](https://github.com/performai-org/stdlayout/blob/main/docs/PROJECT_STRUCTURE.md) · [中文](https://github.com/performai-org/stdlayout/blob/main/docs/PROJECT_STRUCTURE.zh-CN.md)
>
> 英文版:[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)

在项目根目录随时运行 `python3 init_project.py`:只补全缺少的东西,绝不覆盖已有文件。

## 目录一览

```
<project>/
├── deploy/                 # deploy.sh, healthcheck.sh, *.service        (committed)
├── config-ops-template/    # config templates, *.example, no real values (committed)
├── config-ops/             # REAL config & secrets                        (gitignored)
├── data-ops/               # sources.yaml: where the data lives           (committed)
├── reference-data/         # static lookup data shipped with the code     (committed)
├── tests/                  # test cases; run before every commit          (committed)
├── manual-tests/           # checklists for tests done by hand            (committed)
├── third-party/            # prebuilt libraries / tools you did not build (committed)
├── data/                   # data files                                   (gitignored)
├── db/                     # database files (sqlite, ...)                 (gitignored)
├── upload/                 # user-uploaded files                          (gitignored)
├── logs/                   # log files                                    (gitignored)
├── tmp/                    # scratch / cache                              (gitignored)
├── private-docs/            # your private notes / intermediate docs       (gitignored)
├── PROJECT_STRUCTURE.md    # this file
└── .gitignore
```

| 路径 | 提交? | 用途 |
|---|---|---|
| `deploy/` | 提交 | `deploy.sh`(装依赖、迁移、重启,必须幂等)、`healthcheck.sh`(退出码 0 = 健康)、service 单元。均可选。 |
| `config-ops-template/` | 提交 | 程序需要的每个配置文件的模板,值用占位符。可开源。 |
| `config-ops/` | **不提交** | 真实配置与密钥。程序**只**从这里读配置。目录 `700`、文件 `600`。 |
| `data-ops/` | 提交 | `sources.yaml` 声明数据在哪(数据库、目录),供备份工具使用。 |
| `reference-data/` | 提交 | 静态、无敏感信息、所有环境都一样的数据(编码表、对照表、字典)。里面的一切都不被忽略,包括 `*.db`/`*.sqlite`。不放运行时数据(`data/`)和各环境不同的配置(`config-ops/`)。 |
| `tests/` | 提交 | 测试用例。一条命令跑完全部;CI 和每位贡献者在结束任务前运行它。 |
| `manual-tests/` | 提交 | 需要人手工执行的测试清单和脚本。只放 `.md` / `.sh`,文件名要避开测试运行器的匹配规则。 |
| `third-party/` | 提交 | 不是本仓库构建出来的现成库和程序(预编译二进制、vendored 库)。里面的一切都不被忽略,包括 `*.exe`/`*.dll`/`build/`。在 `MANIFEST.md` 记录来源、版本、许可证、sha256。 |
| `data/` | **不提交** | 运行时产生的数据文件。 |
| `db/` | **不提交** | 数据库文件(sqlite 等)。 |
| `upload/` | **不提交** | 用户上传的文件。 |
| `logs/` | **不提交** | 日志文件。 |
| `tmp/` | **不提交** | 临时文件、缓存。 |
| `private-docs/` | **不提交** | 开发者私有的笔记和中间文档,不对外发布。 |

依赖与构建产物(`.venv/`、`node_modules/`、`target/`、`dist/`、`build/` 等)同样被忽略,覆盖 Python、Node/TypeScript、Rust、Go、Java/Kotlin、C/C++、Swift、C#/VB.NET/.NET、Visual Studio、Android、Flutter/Dart、CUDA、ActionScript、Julia、Ada、Fortran、Haskell、Lua、OCaml、Perl、Qt、R、Ruby、Delphi。

## 规则

1. **真实配置和密钥绝不进 git**,只有模板(`config-ops-template/*.example`)进。不要把根目录 `.env` 提交。
2. **运行时数据绝不进 git**。没被忽略的话,切分支/切 tag 可能删掉或覆盖数据,大文件也会撑爆仓库。
3. **绝不能忽略** `config-ops-template/`、`data-ops/`、`deploy/`、`tests/`、`manual-tests/`、`third-party/`、`reference-data/`,工具依赖它们。
4. 被忽略的目录 `git clone` 后并不存在,`deploy.sh` 里要 `mkdir -p`。
5. `deploy/` 下脚本:`#!/usr/bin/env bash`、`set -euo pipefail`、带可执行位、幂等、不输出密钥、改完先 `bash -n`。
6. 已经提交了数据文件或密钥?`git rm -r --cached <路径>`;密钥推送过就视为泄露,必须更换。
7. **先定义测试。** 在 `tests/` 里保持一条能跑全部测试的命令;CI 和每位贡献者在结束前运行它,全绿才算完成。

## .gitignore

`init_project.py` 按段管理:重复运行只追加缺少的行。锁文件(`package-lock.json`、`Cargo.lock`、`go.sum` 等)**不会**被忽略。
