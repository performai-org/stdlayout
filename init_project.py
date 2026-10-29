#!/usr/bin/env python3
"""stdlayout: complete a project's standard directories, .gitignore and structure docs.

Standard library only. Safe to re-run: never overwrites files, only appends missing .gitignore lines.

    python3 init_project.py                     # copy into project root and run
    python3 init_project.py /path/to/project    # target another directory
    python3 init_project.py --data cache models # extra data dirs (ignored + created)
    python3 init_project.py --lang python go    # limit language ignores (default: all)
    python3 init_project.py --gitignore-only    # only the .gitignore block; no directories, no other files
    python3 init_project.py --git-init          # not a git repo yet? run git init first, then do everything
    python3 init_project.py --undo              # remove what it generated, but only what you have not changed
    python3 init_project.py --dry-run           # show what it would do, change nothing
    python3 init_project.py --version           # print the version

Without --git-init, a directory that is not a git repository is left untouched (you may have
copied the script to the wrong place).

What it does and why:
    https://github.com/performai-org/stdlayout/blob/main/docs/PROJECT_STRUCTURE.md
    https://github.com/performai-org/stdlayout/blob/main/docs/PROJECT_STRUCTURE.zh-CN.md  (中文)
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

__version__ = "1.0.0"
PUBLIC_REPO = "https://github.com/performai-org/stdlayout"
FILE_ABOUT = "STDLAYOUT.md"
FILE_EN, FILE_ZH = "PROJECT_STRUCTURE.md", "PROJECT_STRUCTURE.zh-CN.md"

# Directories filled at runtime: created and ignored as a whole (their content never enters git).
# 运行时产生的目录:创建 + 整个忽略(内容绝不进 git)。
RUNTIME_DIRS = ["data", "db", "upload", "logs", "tmp"]
# Developer-only directories (scratch notes, intermediate docs): created and ignored,
# but not created by deploy.sh because production does not need them.
# 开发者私有目录(草稿、中间文档):创建并忽略;生产环境用不到,所以 deploy.sh 不建。
PRIVATE_DIRS = ["private-docs"]
# Must never be ignored, or deploy / backup / config-collecting tools cannot read them.
# 绝不能被忽略的,否则部署/备份/配置汇集工具读不到。
MUST_TRACK = ["config-ops-template/", "data-ops/", "deploy/", "tests/", "manual-tests/", "third-party/", "reference-data/"]

# Everything the script writes into .gitignore lives between these two marker lines; the user's own
# rules go outside them and are never touched.
# 脚本写进 .gitignore 的所有内容都在下面这两行标记之间;用户自己的规则写在标记之外,脚本不会碰。
GI_BEGIN = "# >>> BEGIN stdlayout"
GI_END = "# <<< END stdlayout"
GI_BEGIN_LINES = [
    GI_BEGIN + ": the rules between BEGIN and END are maintained by init_project.py. Put your own rules outside this block.",
    "# 本块(BEGIN 到 END 之间)的规则由 init_project.py 维护;你自己的规则请写在本块之外。",
    f"# Why these rules / 为什么这样忽略: {PUBLIC_REPO}/blob/main/docs/PROJECT_STRUCTURE.md",
]
THIRD_PARTY_TITLE = "third-party (committed prebuilt libraries and tools)"
REFERENCE_DATA_TITLE = "reference-data (committed static data)"
# These two sections un-ignore directories, so they must stay the last sections inside the block.
# 这两段是"放行"规则,在块内必须始终排在最后。
LAST_TITLES = [THIRD_PARTY_TITLE, REFERENCE_DATA_TITLE]


def keep_all(d):
    """Un-ignore everything under d/, but still ignore editor junk and secrets inside it.
    d/ 下一律不忽略,但里面的编辑器垃圾文件和密钥仍然忽略。"""
    junk = [".DS_Store", "Thumbs.db", "Desktop.ini", "*.swp", "*.swo", "*~",
            ".env", ".env.*", "id_rsa", "id_ed25519"]
    return [f"!{d}/", f"!{d}/**"] + [f"{d}/**/{x}" for x in junk]


# (title, entries). Appended section by section; entries already present are not repeated.
# (标题, 条目)。按段追加:某段已有的条目不重复写。
GITIGNORE_SECTIONS = [
    ("secrets & real config", [
        "config-ops/", ".env", ".env.*", "!.env.example", "*.pem", "*.p12", "*.pfx",
        "id_rsa", "id_ed25519", "*.keystore", "*.jks",
    ]),
    ("runtime data (see PROJECT_STRUCTURE.md)", [d + "/" for d in RUNTIME_DIRS] + [
        "*.log", "*.sqlite", "*.sqlite3", "*.db", "*.db-journal", "*.rdb", "*.pid",
    ]),
    ("private docs (not committed)", [d + "/" for d in PRIVATE_DIRS]),
    ("OS / editor", [
        ".DS_Store", "Thumbs.db", "Desktop.ini", "*.swp", "*.swo", "*~",
        ".idea/", "*.iml", ".vscode/", ".history/",
    ]),
    ("python", [
        "__pycache__/", "*.py[cod]", "*$py.class", ".venv/", "venv/", "env/",
        "*.egg-info/", ".eggs/", "build/", "dist/", "wheels/", ".pytest_cache/",
        ".mypy_cache/", ".ruff_cache/", ".tox/", ".nox/", ".coverage", "htmlcov/",
        ".ipynb_checkpoints/",
    ]),
    ("node / typescript / javascript", [
        "node_modules/", "dist/", "build/", "out/", "*.tsbuildinfo", ".next/", ".nuxt/",
        ".turbo/", ".parcel-cache/", ".eslintcache", ".pnpm-store/", "coverage/",
        "npm-debug.log*", "yarn-debug.log*", "yarn-error.log*", "pnpm-debug.log*",
    ]),
    ("rust", ["target/", "**/*.rs.bk"]),
    ("go", ["*.exe", "*.exe~", "*.dll", "*.so", "*.dylib", "*.test", "*.out", "go.work", "go.work.sum"]),
    ("java / kotlin", [
        "*.class", "*.jar", "*.war", "*.ear", "!gradle/wrapper/gradle-wrapper.jar",
        "target/", "build/", "out/", ".gradle/", "hs_err_pid*", "replay_pid*",
    ]),
    ("c / c++", [
        "*.o", "*.obj", "*.a", "*.lib", "*.so", "*.dylib", "*.dll", "*.exe", "*.out",
        "*.gch", "*.pch", "*.dSYM/", "CMakeCache.txt", "CMakeFiles/", "cmake-build-*/",
        "compile_commands.json",
    ]),
    ("swift / xcode", [
        ".build/", ".swiftpm/", "DerivedData/", "xcuserdata/", "*.xcuserstate", "Pods/",
        "*.ipa", "*.dSYM.zip",
    ]),
    ("dotnet / c# / vb.net / f#", [
        "[Oo]bj/", "*.nupkg", "*.snupkg", "*.pdb", "*.dll", "*.exe",
        "project.lock.json", "artifacts/", "TestResults/", "BenchmarkDotNet.Artifacts/",
        "*.user", "*.suo", "*.cache", "*.mdb",
    ]),
    ("visual studio", [
        ".vs/", "*.userosscache", "*.sln.docstates", "*.ncb", "*.sdf", "*.opensdf",
        "*.VC.db", "*.VC.VC.opendb", "ipch/", "[Dd]ebug/", "[Rr]elease/", "x64/", "x86/",
        "*.ilk", "*.idb", "*.tlog", "*.pidb", "_ReSharper*/", "*.DotSettings.user",
        "*.psess", "*.vsp", "*.vspx",
    ]),
    ("android", [
        ".gradle/", "build/", "local.properties", "captures/", ".externalNativeBuild/",
        ".cxx/", "*.apk", "*.aab", "*.ap_", "*.dex", "*.keystore", "*.jks",
        "!gradle/wrapper/gradle-wrapper.jar",
    ]),
    ("flutter / dart", [
        ".dart_tool/", ".packages", ".pub-cache/", ".pub/", "build/", ".flutter-plugins",
        ".flutter-plugins-dependencies", ".fvm/", "*.g.dart.tmp", "**/Flutter/ephemeral/",
        "**/Pods/", "**/ios/Flutter/Generated.xcconfig", "**/android/key.properties",
        "**/android/local.properties", "coverage/", "*.ipa", "*.apk", "*.aab",
    ]),
    ("cuda", [
        "*.o", "*.obj", "*.a", "*.lib", "*.so", "*.dll", "*.exe", "*.out",
        "*.cubin", "*.fatbin", "*.ptx", "*.gpu", "*.ii", "*.cudafe1.*", "*.fatbin.c",
        "*.module_id", "*.nsys-rep", "*.ncu-rep", "*.qdrep",
    ]),
    ("actionscript / flex", [
        "*.swf", "bin-debug/", "bin-release/", ".metadata/", "*.swc.tmp",
        "*.fla.bak", ".flexProperties.local",
    ]),
    ("julia", [
        "*.jl.cov", "*.jl.*.cov", "*.jl.mem", "deps/deps.jl", "docs/build/", "docs/site/",
        ".CondaPkg/",
    ]),
    ("ada", [
        "*.ali", "*.o", "*.obj", "*.a", "*.so", "*.exe", "b~*.ad[sb]", "b__*.ad[sb]",
        "obj/", "alire/", "*.stderr", "*.stdout", "gnatinspect.db",
    ]),
    ("fortran", [
        "*.mod", "*.smod", "*.o", "*.obj", "*.a", "*.lib", "*.so", "*.dylib", "*.dll",
        "*.exe", "*.out",
    ]),
    ("haskell", [
        "dist/", "dist-newstyle/", ".stack-work/", ".cabal-sandbox/", "cabal.sandbox.config",
        "cabal.project.local", "cabal.project.local~", ".ghc.environment.*", "*.hi", "*.o",
        "*.dyn_hi", "*.dyn_o", "*.chi", "*.chs.h", "*.prof", "*.aux", "*.hp", "*.eventlog",
        ".HTF/",
    ]),
    ("lua", [
        "luac.out", "*.luac", "*.src.rock", "lua_modules/", ".luarocks/", "*.o", "*.so",
        "*.dll", "*.a",
    ]),
    ("ocaml", [
        "_build/", "_opam/", "_esy/", "*.cmo", "*.cmi", "*.cmx", "*.cmxa", "*.cma", "*.cmxs",
        "*.cmt", "*.cmti", "*.annot", "*.install", "*.native", "*.byte", ".merlin",
        "*.o", "*.a", "*.so",
    ]),
    ("perl", [
        "blib/", "_build/", "Build", "Build.bat", "MYMETA.*", "pm_to_blib", "Makefile.old",
        "*.o", "*.bs", "cover_db/", "nytprof.out",
    ]),
    ("qt / qmake / cmake", [
        "*.pro.user", "*.pro.user.*", "*.qbs.user", "*.qbs.user.*", "CMakeLists.txt.user*",
        "*.autosave", ".qmake.stash", ".qmake.cache", "moc_*.cpp", "moc_*.h", "qrc_*.cpp",
        "ui_*.h", "*.moc", "object_script.*", "*.qmlc", "*.jsc", "build-*/", "*-build-*/",
        "*.qm", "*_plugin_import.cpp",
    ]),
    ("r", [
        ".Rhistory", ".Rapp.history", ".RData", ".RDataTmp", ".Ruserdata", ".Rproj.user/",
        "*.Rcheck/", "*_cache/", "*_files/", ".httr-oauth", "rsconnect/", "renv/library/",
        "renv/local/", "renv/staging/", "renv/cellar/", "*.knit.md", "*.utf8.md",
    ]),
    ("ruby", [
        "*.gem", "*.rbc", ".bundle/", "vendor/bundle/", ".yardoc/", "_yardoc/", "rdoc/",
        "pkg/", "coverage/", ".byebug_history", ".rspec_status", "*.rbo",
    ]),
    ("delphi / pascal", [
        "*.dcu", "*.bpl", "*.bpi", "*.dcp", "*.drc", "*.dres", "*.rsm", "*.tds",
        "*.exe", "*.dll", "*.so", "*.o", "*.ppu", "*.a", "*.lib", "*.identcache",
        "*.projdata", "*.tvsconfig", "*.dsk", "__history/", "__recovery/", "*.~*",
        "Win32/", "Win64/",
    ]),
    # These MUST stay the last sections: a later rule wins, so the negations override the build-output
    # rules above (*.exe, *.dll, *.db, build/, ...) for committed prebuilt libraries and static data.
    # 这些必须是最后几段:后面的规则优先,"!"用来覆盖上面的构建产物规则(*.exe、*.dll、*.db、build/ 等),
    # 让已编译的第三方库和静态参考数据能提交。
    (THIRD_PARTY_TITLE, keep_all("third-party")),
    (REFERENCE_DATA_TITLE, keep_all("reference-data")),
]
_DOTNET = "dotnet / c# / vb.net / f#"
# Several --lang names may share one section (e.g. csharp and vb both map to dotnet).
# 多个 --lang 名字可以对应同一段(如 csharp 和 vb 都对应 dotnet)。
LANG_SECTION = {"python": "python", "node": "node / typescript / javascript",
                "typescript": "node / typescript / javascript", "rust": "rust", "go": "go",
                "java": "java / kotlin", "kotlin": "java / kotlin", "c": "c / c++",
                "cpp": "c / c++", "swift": "swift / xcode",
                "csharp": _DOTNET, "vb": _DOTNET, "fsharp": _DOTNET, "dotnet": _DOTNET,
                "visualstudio": "visual studio", "android": "android",
                "flutter": "flutter / dart", "dart": "flutter / dart", "cuda": "cuda",
                "actionscript": "actionscript / flex", "julia": "julia", "ada": "ada",
                "fortran": "fortran", "haskell": "haskell", "lua": "lua", "ocaml": "ocaml",
                "perl": "perl", "qt": "qt / qmake / cmake", "r": "r", "ruby": "ruby",
                "delphi": "delphi / pascal", "pascal": "delphi / pascal"}
# Sections written regardless of --lang. / 不受 --lang 限制、总会写入的段。
ALWAYS_SECTIONS = {"secrets & real config", "runtime data (see PROJECT_STRUCTURE.md)",
                   "private docs (not committed)", "OS / editor",
                   THIRD_PARTY_TITLE, REFERENCE_DATA_TITLE}


DEPLOY_SH = """#!/usr/bin/env bash
# 切到新 release 后执行;配置变化时也可能重跑,必须幂等。
# Runs after switching to a new release; may re-run, so keep it idempotent.
# 不要输出配置或密钥 / never print config or secrets.
set -euo pipefail
cd "$(dirname "$0")/.."

# 运行时目录被 .gitignore 忽略,clone 下来不存在,这里补建
# runtime dirs are gitignored and absent after clone
mkdir -p %(dirs)s

# 例 / examples:
# python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt
# sudo systemctl restart <service>
"""

HEALTHCHECK_SH = """#!/usr/bin/env bash
# 部署后探测:退出码 0 = 健康,非 0 = 失败。要有超时。
# Post-deploy probe: exit 0 = healthy, non-zero = failed. Always use a timeout.
set -euo pipefail

# 例 / example:
# curl -fsS --max-time 10 http://127.0.0.1:8080/health >/dev/null
"""

CONFIG_README = """# config-ops-template

配置**模板**(占位值,文件名带 `.example`),可以提交、可以开源。**不要写真实密钥。**
Config **templates** (placeholder values, files end in `.example`). Safe to commit/open-source. **No real secrets.**

- 真实配置放私有仓库,部署时复制到本项目的 `config-ops/`(已 .gitignore);程序只读 `config-ops/`。
  Real config lives in a private repo and is copied into `config-ops/` (gitignored); the program reads only `config-ops/`.
- 例 / e.g.: `app.json.example` -> real file `app.json`.
"""

THIRD_PARTY_README = """# third-party

Ready-made libraries and programs that were NOT built from this repository's source, but are
committed on purpose (prebuilt binaries, vendored libraries, installers, SDK snapshots).
**Committed. Everything in here is un-ignored**, including `*.exe`, `*.dll`, `*.jar`, `build/`.
不是由本仓库源码生成、但**特意提交**的现成库和程序(预编译二进制、vendored 库、安装包、SDK 快照)。
**提交到 git;这里的一切都不被忽略**,包括 `*.exe`、`*.dll`、`*.jar`、`build/`。

- One subdirectory per item, and record where it came from in `third-party/MANIFEST.md`:
  name, version, source URL, license, sha256 of the file.
  每个条目一个子目录,并在 `third-party/MANIFEST.md` 记录:名称、版本、来源 URL、许可证、文件 sha256。
- Prefer a package manager and its lock file (`package-lock.json`, `Cargo.lock`, ...) when one exists;
  use this directory only for things that cannot be fetched that way.
  有包管理器和锁文件时优先用它们;只有拿不到的东西才放这里。
- Keep files small. Very large binaries: use Git LFS (`git lfs track "third-party/**/*.bin"`).
  文件要小;特别大的二进制用 Git LFS。
- Check the license allows redistribution. Never put secrets here (`.env*` and `id_rsa` stay ignored).
  确认许可证允许再分发。不要放密钥(`.env*`、`id_rsa` 仍然被忽略)。
"""

REFERENCE_DATA_README = """# reference-data

Static, non-secret data that ships with the code and is the same in every environment, e.g. the
lookup table from the first 6 digits of a Chinese ID number to province / city / county, country and
currency codes, dictionaries. **Committed. Everything in here is un-ignored**, including `*.db`, `*.sqlite`.
随代码发布、所有环境都一样、不含敏感信息的静态数据,例如身份证前 6 位对应的省市县、国家/币种代码、字典表。
**提交到 git;这里的一切都不被忽略**,包括 `*.db`、`*.sqlite`。

- NOT for data produced at runtime (that is `data/`, gitignored), NOT for per-environment settings
  (that is `config-ops/`), NEVER for secrets or personal data.
  不放运行时产生的数据(那是被忽略的 `data/`),不放各环境不同的配置(`config-ops/`),绝不放密钥或个人信息。
- Prefer plain, diff-friendly formats (csv / json / yaml / tsv) over binaries.
  优先用纯文本、方便 diff 的格式(csv / json / yaml / tsv)。
- Record where each file came from in `reference-data/MANIFEST.md`: source URL, version or date, license, sha256.
  在 `reference-data/MANIFEST.md` 记录每个文件的来源 URL、版本或日期、许可证、sha256。
- Update by replacing the file in a commit that says why; keep the generating script in the repo if there is one.
  更新就在一次说明原因的提交里替换文件;如果有生成脚本,也放进仓库。
- Very large files: use Git LFS (`git lfs track "reference-data/**/*.bin"`).
  特别大的文件用 Git LFS。
"""

MANUAL_TESTS_README = """# manual-tests

Test steps that a person runs by hand (checklists, one-off scripts, things automation cannot cover).
**Committed; never gitignored.**
需要人手工执行的测试步骤(检查清单、一次性脚本、自动化覆盖不了的内容)。**提交到 git,绝不忽略。**

Automated tests live in `tests/`. Nothing here may be picked up by an automatic test runner, so:
自动化测试在 `tests/`。这里的东西不能被任何自动测试运行器收集,所以:

- Write checklists as `.md` and helper scripts as `.sh`. No test-framework code files.
  检查清单写成 `.md`,辅助脚本写成 `.sh`,不要放测试框架的代码文件。
- **Name every file `check-<topic>.md` or `check-<topic>.sh`** (for example `check-install.md`, `check-backup.sh`),
  so that automatic test frameworks never collect and run them. Do not put `test` or `spec` in the name.
  Why, and what each framework collects: [FILE-NAMING.md](FILE-NAMING.md).
  **所有文件都命名为 `check-<主题>.md` 或 `check-<主题>.sh`**(例如 `check-install.md`、`check-backup.sh`),
  这样自动化测试框架不会收集和执行它们。名字里不要出现 `test` 和 `spec`。原因和各框架的收集规则见 [FILE-NAMING.md](FILE-NAMING.md)。
- Write down: what to do, what you expect to see, and the date, version and environment of the last run.
  记录:怎么做、期望看到什么,以及上次执行的日期、版本和环境。
- Scratch output of a manual run goes to `tmp/` (gitignored), not here.
  手工运行产生的临时输出放 `tmp/`(被忽略),不要放这里。
"""

MANUAL_NAMING_MD = """# File names that keep test runners away / 避免被自动测试收集的文件名

Everything in `manual-tests/` is run by a person. If an automatic test runner (locally or in CI) collects
a file from here, a "manual" step will suddenly run, fail or hang the build. Runners decide by **file name**
(and sometimes directory name), so choose names carefully.
`manual-tests/` 里的东西由人来执行。如果自动测试运行器(本地或 CI)把这里的文件收集进去,手工步骤就会突然被执行、失败或卡住构建。
运行器靠**文件名**(有时也靠目录名)判断,所以起名要小心。

## The simple rule / 最简单的规则

1. Name files `check-<topic>.md` / `check-<topic>.sh`; only `.md` and `.sh`. / 文件命名为 `check-<主题>.md` / `check-<主题>.sh`;只放 `.md` 和 `.sh`。
2. The file name must not contain `test` or `spec` (any case). / 文件名里不要出现 `test` 或 `spec`(不分大小写)。
3. No sub-directories named `test`, `tests`, `spec`, `__tests__`, `t`, `testdata`. / 不要建名为 `test`、`tests`、`spec`、`__tests__`、`t`、`testdata` 的子目录。
4. Never add `__init__.py`, `conftest.py`, `main.rs`, `*.csproj`, `*.sln`, `CMakeLists.txt`, `*.t`, `*.bats`. / 不要放这些文件。

## Suggested names / 建议的文件名

Use the prefix **`check-`** for everything here. It is a plain word that no test runner matches.
这里所有文件都用 **`check-`** 前缀。它是普通单词,没有任何测试运行器会匹配它。

| Purpose / 用途 | File name / 文件名 |
|---|---|
| Steps a person follows and what to expect / 人照着做的步骤和期望结果 | `check-install.md`, `check-upgrade.md`, `check-release.md` |
| A helper script a person runs / 人来运行的辅助脚本 | `check-environment.sh`, `check-backup-restore.sh` |
| Notes on a run / 某次执行的记录 | `check-install-2025-01-15.md` |

Pattern / 模式: `check-<topic>.md` and `check-<topic>.sh`.

## What each runner collects (defaults) / 各运行器默认会收集什么

These are the usual defaults; your project's own configuration can change them, so check it too.
这些是常见的默认规则;项目自己的配置可能改变它们,也要看一下。

| Ecosystem / runner | Collects / 会收集 | So avoid / 所以避开 |
|---|---|---|
| Python `unittest` | `test*.py` inside packages (dirs with `__init__.py`) | `test*.py`, `__init__.py` |
| Python `pytest` | `test_*.py`, `*_test.py`; loads `conftest.py` | `test_*.py`, `*_test.py`, `conftest.py` |
| Node `jest` | `*.test.js/ts/jsx/tsx`, `*.spec.*`, anything in `__tests__/` | `*.test.*`, `*.spec.*`, `__tests__/` |
| Node `vitest` | `*.test.*`, `*.spec.*` (js, mjs, cjs, ts, jsx, tsx) | same |
| Node `mocha` | `./test/*.js` | a `test/` directory |
| Node `node --test` | `*.test.js`, `test-*.js`, `*-test.js`, `*_test.js`, files in `test/` | those names, `test/` |
| Go `go test ./...` | `*_test.go` in any directory (skips dirs starting with `_` or `.`, and `testdata`) | `*_test.go`, any `.go` file |
| Rust `cargo test` | `tests/*.rs`, `tests/<dir>/main.rs`, `#[test]` in `src/` | `.rs` files, `main.rs` |
| Java / Kotlin (Maven, Gradle) | `Test*.java`, `*Test.java`, `*Tests.java`, `*TestCase.java` under `src/test` | those names, `.java` / `.kt` files |
| C# / .NET `dotnet test` | test projects (`*.csproj` / `*.sln` with a test SDK; `[Fact]`, `[Test]`) | `.csproj`, `.sln`, `.cs` files |
| Ruby `rspec` | `spec/**/*_spec.rb` | `*_spec.rb`, a `spec/` directory |
| Ruby minitest / rake | `test/**/test_*.rb`, `*_test.rb` | those names, a `test/` directory |
| PHP `phpunit` | `*Test.php` in directories named in `phpunit.xml` | `*Test.php` |
| C / C++ (CTest, GoogleTest) | whatever `add_test(...)` in `CMakeLists.txt` registers | `CMakeLists.txt`, `.c` / `.cpp` files |
| Swift `swift test` | `Tests/` directory, `*Tests.swift` | `Tests/`, `.swift` files |
| Perl `prove` | `t/*.t` | `*.t`, a `t/` directory |
| R (`testthat`, `R CMD check`) | `tests/testthat/test-*.R`, `tests/*.R` | `.R` files |
| Elixir `mix test` | `test/**/*_test.exs` | `*_test.exs` |
| Dart / Flutter `flutter test` | `test/**/*_test.dart` | `*_test.dart`, `.dart` files |
| Julia `Pkg.test()` | `test/runtests.jl` | `runtests.jl` |
| Lua `busted` | `*_spec.lua` | `*_spec.lua` |
| Shell `bats` | `*.bats` | `*.bats` |
| Anything in CI | broad globs such as `**/*test*` | no "test" / "spec" in names |
"""

TESTS_README = """# tests

Test cases for this project. **Committed; never gitignored.**
本项目的测试用例。**提交到 git,绝不忽略。**

- One command must run ALL tests and exit non-zero on any failure. Write that command here, e.g.
  `python3 -m unittest discover -s tests` / `python3 -m pytest` / `npm test` / `go test ./...` / `cargo test`.
  一条命令跑完所有测试,任何失败都要返回非 0。把这条命令写在这里。
- CI and every contributor run it before finishing a task: all green = done; any red = not done.
  CI 和每位贡献者在结束任务前运行它:全绿才算完成。
- New behavior gets a test; a bug fix starts with a test that fails. Define the cases first, then write the code against them.
  新行为要有测试,修 bug 先写一个会失败的测试。先定义用例,再照着写代码。
- Keep fixtures small under `tests/fixtures/`; no real secrets or production data.
  测试数据放 `tests/fixtures/`,要小;不要放真实密钥或生产数据。

Test command / 测试命令:

    TODO: replace this line
"""

SOURCES_YAML = """# 数据在哪(不机密,提交)。备份工具据此工作;没有需要备份的数据保留空列表。
# Where the data lives (not secret, committed). Backup tools read this. Keep empty if none.
data: []
# 例 / examples:
# data:
#   - {type: dir,      path: data/}
#   - {type: dir,      path: upload/}
#   - {type: sqlite,   path: db/app.sqlite3}
#   - {type: postgres, name: mydb}
"""

ABOUT_MD = """\
# About the standard layout / 关于标准目录结构

This project was completed by [stdlayout](%(repo)s)'s `init_project.py`.
本项目的目录结构和 `.gitignore` 由 [stdlayout](%(repo)s) 的 `init_project.py` 补全。

## English

`init_project.py` is a single, dependency-free Python script. Run `python3 init_project.py` in a project root and it:

- creates the standard directories `data/ db/ upload/ logs/ tmp/` (runtime data, gitignored), `private-docs/` (private notes, gitignored), `deploy/`, `config-ops-template/`, `data-ops/`, `tests/`, `manual-tests/`, `third-party/`, `reference-data/` (committed);
- makes sure `.gitignore` covers real config and secrets (`config-ops/`, `.env*`), runtime data, and build output of Python, Node/TypeScript, Rust, Go, Java/Kotlin, C/C++, Swift, C#/VB.NET/.NET, Visual Studio, Android, Flutter/Dart, CUDA, ActionScript, Julia, Ada, Fortran, Haskell, Lua, OCaml, Perl, Qt, R, Ruby and Delphi;
- never overwrites existing files; re-running only fills in what is missing;
- does nothing in a directory that is not a git repository, unless `--git-init` is given (it then runs `git init -b main` first).

Read what the layout is and why:
- [Standard project structure (English)](%(repo)s/blob/main/docs/PROJECT_STRUCTURE.md)
- [项目标准目录结构(中文)](%(repo)s/blob/main/docs/PROJECT_STRUCTURE.zh-CN.md)

## 中文

`init_project.py` 是一个无依赖的 Python 脚本。在项目根目录运行 `python3 init_project.py`,它会:

- 创建标准目录:`data/ db/ upload/ logs/ tmp/`(运行时数据,不提交)、`private-docs/`(私有笔记,不提交)、`deploy/`、`config-ops-template/`、`data-ops/`、`tests/`、`manual-tests/`、`third-party/`、`reference-data/`(提交);
- 确保 `.gitignore` 覆盖真实配置与密钥(`config-ops/`、`.env*`)、运行时数据,以及 Python、Node/TypeScript、Rust、Go、Java/Kotlin、C/C++、Swift、C#/VB.NET/.NET、Visual Studio、Android、Flutter/Dart、CUDA、ActionScript、Julia、Ada、Fortran、Haskell、Lua、OCaml、Perl、Qt、R、Ruby、Delphi 的构建产物;
- 绝不覆盖已有文件,重复运行只补缺少的;
- 目录不是 git 仓库时什么都不做,除非加 `--git-init`(此时先执行 `git init -b main`)。

目录是什么、为什么这样:
- [项目标准目录结构(中文)](%(repo)s/blob/main/docs/PROJECT_STRUCTURE.zh-CN.md)
- [Standard project structure (English)](%(repo)s/blob/main/docs/PROJECT_STRUCTURE.md)
- [Git 与 GitHub 使用指南](%(repo)s/blob/main/docs/GIT_GITHUB.zh-CN.md) · [Git & GitHub guide](%(repo)s/blob/main/docs/GIT_GITHUB.md)
"""

DOC_TREE = """\
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
"""

DOC_EN = """\
# Standard Project Structure

> Generated by [stdlayout](%(repo)s). The latest version of this document:
> [English](%(repo)s/blob/main/docs/PROJECT_STRUCTURE.md) · [中文](%(repo)s/blob/main/docs/PROJECT_STRUCTURE.zh-CN.md)
>
> Chinese version of this file: [PROJECT_STRUCTURE.zh-CN.md](PROJECT_STRUCTURE.zh-CN.md)

Run `python3 init_project.py` in the project root at any time: it creates what is missing and never overwrites anything.

## Layout

```
%(tree)s```

| Path | Committed? | Purpose |
|---|---|---|
| `deploy/` | yes | `deploy.sh` (install deps, migrate, restart; must be idempotent), `healthcheck.sh` (exit 0 = healthy), service units. All optional. |
| `config-ops-template/` | yes | Templates of every config file the program needs, with placeholder values. Safe to open-source. |
| `config-ops/` | **no** | Real config and secrets. The program reads config **only** from here. Keep dir `700`, files `600`. |
| `data-ops/` | yes | `sources.yaml` declares where data lives (db, directories) so backup tools can find it. |
| `reference-data/` | yes | Static, non-secret data that is the same in every environment (code tables, lookup tables, dictionaries). Everything inside is un-ignored, `*.db`/`*.sqlite` included. Not for runtime data (`data/`) or per-environment settings (`config-ops/`). |
| `tests/` | yes | Test cases. One command runs them all; CI and every contributor run it before finishing a task. |
| `manual-tests/` | yes | Checklists and scripts for tests a person runs by hand. Only `.md` / `.sh` files, named so no test runner picks them up. |
| `third-party/` | yes | Ready-made libraries and programs not built from this repo (prebuilt binaries, vendored libs). Everything inside is un-ignored, `*.exe`/`*.dll`/`build/` included. Record source, version, license, sha256 in `MANIFEST.md`. |
| `data/` | **no** | Data files produced at runtime. |
| `db/` | **no** | Database files (sqlite etc.). |
| `upload/` | **no** | Files uploaded by users. |
| `logs/` | **no** | Log files. |
| `tmp/` | **no** | Scratch files and caches. |
| `private-docs/` | **no** | Developer-only notes and intermediate documents that should not be published. |

Dependencies and build output (`.venv/`, `node_modules/`, `target/`, `dist/`, `build/`, ...) are gitignored too, for Python, Node/TypeScript, Rust, Go, Java/Kotlin, C/C++, Swift, C#/VB.NET/.NET, Visual Studio, Android, Flutter/Dart, CUDA, ActionScript, Julia, Ada, Fortran, Haskell, Lua, OCaml, Perl, Qt, R, Ruby and Delphi.

## Rules

1. **Real config and secrets never enter git.** Only templates (`config-ops-template/*.example`) do. Do not commit a root `.env`.
2. **Runtime data never enters git.** If it is not ignored, switching branches/tags can delete or overwrite it, and big files bloat the repo.
3. **Never ignore** `config-ops-template/`, `data-ops/`, `deploy/`, `tests/`, `manual-tests/`, `third-party/`, `reference-data/`: tooling depends on them.
4. Ignored directories do not exist after `git clone`; `deploy.sh` must `mkdir -p` them.
5. Scripts in `deploy/`: `#!/usr/bin/env bash`, `set -euo pipefail`, executable bit, idempotent, never print secrets, run `bash -n` after editing.
6. Already committed a data file or secret? `git rm -r --cached <path>`, and rotate the secret if it was ever pushed.
7. **Define tests first.** Keep one command that runs every test in `tests/`; CI and every contributor run it before finishing, and only all-green counts as done.

## .gitignore

Managed in marked sections by `init_project.py`: re-running only appends lines that are missing. Lock files (`package-lock.json`, `Cargo.lock`, `go.sum`, ...) are deliberately **not** ignored.
"""

DOC_ZH = """\
# 项目标准目录结构

> 由 [stdlayout](%(repo)s) 生成。本文最新版:
> [English](%(repo)s/blob/main/docs/PROJECT_STRUCTURE.md) · [中文](%(repo)s/blob/main/docs/PROJECT_STRUCTURE.zh-CN.md)
>
> 英文版:[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)

在项目根目录随时运行 `python3 init_project.py`:只补全缺少的东西,绝不覆盖已有文件。

## 目录一览

```
%(tree)s```

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
"""


class Scaffold:
    """Does the actual work under one project root; with dry=True it only prints.
    在一个项目根目录下做实际工作;dry=True 时只打印、不写盘。"""

    def __init__(self, root, dry):
        self.root, self.dry = root, dry

    def say(self, tag, rel):
        # One aligned status line per action. / 每个动作打印一行对齐的状态。
        print(f"  {tag:8} {rel}")

    def mkdir(self, rel):
        # Create a directory if missing; an existing one is left alone.
        # 目录不存在才创建,已存在就不动。
        p = self.root / rel
        if p.is_dir():
            return self.say("exists", rel + "/")
        self.say("create", rel + "/")
        if not self.dry:
            p.mkdir(parents=True, exist_ok=True)

    def write(self, rel, text, exe=False):
        # Write a new file; NEVER overwrite an existing one (the core guarantee).
        # 只写新文件,绝不覆盖已有文件(核心保证)。
        p = self.root / rel
        if p.exists():
            return self.say("exists", rel)
        self.say("create", rel)
        if self.dry:
            return
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        if exe:
            p.chmod(0o755)

    def gitignore(self, sections, extra_dirs, skip_existing=False):
        # All our changes live in ONE block between GI_BEGIN and GI_END. Lines outside the block are the
        # user's: never read as ours, never modified, never reordered. Inside the block we only add
        # missing entries (new sections go before the un-ignore sections so those stay last).
        # 我们的全部改动都在 GI_BEGIN 与 GI_END 之间的同一个块里。块外是用户的行:不改、不动、不重排。
        # 块内只补缺少的条目(新增的段插在"放行"段之前,保证放行段始终在最后)。
        p = self.root / ".gitignore"
        old = p.read_text(encoding="utf-8") if p.exists() else ""
        lines = old.splitlines()
        sections = sections + ([("extra data dirs", [d + "/" for d in extra_dirs])] if extra_dirs else [])

        # 1) Split the file into: before / inside / after our block. / 把文件拆成:块前 / 块内 / 块后。
        begin = [i for i, ln in enumerate(lines) if ln.startswith(GI_BEGIN)]
        end = [i for i, ln in enumerate(lines) if ln.startswith(GI_END)]
        if len(begin) > 1 or len(end) > 1 or len(begin) != len(end) or (begin and end[0] < begin[0]):
            sys.exit(f"{p} has a broken stdlayout block (need exactly one BEGIN line followed by one END line). "
                     "Nothing was changed; fix or delete the block and run again.")
        if begin and skip_existing:
            return self.say("kept", ".gitignore  (stdlayout block already present)")
        if begin:
            before, inner, after = lines[:begin[0]], lines[begin[0] + 1:end[0]], lines[end[0] + 1:]
        else:
            before, inner, after = lines, [], []

        # 2) Parse the block into [title, lines] sections; lines before the first header (our
        #    explanatory comments) are regenerated, so they are dropped here.
        #    把块内解析成 [标题, 行] 的段;第一个标题之前的行(说明注释)每次重新生成,所以这里丢弃。
        parsed = []
        for ln in inner:
            m = re.match(r"# --- (.+) ---$", ln)
            if m:
                parsed.append([m.group(1), []])
            elif parsed and ln.strip():
                parsed[-1][1].append(ln)

        # Trailing blank lines before the block are only our separator; drop them so reruns do not pile up blanks.
        # 块前末尾的空行只是我们加的分隔,去掉,避免重复运行时空行越积越多。
        while before and not before[-1].strip():
            before.pop()

        # 3) Add the missing entries. `have` = user lines outside the block + lines already in the block.
        #    补缺少的条目。have = 块外的用户行 + 块内已有的行。
        have = {ln.strip() for ln in before + after} | {x.strip() for _, ls in parsed for x in ls}
        added = 0
        for title, entries in sections:
            want = []
            for e in entries:
                # "x/" and "x" count as the same rule. / "x/" 和 "x" 视为同一条规则。
                if e in have or e.rstrip("/") in have or e in want:
                    continue
                want.append(e)
            if not want:
                continue
            added += len(want)
            have.update(want)
            sec = next((x for x in parsed if x[0] == title), None)
            if sec:
                sec[1].extend(want)
            else:
                at = next((k for k, x in enumerate(parsed) if x[0] in LAST_TITLES), len(parsed))
                parsed.insert(len(parsed) if title in LAST_TITLES else at, [title, want])
        if not added and begin:
            return self.say("up to date", ".gitignore")
        if not added and not begin and not parsed:
            return self.say("up to date", ".gitignore")  # nothing to add and nothing to write / 没有要加的
        # 4) Render: user lines before, our block, user lines after. / 输出:块前用户行、我们的块、块后用户行。
        block = GI_BEGIN_LINES[:]
        for title, ls in parsed:
            block += ["", f"# --- {title} ---"] + ls
        block += ["", GI_END + " (end of the lines maintained by init_project.py)"]
        text_before = "\n".join(before).rstrip("\n")
        out = ("\n".join(before) + "\n\n" if text_before else "") + "\n".join(block) + "\n"
        if after:
            out += "\n".join(after) + "\n"
        self.say("append" if old else "create", f".gitignore  +{added} lines")
        if self.dry:
            return
        p.write_text(out, encoding="utf-8")

    def undo(self, extra_dirs):
        # Remove what this script generated, but only what the user has not touched:
        #   - a generated file is deleted only if its content equals what the script would generate now;
        #   - a directory is removed only if it is empty (rmdir), so user data is never lost;
        #   - in .gitignore only the BEGIN..END block is removed; the user's own lines stay.
        # .git/ and any other file are never touched.
        # 撤销本脚本生成的内容,但只撤销用户没动过的:
        #   - 生成的文件:内容与脚本现在会生成的完全一致才删;
        #   - 目录:为空才删(rmdir),所以不会丢用户数据;
        #   - .gitignore:只删 BEGIN..END 之间的块,用户自己的行保留。
        # .git/ 和其它任何文件都不碰。
        dirs = RUNTIME_DIRS + extra_dirs
        generated = {
            "deploy/deploy.sh": DEPLOY_SH % {"dirs": " ".join(dirs)},
            "deploy/healthcheck.sh": HEALTHCHECK_SH,
            "config-ops-template/README.md": CONFIG_README,
            "data-ops/sources.yaml": SOURCES_YAML,
            "tests/README.md": TESTS_README,
            "manual-tests/README.md": MANUAL_TESTS_README,
            "manual-tests/FILE-NAMING.md": MANUAL_NAMING_MD,
            "third-party/README.md": THIRD_PARTY_README,
            "reference-data/README.md": REFERENCE_DATA_README,
            FILE_ABOUT: ABOUT_MD % {"repo": PUBLIC_REPO},
            FILE_EN: DOC_EN % {"repo": PUBLIC_REPO, "tree": DOC_TREE},
            FILE_ZH: DOC_ZH % {"repo": PUBLIC_REPO, "tree": DOC_TREE},
        }
        removed_tracked = []
        for rel, text in generated.items():
            p = self.root / rel
            if not p.is_file():
                continue
            if p.read_text(encoding="utf-8") != text:
                self.say("keep", rel + "  (modified by you)")
                continue
            if self.git("ls-files", "--", rel)[1]:
                removed_tracked.append(rel)
            self.say("remove", rel)
            if not self.dry:
                p.unlink()
        # Directories, children first. In dry-run nothing was deleted yet, so "empty" means
        # "empty after the removals above". / 目录:子先父后。dry-run 时文件还没真删,所以"空"指"上面的删除之后为空"。
        planned = {rel for rel in generated if (self.root / rel).is_file() and
                   (self.root / rel).read_text(encoding="utf-8") == generated[rel]}
        dir_list = sorted({str(Path(rel).parent) for rel in generated if "/" in rel}) + dirs + PRIVATE_DIRS
        for d in dir_list:
            p = self.root / d
            if not p.is_dir():
                continue
            left = [x for x in p.iterdir() if not (self.dry and str(x.relative_to(self.root)) in planned)]
            if left:
                self.say("keep", d + "/  (not empty)")
                continue
            self.say("remove", d + "/")
            if not self.dry:
                p.rmdir()
        self.undo_gitignore()
        if removed_tracked:
            print("  ! these removed files are tracked by git; commit the deletion: " + " ".join(removed_tracked))

    def undo_gitignore(self):
        # Remove only the BEGIN..END block from .gitignore. / 只删 .gitignore 里 BEGIN..END 之间的块。
        p = self.root / ".gitignore"
        if not p.is_file():
            return
        lines = p.read_text(encoding="utf-8").splitlines()
        begin = [i for i, ln in enumerate(lines) if ln.startswith(GI_BEGIN)]
        end = [i for i, ln in enumerate(lines) if ln.startswith(GI_END)]
        if not begin and not end:
            return
        if len(begin) != 1 or len(end) != 1 or end[0] < begin[0]:
            self.say("keep", ".gitignore  (broken stdlayout block; fix it by hand)")
            return
        rest = lines[:begin[0]] + lines[end[0] + 1:]
        while begin[0] > 0 and begin[0] <= len(rest) and not rest[begin[0] - 1].strip():
            # drop the blank separator we added before the block / 去掉块前我们加的空行分隔
            del rest[begin[0] - 1]
            begin[0] -= 1
        if not "".join(rest).strip():
            self.say("remove", ".gitignore")
            if not self.dry:
                p.unlink()
            return
        self.say("edit", f".gitignore  (-{end[0] - begin[0] + 1} lines: the stdlayout block)")
        if not self.dry:
            p.write_text("\n".join(rest) + "\n", encoding="utf-8")

    def git(self, *args):
        # Run git in the project; returns (exit code, stdout). 127 = git is not installed.
        # 在项目目录里运行 git,返回 (退出码, 标准输出);127 表示没装 git。
        try:
            r = subprocess.run(["git", "-C", str(self.root), *args], capture_output=True, text=True)
        except FileNotFoundError:
            return 127, ""
        return r.returncode, r.stdout.strip()

    def git_toplevel(self):
        # Top-level directory of the repository containing root, or None if there is none.
        # 包含 root 的 git 仓库的顶层目录;不在任何仓库里则返回 None。
        code, out = self.git("rev-parse", "--show-toplevel")
        return Path(out).resolve() if code == 0 and out else None

    def git_init(self):
        # `git init` with branch main (older git: init, then point HEAD at main). Only called when asked.
        # 以 main 为默认分支执行 git init(旧版 git:先 init 再把 HEAD 指向 main)。仅在用户要求时调用。
        self.say("create", ".git  (git init -b main)")
        if self.dry:
            return
        code, _ = self.git("init", "-q", "-b", "main")
        if code != 0:
            code, _ = self.git("init", "-q")
            if code == 0:
                self.git("symbolic-ref", "HEAD", "refs/heads/main")
        if code != 0:
            sys.exit("git init failed (is git installed?)")

    def verify(self, dirs):
        """Check with git check-ignore: what must be ignored is, what must not be isn't, and nothing ignored is already tracked.
        用 git check-ignore 实测:该忽略的忽略、不该忽略的没被忽略,且被忽略的路径下没有已跟踪的文件。
        Returns the number of failed checks. / 返回失败项的个数。"""
        if self.git("rev-parse", "--git-dir")[0] != 0:
            print("  ! not a git repository; skipped the .gitignore check")
            return 1
        bad = 0
        # 1) These must be ignored. / 这些必须被忽略。
        for d in ["config-ops"] + dirs:
            if self.git("check-ignore", "-q", d + "/x")[0] != 0:
                print(f"  ✗ should be ignored but is not: {d}/"); bad += 1
        # 2) These must NOT be ignored. / 这些绝不能被忽略。
        for d in MUST_TRACK + [".env.example"]:
            probe = d + "x" if d.endswith("/") else d
            if self.git("check-ignore", "-q", probe)[0] == 0:
                print(f"  ✗ must not be ignored but is: {d} (conflicting rule in .gitignore?)"); bad += 1
        # 3) Nothing under an ignored path may already be tracked (leaked data/secrets).
        # 被忽略的路径下不能已有被跟踪的文件(已泄露的数据/密钥)。
        _, tracked = self.git("ls-files", "--", "config-ops", *dirs)
        if tracked:
            print("  ✗ these paths should be ignored but are tracked by git (config-ops/ may hold real secrets):\n    "
                  + tracked.replace("\n", "\n    ")
                  + "\n    fix: git rm -r --cached <path>; if a secret was ever pushed, treat it as leaked and rotate it")
            bad += 1
        if not bad:
            print("  ✓ .gitignore check passed")
        return bad


def is_empty_project(root, me):
    """True if there is no real content (only .git, .gitignore, .DS_Store, this script, STDLAYOUT.md).
    没有任何实际内容(只有 .git、.gitignore、.DS_Store、本脚本、STDLAYOUT.md)。"""
    skip = {".git", ".gitignore", ".DS_Store", me, FILE_ABOUT}
    return not [p for p in root.iterdir() if p.name not in skip]


def main():
    # `__doc__` is None under python -OO, hence the `or ""`. / `python -OO` 下 `__doc__` 是 None,所以加 `or ""`。
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("path", nargs="?", default=None,
                    help="project directory (default: the directory of this script, so copying it into the project root just works)")
    ap.add_argument("--data", nargs="*", default=[], metavar="DIR", help="extra data directories (created and gitignored)")
    ap.add_argument("--lang", nargs="*", default=None, metavar="LANG",
                    help="only add ignores for these languages: " + " ".join(LANG_SECTION) + " (default: all)")
    ap.add_argument("--docs", choices=["auto", "yes", "no"], default="auto",
                    help="generate the structure docs (English + Chinese). auto = only when the project has no files yet")
    ap.add_argument("--name-prefix", metavar="P", help="expected repo-name prefix; only warns on mismatch (e.g. 5)")
    ap.add_argument("--no-deploy", action="store_true", help="do not create deploy/")
    ap.add_argument("--no-config", action="store_true", help="do not create config-ops-template/")
    ap.add_argument("--no-third-party", action="store_true", help="do not create third-party/")
    ap.add_argument("--no-reference-data", action="store_true", help="do not create reference-data/")
    ap.add_argument("--no-manual-tests", action="store_true", help="do not create manual-tests/")
    ap.add_argument("--no-tests", action="store_true", help="do not create tests/")
    ap.add_argument("--no-data-ops", action="store_true", help="do not create data-ops/sources.yaml")
    ap.add_argument("--gitignore-only", action="store_true",
                    help="only create the stdlayout block in .gitignore (for projects with their own layout): "
                         "no directories or other files; if the block already exists, .gitignore is left untouched")
    ap.add_argument("--git-init", action="store_true",
                    help="if the directory is not a git repository, run `git init` first, then do everything else")
    ap.add_argument("--undo", action="store_true",
                    help="remove what this script generated, but only if you have not changed it "
                         "(unchanged files, empty directories, the stdlayout block in .gitignore); combine with --dry-run to preview")
    ap.add_argument("--dry-run", action="store_true", help="show what would be done, change nothing")
    ap.add_argument("--version", action="version", version="init_project.py " + __version__)
    a = ap.parse_args()

    # Default target = the folder holding this script, so "copy into project root and run" works.
    # 默认目标 = 脚本所在目录,所以"复制到项目根目录直接运行"成立。
    here = Path(__file__).resolve().parent
    if a.path is None:
        a.path = here
    root = Path(a.path).resolve()
    if not root.is_dir():
        sys.exit(f"directory does not exist: {root}")

    # Safety check: only work inside a git repository whose top level is root. A directory that is
    # not a repo is usually a wrongly copied script, so do nothing unless --git-init is given.
    # 安全检查:只在"顶层目录就是 root"的 git 仓库里工作。不是仓库多半是脚本复制错了地方,
    # 除非给了 --git-init,否则什么都不做。
    s = Scaffold(root, a.dry_run)
    if a.undo:
        print(f"project: {root}  (undo" + (", dry-run)" if a.dry_run else ")"))
        s.undo([d.strip("/") for d in a.data])
        return
    top = s.git_toplevel()
    if top == root:
        need_init = False
    elif a.git_init:
        # Not a repo yet, or only a subfolder of another repo: --git-init makes root its own repo.
        # 还不是仓库,或只是别的仓库的子目录:--git-init 让 root 成为独立的仓库。
        need_init = True
    elif top is None:
        sys.exit(f"{root} is not a git repository (or git is not installed). Nothing was done.\n"
                 f"Wrong directory? If this is the right one, run:  {Path(__file__).name} --git-init\n"
                 f"(or run `git init` yourself first). Git & GitHub guide: {PUBLIC_REPO}/blob/main/docs/GIT_GITHUB.md")
    else:
        sys.exit(f"{root} is not a git repository of its own: it is a subfolder of the repository at {top}. Nothing was done.\n"
                 f"Wrong directory? Run the script from {top}, or pass that path.\n"
                 f"To make this folder a separate (nested) repository, run:  {Path(__file__).name} --git-init\n"
                 f"Git & GitHub guide: {PUBLIC_REPO}/blob/main/docs/GIT_GITHUB.md")

    if a.gitignore_only and a.docs == "yes":
        sys.exit("--gitignore-only creates no docs; it cannot be combined with --docs yes")

    # --lang keeps the always-on sections plus the chosen languages.
    # --lang:总是保留通用段,再加上选中的语言段。
    sections = GITIGNORE_SECTIONS
    if a.lang is not None:
        unknown = [x for x in a.lang if x not in LANG_SECTION]
        if unknown:
            sys.exit(f"unknown language: {' '.join(unknown)} (choose from: {' '.join(LANG_SECTION)})")
        keep = ALWAYS_SECTIONS | {LANG_SECTION[x] for x in a.lang}
        sections = [s for s in sections if s[0] in keep]

    # Decides whether PROJECT_STRUCTURE*.md is generated (--docs auto). / 决定是否生成结构说明(--docs auto)。
    empty = is_empty_project(root, Path(__file__).name)
    print(f"stdlayout docs:\n  {PUBLIC_REPO}/blob/main/docs/PROJECT_STRUCTURE.md\n  {PUBLIC_REPO}/blob/main/docs/PROJECT_STRUCTURE.zh-CN.md  (中文)")
    print(f"project: {root}" + ("  (dry-run)" if a.dry_run else "") + ("  [empty project]" if empty else ""))
    if a.name_prefix and not root.name.startswith(a.name_prefix):
        print(f"  ! note: repo name should start with {a.name_prefix}")

    # dirs = what deploy.sh mkdir's; private dirs are created and checked but kept out of deploy.sh.
    # dirs = deploy.sh 要 mkdir 的目录;私有目录会创建和检查,但不进 deploy.sh。
    dirs = RUNTIME_DIRS + [d.strip("/") for d in a.data]
    if need_init:
        s.git_init()
    s.gitignore(sections, [d.strip("/") for d in a.data], skip_existing=a.gitignore_only)
    if a.gitignore_only:
        if not a.dry_run:
            sys.exit(1 if s.verify(dirs + PRIVATE_DIRS) else 0)
        return
    for d in dirs + PRIVATE_DIRS:
        s.mkdir(d)
    if not a.no_deploy:
        s.write("deploy/deploy.sh", DEPLOY_SH % {"dirs": " ".join(dirs)}, exe=True)
        s.write("deploy/healthcheck.sh", HEALTHCHECK_SH, exe=True)
    if not a.no_config:
        s.write("config-ops-template/README.md", CONFIG_README)
    if not a.no_data_ops:
        s.write("data-ops/sources.yaml", SOURCES_YAML)
    if not a.no_reference_data:
        s.write("reference-data/README.md", REFERENCE_DATA_README)
    if not a.no_third_party:
        s.write("third-party/README.md", THIRD_PARTY_README)
    if not a.no_manual_tests:
        s.write("manual-tests/README.md", MANUAL_TESTS_README)
        s.write("manual-tests/FILE-NAMING.md", MANUAL_NAMING_MD)
    if not a.no_tests:
        s.write("tests/README.md", TESTS_README)
    s.write(FILE_ABOUT, ABOUT_MD % {"repo": PUBLIC_REPO})
    # Docs: always for "yes", only for an empty project for "auto". / 文档:yes 一律生成,auto 仅空项目生成。
    if a.docs == "yes" or (a.docs == "auto" and empty):
        fill = {"repo": PUBLIC_REPO, "tree": DOC_TREE}
        s.write(FILE_EN, DOC_EN % fill)
        s.write(FILE_ZH, DOC_ZH % fill)
    if not a.dry_run:
        # Exit code 1 if any check failed, so CI can catch it. / 有检查失败就退出码 1,方便 CI 发现。
        sys.exit(1 if s.verify(dirs + PRIVATE_DIRS) else 0)


if __name__ == "__main__":
    main()
