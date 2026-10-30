"""Regression tests for init_project.py. Standard library only.
init_project.py 的回归测试。只用标准库。

Run all / 运行全部:   python3 -m unittest discover -s tests -v

Rules for every test here / 本文件所有测试的约定:
  - Run the script as a subprocess in a fresh temp directory, like a user would.
    以子进程方式、在全新的临时目录里运行脚本,和用户的用法一致。
  - ALWAYS pass the target path. Without it the script acts on its own directory (the repository).
    一定带目标路径参数;不带的话脚本会作用于它所在的目录(也就是本仓库)。
  - Judge .gitignore behavior with the real `git check-ignore`, not by reading the file.
    判断 .gitignore 的效果用真实的 `git check-ignore`,而不是读文件内容。
"""
import hashlib
import importlib.util
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "init_project.py"
# Matches any CJK character (used to prove CLI output is English only).
# 匹配任意中日韩汉字(用来证明命令行输出只有英文)。
CJK = re.compile(r"[一-鿿]")


def load_module():
    """Import init_project.py as a module so tests can inspect its tables (GITIGNORE_SECTIONS, ...).
    Safe: the script runs main() only under __main__.
    把脚本当模块导入,检查它的数据表。安全:脚本只在 __main__ 下才执行 main()。"""
    spec = importlib.util.spec_from_file_location("init_project", SCRIPT)
    # spec and spec.loader are Optional in the typeshed stubs; fail loudly instead of with AttributeError.
    # 类型存根里 spec 和 spec.loader 可能是 None;这里明确报错,而不是出现 AttributeError。
    assert spec is not None and spec.loader is not None, f"cannot load {SCRIPT}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(target, *args):
    """Run `init_project.py <target> <args>`; returns CompletedProcess (returncode, stdout, stderr).
    运行脚本,返回 CompletedProcess(退出码、标准输出、标准错误)。"""
    return subprocess.run([sys.executable, str(SCRIPT), str(target), *args],
                          capture_output=True, text=True)


def git(cwd, *args):
    """Run git inside cwd. 在 cwd 目录里运行 git。"""
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)


def ignored(cwd, path):
    """True if git would ignore `path` (a path need not exist). 判断 git 是否会忽略该路径(路径可以不存在)。"""
    return git(cwd, "check-ignore", "-q", path).returncode == 0


def snapshot(root):
    """{relative path: sha256} of every file under root (except .git). Two equal snapshots prove
    that nothing was added, removed or modified.
    root 下所有文件(不含 .git)的 {相对路径: sha256}。两次快照相同,就证明没有新增、删除或修改。"""
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file() and ".git" not in p.parts}


class TmpRepoCase(unittest.TestCase):
    """Base class: every test gets its own empty directory that is already a git repository (self.d).
    基类:每个测试得到一个独立的、已经是 git 仓库的空目录(self.d)。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        # resolve(): on macOS /var is a symlink to /private/var; the script compares resolved paths.
        # resolve():macOS 上 /var 是 /private/var 的软链接,脚本比较的是解析后的路径。
        self.d = Path(self._tmp.name).resolve()
        git(self.d, "init", "-q", "-b", "main")


class SourceChecks(unittest.TestCase):
    """Static checks on the script file and its data tables; nothing is executed.
    对脚本文件本身和它的数据表做静态检查,不实际运行脚本。"""

    def test_compiles(self):
        """The script has no syntax error. 脚本没有语法错误。"""
        r = subprocess.run([sys.executable, "-m", "py_compile", str(SCRIPT)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_only_standard_library(self):
        """Hard rule #1: every import is from the standard library (single file, copy and run).
        不可违背 #1:所有 import 都来自标准库(单文件,复制即用)。"""
        import ast
        if not hasattr(sys, "stdlib_module_names"):
            self.skipTest("needs Python 3.10+")  # 需要 Python 3.10+ 才有 sys.stdlib_module_names
        names = set()
        for n in ast.walk(ast.parse(SCRIPT.read_text(encoding="utf-8"))):
            if isinstance(n, ast.Import):
                names |= {a.name.split(".")[0] for a in n.names}
            elif isinstance(n, ast.ImportFrom) and n.module:
                names.add(n.module.split(".")[0])
        self.assertEqual(names - set(sys.stdlib_module_names), set())

    def test_has_shebang_and_is_executable(self):
        """`./init_project.py` must work: shebang on line 1 and the executable bit set.
        必须能直接 `./init_project.py` 运行:第一行有 shebang,并且有可执行位。"""
        self.assertTrue(SCRIPT.read_text(encoding="utf-8").startswith("#!/usr/bin/env python3"))
        self.assertTrue(SCRIPT.stat().st_mode & 0o111, "run: chmod +x init_project.py")

    def test_section_tables_are_consistent(self):
        """No duplicate section titles; every --lang name and every always-on section points at a real section.
        段标题不重复;每个 --lang 名字和每个"总是写入"的段都指向真实存在的段。"""
        m = load_module()
        titles = [t for t, _ in m.GITIGNORE_SECTIONS]
        self.assertEqual(len(titles), len(set(titles)), "duplicate section title")
        for lang, title in m.LANG_SECTION.items():
            self.assertIn(title, titles, f"--lang {lang} points at a missing section")
        for title in m.ALWAYS_SECTIONS:
            self.assertIn(title, titles)

    def test_no_forbidden_ignore_entries(self):
        """Lock files, generic directory names and must-track directories must never be written as ignores.
        This is the "avoid mistakenly ignoring things" rule in executable form.
        锁文件、过于通用的目录名、必须提交的目录,绝不能作为忽略条目写入。这是"避免误伤"原则的可执行形式。"""
        m = load_module()
        entries = {e for _, es in m.GITIGNORE_SECTIONS for e in es}
        for bad in ["package-lock.json", "Cargo.lock", "go.sum", "Gemfile.lock", "pubspec.lock",
                    "yarn.lock", "poetry.lock", "uv.lock", "renv.lock", "config/", "local/", "bin/",
                    "[Bb]in/", "lib/", "src/", "scripts/", "docs/", "tests/", "test/", "deploy/",
                    "data-ops/", "config-ops-template/", "manual-tests/", "third-party/", "reference-data/", "assets/"]:
            self.assertNotIn(bad, entries)

    def test_third_party_section_is_last(self):
        """In .gitignore a later rule wins, so the third-party / reference-data / assets negations (`!dir/**`)
        must be the LAST three sections, otherwise build-output rules written after them would override them.
        .gitignore 里后面的规则优先,所以 third-party / reference-data / assets 的放行规则(`!dir/**`)必须是最后三段,
        否则排在它们后面的构建产物规则会把它们覆盖掉。"""
        m = load_module()
        last = [t for t, _ in m.GITIGNORE_SECTIONS[-3:]]
        self.assertTrue(last[0].startswith("third-party") and last[1].startswith("reference-data")
                        and last[2].startswith("assets"), last)
        for title in last:
            self.assertIn(title, m.ALWAYS_SECTIONS)

    def test_manual_tests_dirs_contain_nothing_a_test_runner_would_pick_up(self):
        """manual-tests/ as generated by the script must hold only docs and shell scripts:
        no file name that unittest / pytest / go test / jest / cargo / rspec / JUnit / dotnet would collect.
        脚本生成的 manual-tests/ 只能有文档和 shell 脚本:不能有任何会被
        unittest / pytest / go test / jest / cargo / rspec / JUnit / dotnet 收集的文件名。"""
        runner_names = re.compile(
            r"^(test_.*\.py|.*_test\.py|__init__\.py|conftest\.py|.*_test\.go|.*\.(test|spec)\.[cm]?[jt]sx?"
            r"|.*_(spec|test)\.rb|main\.rs|.*\.csproj|.*\.sln|Test.*\.java|.*Tests?\.(java|kt|cs))$")
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp).resolve()
            git(d, "init", "-q", "-b", "main")
            run(d)
            base = d / "manual-tests"
            self.assertTrue(base.is_dir(), base)
            for f in base.rglob("*"):
                if f.is_file():
                    self.assertIsNone(runner_names.match(f.name), f"{f} would be collected by a test runner")
                    self.assertIsNone(re.search("test|spec", f.name, re.I), f"{f}: no 'test'/'spec' in file names")
                    self.assertIn(f.suffix, {".md", ".sh"}, f"{f}: only .md and .sh files belong in manual-tests/")

    def test_version_constant_is_x_y_z_and_printed_by_version_flag(self):
        """__version__ is plain `x.y.z` (digits only) and `--version` prints it.
        __version__ 是纯数字的 `x.y.z`,`--version` 会打印它。"""
        version = load_module().__version__
        self.assertRegex(version, r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
        r = subprocess.run([sys.executable, str(SCRIPT), "--version"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(version, r.stdout + r.stderr)

    def test_no_company_specific_details(self):
        """Project rule #5: the project stays generic; no server paths or internal host names.
        不可违背 #5:项目保持通用,不出现服务器路径或内部主机名。"""
        text = SCRIPT.read_text(encoding="utf-8")
        for word in ["/srv/", "/opt/", "internal.", ".corp", "intranet"]:
            self.assertNotIn(word, text)


class FreshProject(TmpRepoCase):
    """Running on an empty git repository: what is created, and that re-running is harmless.
    在空的 git 仓库上运行:创建了什么,以及重复运行是否无害。"""

    def test_creates_everything_and_passes_its_own_check(self):
        """Exit 0, the built-in `git check-ignore` verification passes, and every standard directory and file exists.
        退出码 0,脚本内置的 git check-ignore 实测通过,所有标准目录和文件都已创建。"""
        r = run(self.d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(".gitignore check passed", r.stdout)
        for rel in ["data", "db", "upload", "logs", "tmp", "private-docs", "deploy", "config-ops-template",
                    "data-ops", "tests", "manual-tests", "third-party", "reference-data", "assets"]:
            self.assertTrue((self.d / rel).is_dir(), rel)
        for rel in ["assets/images", "assets/icons", "assets/animations", "assets/video", "tests/fixtures"]:
            self.assertTrue((self.d / rel / ".gitkeep").is_file(), rel)
        for rel in [".gitignore", "deploy/deploy.sh", "deploy/healthcheck.sh", "config-ops-template/README.md",
                    "data-ops/sources.yaml", "tests/README.md", "manual-tests/README.md", "manual-tests/FILE-NAMING.md", "third-party/README.md",
                    "reference-data/README.md", "assets/README.md", "STDLAYOUT.md", "PROJECT_STRUCTURE.md",
                    "PROJECT_STRUCTURE.zh-CN.md"]:
            self.assertTrue((self.d / rel).is_file(), rel)

    def test_deploy_scripts_are_executable_and_valid_bash(self):
        """Generated deploy/*.sh have the executable bit and pass `bash -n` (syntax check).
        生成的 deploy/*.sh 有可执行位,并且通过 `bash -n` 语法检查。"""
        run(self.d)
        for name in ["deploy.sh", "healthcheck.sh"]:
            p = self.d / "deploy" / name
            self.assertTrue(p.stat().st_mode & 0o100, name)
            self.assertEqual(subprocess.run(["bash", "-n", str(p)]).returncode, 0, name)

    def test_deploy_sh_creates_runtime_dirs_but_not_private_dirs(self):
        """Ignored runtime dirs do not exist after `git clone`, so deploy.sh must mkdir them;
        private-docs is developer-only and must not be created in production.
        被忽略的运行时目录在 git clone 后不存在,所以 deploy.sh 要 mkdir 它们;
        private-docs 只给开发者用,不应该在生产环境创建。"""
        run(self.d)
        text = (self.d / "deploy/deploy.sh").read_text(encoding="utf-8")
        self.assertIn("mkdir -p data db upload logs tmp", text)
        self.assertNotIn("private-docs", text)

    def test_second_run_changes_nothing(self):
        """Idempotence (hard rule #2): a second run leaves every file byte-identical and reports
        "up to date" instead of create/append.
        幂等(不可违背 #2):第二次运行后所有文件逐字节不变,输出是 "up to date" 而不是 create/append。"""
        run(self.d)
        before = snapshot(self.d)
        r = run(self.d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(snapshot(self.d), before)
        self.assertNotRegex(r.stdout, r"^\s+(create|append)\s", "second run must not create or append")
        self.assertIn("up to date", r.stdout)

    def test_dry_run_writes_nothing(self):
        """--dry-run only prints; the directory stays empty (apart from .git).
        --dry-run 只打印,目录里除了 .git 什么都没有。"""
        r = run(self.d, "--dry-run")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual([p.name for p in self.d.iterdir() if p.name != ".git"], [])

    def test_option_switches(self):
        """--no-* switches skip their directory, --docs no skips the docs, --data adds extra ignored directories.
        --no-* 开关跳过对应目录,--docs no 不生成文档,--data 增加额外的被忽略目录。"""
        r = run(self.d, "--no-deploy", "--no-config", "--no-data-ops", "--no-tests", "--no-manual-tests", "--no-third-party",
                "--no-reference-data", "--docs", "no", "--data", "cache", "models")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for rel in ["deploy", "config-ops-template", "data-ops", "tests", "manual-tests", "third-party",
                    "reference-data", "PROJECT_STRUCTURE.md"]:
            self.assertFalse((self.d / rel).exists(), rel)
        for rel in ["cache", "models"]:
            self.assertTrue((self.d / rel).is_dir())
            self.assertTrue(ignored(self.d, rel + "/x"))


class IgnoreRules(TmpRepoCase):
    """The generated .gitignore, judged by real `git check-ignore`. Paths do not need to exist.
    用真实的 git check-ignore 判断生成的 .gitignore;路径不需要真实存在。"""

    def setUp(self):
        super().setUp()
        self.assertEqual(run(self.d).returncode, 0)

    def test_must_be_ignored(self):
        """Secrets, runtime data, private docs and typical build output are ignored.
        密钥、运行时数据、私有文档和典型的构建产物都被忽略。"""
        for path in ["config-ops/app.json", ".env", ".env.local", "data/x", "db/x", "upload/x", "logs/x",
                     "tmp/x", "private-docs/x.md", "app.log", "tools/foo.exe", "foo.dll", "lib.jar",
                     "node_modules/x", "__pycache__/x.pyc", ".venv/x", "target/x", "build/x", "Foo.class",
                     "obj/x.dll", ".vs/x", "foo.pyc", ".dart_tool/x", "dist-newstyle/x", ".stack-work/x",
                     "_build/x", "blib/x"]:
            self.assertTrue(ignored(self.d, path), f"{path} should be ignored")

    def test_must_not_be_ignored(self):
        """Committed directories, templates, lock files and generic directory names are NOT ignored.
        This protects against over-broad rules (the "avoid mistakenly ignoring" principle).
        提交型目录、模板、锁文件和通用目录名不能被忽略。防止规则过宽(避免误伤原则)。"""
        for path in ["config-ops-template/app.json.example", "data-ops/sources.yaml", "deploy/deploy.sh",
                     "tests/test_x.py", "manual-tests/check-windows.sh", ".env.example", "reference-data/region.sqlite3",
                     "reference-data/id_region_codes.csv", "assets/images/logo.png",
                     "assets/animations/spin.gif", "assets/icons/a.svg", "assets/video/intro.mp4", "tests/fixtures/.gitkeep", "package-lock.json", "Cargo.lock", "go.sum",
                     "Gemfile.lock", "pubspec.lock", "renv.lock", "poetry.lock", "yarn.lock",
                     "gradle/wrapper/gradle-wrapper.jar", "README.md", "STDLAYOUT.md",
                     "src/main.py", "bin/run.sh", "lib/x.py", "config/app.yaml", "local/x", "scripts/x.sh",
                     "docs/index.md", "test/x"]:
            self.assertFalse(ignored(self.d, path), f"{path} must NOT be ignored")

    def test_third_party_keeps_prebuilt_binaries_and_build_dirs(self):
        """Inside third-party/ even *.exe, *.dll, *.jar, build/, dist/, node_modules/ are kept,
        because prebuilt third-party files are committed on purpose.
        third-party/ 里连 *.exe、*.dll、*.jar、build/、dist/、node_modules/ 都保留,因为预编译的第三方文件是特意提交的。"""
        for path in ["third-party/README.md", "third-party/foo/foo.exe", "third-party/foo/bar.dll",
                     "third-party/lib/x.jar", "third-party/lib/x.so", "third-party/foo/build/out.o",
                     "third-party/foo/node_modules/a/index.js", "third-party/foo/dist/x.js",
                     "third-party/foo/__pycache__/x.pyc", "third-party/foo/target/x.rlib"]:
            self.assertFalse(ignored(self.d, path), f"{path} must NOT be ignored")

    def test_reference_data_keeps_databases_but_not_secrets(self):
        """reference-data/ keeps *.db / *.sqlite / csv (static lookup data), still ignores junk and secrets,
        and the runtime data/ directory next to it stays ignored.
        reference-data/ 保留 *.db / *.sqlite / csv(静态对照数据),仍然忽略垃圾文件和密钥;旁边的运行时 data/ 依然被忽略。"""
        for path in ["reference-data/id_region.db", "reference-data/region.sqlite", "reference-data/a/b/x.csv"]:
            self.assertFalse(ignored(self.d, path), f"{path} must NOT be ignored")
        for path in ["reference-data/.env", "reference-data/.DS_Store", "reference-data/x/id_rsa"]:
            self.assertTrue(ignored(self.d, path), f"{path} should be ignored")
        self.assertTrue(ignored(self.d, "data/region.sqlite"), "runtime data/ stays ignored")

    def test_assets_keeps_pictures_but_not_junk(self):
        """assets/ keeps images, GIF/WebP animations and SVG even inside build-like names, but still ignores
        editor junk and secrets placed inside it.
        assets/ 里的图片、GIF/WebP 动图、SVG 都保留(哪怕在 build 之类的目录名下),但里面的编辑器垃圾文件和密钥仍被忽略。"""
        for path in ["assets/images/logo.png", "assets/animations/a.gif", "assets/animations/a.webp",
                     "assets/icons/a.svg", "assets/build/x.png", "assets/dist/x.png"]:
            self.assertFalse(ignored(self.d, path), f"{path} must NOT be ignored")
        for path in ["assets/.DS_Store", "assets/images/.env", "assets/x/id_rsa"]:
            self.assertTrue(ignored(self.d, path), f"{path} should be ignored")

    def test_third_party_still_ignores_junk_and_secrets(self):
        """The un-ignore of third-party/ does not re-include editor junk or secrets placed inside it.
        third-party/ 的整体放行不会把里面的编辑器垃圾文件和密钥重新放进来。"""
        for path in ["third-party/.DS_Store", "third-party/foo/Thumbs.db", "third-party/foo/a.swp",
                     "third-party/foo/a.txt~", "third-party/foo/.env", "third-party/foo/.env.local",
                     "third-party/foo/id_rsa"]:
            self.assertTrue(ignored(self.d, path), f"{path} should be ignored")


class ExistingProject(TmpRepoCase):
    """Running on a project that already has files: nothing of the user's may be overwritten or reordered.
    在已有文件的项目上运行:用户的任何内容都不能被覆盖或改动顺序。"""

    def test_existing_files_survive_and_gitignore_is_append_only(self):
        """An existing .gitignore keeps its lines first and in order (no duplicate of `data/`); an existing
        README.md and deploy/deploy.sh are left byte-identical; missing rules are appended.
        已有的 .gitignore 原有行保持在最前且顺序不变(`data/` 不重复);已有的 README.md 和 deploy/deploy.sh 原样保留;缺少的规则被追加。"""
        (self.d / ".gitignore").write_text("# mine\nfoo.txt\ndata/\n", encoding="utf-8")
        (self.d / "README.md").write_text("keep me\n", encoding="utf-8")
        (self.d / "deploy").mkdir()
        (self.d / "deploy/deploy.sh").write_text("#!/bin/sh\necho mine\n", encoding="utf-8")
        r = run(self.d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        gi = (self.d / ".gitignore").read_text(encoding="utf-8")
        self.assertTrue(gi.startswith("# mine\nfoo.txt\ndata/\n"), "existing lines must stay first and untouched")
        # count whole-line occurrences of `data/` (it was already there, so it must not be added again)
        # 统计整行 `data/` 出现的次数(原来就有,所以不能再追加一次)
        self.assertEqual(gi.count("\ndata/\n") + (1 if gi.startswith("data/\n") else 0), 1, "data/ duplicated")
        self.assertIn("config-ops/", gi)
        self.assertEqual((self.d / "README.md").read_text(encoding="utf-8"), "keep me\n")
        self.assertEqual((self.d / "deploy/deploy.sh").read_text(encoding="utf-8"), "#!/bin/sh\necho mine\n")

    def test_user_unignore_rule_is_kept_and_honoured(self):
        """A user's own `!path` line (the way to commit a normally-ignored *.exe) survives re-running
        and keeps working, while other *.exe files stay ignored.
        用户自己写的 `!路径` 行(提交被忽略的 *.exe 的办法)在重复运行后依然存在并生效,其他 *.exe 仍被忽略。"""
        run(self.d)
        with open(self.d / ".gitignore", "a", encoding="utf-8") as f:
            f.write("!tools/foo.exe\n")
        run(self.d)
        self.assertIn("!tools/foo.exe", (self.d / ".gitignore").read_text(encoding="utf-8"))
        self.assertFalse(ignored(self.d, "tools/foo.exe"))
        self.assertTrue(ignored(self.d, "tools/bar.exe"))

    def test_docs_only_for_empty_project_unless_forced(self):
        """PROJECT_STRUCTURE*.md are written only for an empty project (--docs auto); --docs yes forces them.
        只有空项目才生成 PROJECT_STRUCTURE*.md(--docs auto);--docs yes 可强制生成。"""
        (self.d / "main.py").write_text("print(1)\n", encoding="utf-8")
        run(self.d)
        self.assertFalse((self.d / "PROJECT_STRUCTURE.md").exists())
        run(self.d, "--docs", "yes")
        self.assertTrue((self.d / "PROJECT_STRUCTURE.md").exists())

    def test_lang_limits_language_sections_only(self):
        """--lang go keeps the always-on sections (secrets, private docs, ...) plus Go, and drops other languages.
        --lang go 保留总是写入的段(密钥、私有文档等)加上 Go,去掉其他语言。"""
        r = run(self.d, "--lang", "go")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        gi = (self.d / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("config-ops/", gi)
        self.assertIn("private-docs/", gi)
        self.assertIn("go.work", gi)
        self.assertNotIn("__pycache__/", gi)
        self.assertNotIn("node_modules/", gi)

    def test_unknown_lang_is_rejected(self):
        """An unknown --lang name is an error, and nothing is written.
        未知的 --lang 名字报错,并且什么都不写。"""
        r = run(self.d, "--lang", "cobol-9000")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("unknown language", r.stdout + r.stderr)
        self.assertFalse((self.d / ".gitignore").exists())

    def test_conflicting_rule_fails_the_check(self):
        """If the user's .gitignore ignores deploy/ or tests/, the built-in check reports it and exits 1.
        如果用户的 .gitignore 忽略了 deploy/ 或 tests/,内置实测会报告并以退出码 1 结束。"""
        (self.d / ".gitignore").write_text("deploy/\ntests/\n", encoding="utf-8")
        r = run(self.d)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("must not be ignored", r.stdout)

    def test_tracked_secret_fails_the_check(self):
        """A file already tracked under config-ops/ (a leaked secret) makes the check fail with exit 1.
        config-ops/ 下已被 git 跟踪的文件(已泄露的密钥)会让实测失败,退出码 1。"""
        (self.d / "config-ops").mkdir()
        (self.d / "config-ops/secret.json").write_text("{}", encoding="utf-8")
        git(self.d, "add", "-f", "config-ops/secret.json")  # -f: force-add despite the ignore rule / 强制添加
        r = run(self.d)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("tracked by git", r.stdout)


class ManagedBlock(TmpRepoCase):
    """Everything the script writes into .gitignore sits between the BEGIN and END marker lines;
    the user's own lines outside the block are never touched, so manual edits cannot conflict.
    脚本写进 .gitignore 的一切都在 BEGIN 和 END 标记行之间;块外的用户行绝不改动,所以手工修改不会冲突。"""

    def block_bounds(self, text):
        lines = text.splitlines()
        b = [i for i, ln in enumerate(lines) if ln.startswith("# >>> BEGIN stdlayout")]
        e = [i for i, ln in enumerate(lines) if ln.startswith("# <<< END stdlayout")]
        return lines, b, e

    def test_fresh_file_has_exactly_one_block(self):
        """A new .gitignore is one BEGIN ... END block; everything the script wrote is inside it.
        新建的 .gitignore 就是一个 BEGIN ... END 块;脚本写的一切都在块内。"""
        run(self.d)
        lines, b, e = self.block_bounds((self.d / ".gitignore").read_text(encoding="utf-8"))
        self.assertEqual((b, e), ([0], [len(lines) - 1]))

    def test_user_lines_before_and_after_the_block_are_untouched_across_runs(self):
        """User lines above and below the block survive any number of runs, byte for byte, in place.
        块上方和下方的用户行在任意多次运行后都原样保留、位置不变。"""
        (self.d / ".gitignore").write_text("# mine-top\nfoo.txt\n", encoding="utf-8")
        run(self.d)
        with open(self.d / ".gitignore", "a", encoding="utf-8") as f:
            f.write("# mine-bottom\n!tools/foo.exe\nbar.txt\n")
        for args in [(), ("--lang", "python"), ("--data", "cache"), ()]:
            self.assertEqual(run(self.d, *args).returncode, 0)
        text = (self.d / ".gitignore").read_text(encoding="utf-8")
        lines, b, e = self.block_bounds(text)
        self.assertEqual(len(b), 1)
        self.assertEqual(len(e), 1)
        self.assertEqual(lines[:b[0]], ["# mine-top", "foo.txt", ""])
        self.assertEqual(lines[e[0] + 1:], ["# mine-bottom", "!tools/foo.exe", "bar.txt"])

    def test_rerun_with_more_languages_stays_inside_block_and_keeps_unignore_last(self):
        """Adding a language in a LATER run inserts it inside the block, before the third-party /
        reference-data un-ignore sections, so those still win and prebuilt binaries stay un-ignored.
        以后的运行追加语言时,新段插在块内、third-party / reference-data 放行段之前,放行规则依然优先,预编译二进制依然不被忽略。"""
        run(self.d, "--lang", "go")
        run(self.d, "--lang", "python")
        text = (self.d / ".gitignore").read_text(encoding="utf-8")
        lines, b, e = self.block_bounds(text)
        self.assertEqual((len(b), len(e)), (1, 1))
        inner = lines[b[0]:e[0]]
        self.assertIn("__pycache__/", inner)
        self.assertLess(inner.index("__pycache__/"), inner.index("!third-party/**"))
        self.assertFalse(ignored(self.d, "third-party/x/build/out.o"))
        self.assertFalse(ignored(self.d, "third-party/x/y.exe"))
        self.assertTrue(ignored(self.d, "build/out.o"))

    def test_entries_already_in_user_lines_are_not_duplicated_in_block(self):
        """A rule the user already wrote outside the block is not written again inside it.
        用户已经在块外写过的规则,不会在块内再写一遍。"""
        (self.d / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
        run(self.d)
        self.assertEqual((self.d / ".gitignore").read_text(encoding="utf-8").count("node_modules/"), 1)

    def test_broken_block_is_refused_and_file_untouched(self):
        """BEGIN without END (or the reverse): the script refuses, exits non-zero and leaves the file byte-identical.
        只有 BEGIN 没有 END(或相反):脚本拒绝执行、退出码非 0,文件保持原样。"""
        broken = "mine\n# >>> BEGIN stdlayout\nfoo\n"
        (self.d / ".gitignore").write_text(broken, encoding="utf-8")
        r = run(self.d)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("broken stdlayout block", r.stdout + r.stderr)
        self.assertEqual((self.d / ".gitignore").read_text(encoding="utf-8"), broken)


class GitignoreOnly(TmpRepoCase):
    """--gitignore-only writes just the .gitignore block, for projects with their own layout.
    --gitignore-only 只写 .gitignore 块,给有自己目录结构的项目用。"""

    def test_creates_only_gitignore_and_passes_check(self):
        """On an empty repo only .gitignore appears: no directories, no STDLAYOUT.md, no docs.
        在空仓库上只多出 .gitignore:没有目录、没有 STDLAYOUT.md、没有结构文档。"""
        r = run(self.d, "--gitignore-only")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(sorted(snapshot(self.d)), [".gitignore"])
        self.assertEqual([p.name for p in self.d.iterdir() if p.name != ".git"], [".gitignore"])
        self.assertTrue(ignored(self.d, "config-ops/x"))
        self.assertFalse(ignored(self.d, "deploy/x"))

    def test_existing_block_is_left_untouched(self):
        """If the block exists (even a partial one), .gitignore stays byte-identical and the run succeeds.
        已有该块(哪怕不完整)时,.gitignore 保持逐字节不变,运行成功。"""
        run(self.d, "--gitignore-only", "--lang", "python")
        before = snapshot(self.d)
        r = run(self.d, "--gitignore-only")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(snapshot(self.d), before)

    def test_user_lines_survive_and_block_is_added(self):
        """A user's own .gitignore keeps its lines first; the block is appended after them.
        用户已有的 .gitignore 原有行保持在最前,块追加在后面。"""
        (self.d / ".gitignore").write_text("# mine\nfoo.txt\n", encoding="utf-8")
        r = run(self.d, "--gitignore-only")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        gi = (self.d / ".gitignore").read_text(encoding="utf-8")
        self.assertTrue(gi.startswith("# mine\nfoo.txt\n"))
        self.assertIn("config-ops/", gi)
        self.assertEqual(sorted(snapshot(self.d)), [".gitignore"])

    def test_docs_yes_is_rejected(self):
        """--docs yes contradicts --gitignore-only and is refused before anything is written.
        --docs yes 与 --gitignore-only 矛盾,在写任何东西之前被拒绝。"""
        r = run(self.d, "--gitignore-only", "--docs", "yes")
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(snapshot(self.d), {})


class Undo(TmpRepoCase):
    """--undo removes what the script generated, but only what the user has not changed.
    --undo 撤销脚本生成的内容,但只撤销用户没动过的。"""

    def listing(self):
        return sorted(str(p.relative_to(self.d)) for p in self.d.rglob("*") if ".git" not in p.parts)

    def test_undo_after_fresh_run_leaves_nothing_behind(self):
        """Run then --undo on an empty repo: no file, no directory, no .gitignore is left (only .git).
        This also catches any new generated file that --undo forgot to list.
        在空仓库上先运行再 --undo:不剩任何文件、目录和 .gitignore(只剩 .git)。也能发现 --undo 漏掉的新生成文件。"""
        run(self.d)
        r = run(self.d, "--undo")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.listing(), [])

    def test_undo_dry_run_changes_nothing_and_second_undo_is_a_noop(self):
        """--undo --dry-run only prints; a second real --undo has nothing left to do.
        --undo --dry-run 只打印;第二次真正的 --undo 无事可做。"""
        run(self.d)
        before = snapshot(self.d)
        r = run(self.d, "--undo", "--dry-run")
        self.assertIn("remove", r.stdout)
        self.assertEqual(snapshot(self.d), before)
        run(self.d, "--undo")
        r = run(self.d, "--undo")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("remove", r.stdout)

    def test_modified_files_and_non_empty_directories_are_kept(self):
        """A generated file you edited stays (with its directory); data in runtime dirs stays; unchanged files go.
        你改过的生成文件连同它的目录一起保留;运行时目录里的数据保留;没改的文件被删。"""
        run(self.d)
        (self.d / "tests/README.md").write_text("my own notes\n", encoding="utf-8")
        (self.d / "data/keep.txt").write_text("precious\n", encoding="utf-8")
        r = run(self.d, "--undo")
        self.assertIn("modified by you", r.stdout)
        self.assertEqual((self.d / "tests/README.md").read_text(encoding="utf-8"), "my own notes\n")
        self.assertEqual((self.d / "data/keep.txt").read_text(encoding="utf-8"), "precious\n")
        self.assertFalse((self.d / "deploy").exists())
        self.assertFalse((self.d / "manual-tests").exists())

    def test_only_the_stdlayout_block_is_removed_from_gitignore(self):
        """User lines above and below the block survive --undo; the block (BEGIN..END) is gone.
        块上方和下方的用户行在 --undo 后保留;BEGIN..END 之间的块被删掉。"""
        (self.d / ".gitignore").write_text("mine-top\n", encoding="utf-8")
        run(self.d)
        with open(self.d / ".gitignore", "a", encoding="utf-8") as f:
            f.write("mine-bottom\n")
        run(self.d, "--undo")
        self.assertEqual((self.d / ".gitignore").read_text(encoding="utf-8"), "mine-top\nmine-bottom\n")

    def test_undo_never_touches_other_files_or_git(self):
        """Files the script never generates (and .git) are untouched by --undo.
        脚本从不生成的文件(以及 .git)不受 --undo 影响。"""
        (self.d / "main.py").write_text("print(1)\n", encoding="utf-8")
        (self.d / "README.md").write_text("hello\n", encoding="utf-8")
        run(self.d)
        run(self.d, "--undo")
        self.assertEqual(self.listing(), ["README.md", "main.py"])
        self.assertTrue((self.d / ".git").is_dir())

    def test_undo_works_without_a_git_repository(self):
        """--undo does not need a git repo (it only removes files identical to its own templates).
        --undo 不需要 git 仓库(只删与自己模板完全一致的文件)。"""
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp).resolve()
            run(d, "--git-init")
            subprocess.run(["rm", "-rf", str(d / ".git")])
            r = run(d, "--undo")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(list(d.iterdir()), [])


class GitRepoRequirement(unittest.TestCase):
    """The git-repository safety check and --git-init. Starts from a plain (non-git) temp directory.
    git 仓库安全检查和 --git-init。从一个普通的(非 git)临时目录开始。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.d = Path(self._tmp.name).resolve()

    def test_not_a_repo_does_nothing(self):
        """Not a git repo and no --git-init: exit 1, the message names the problem and the fix,
        and the directory is still empty (the script was probably copied to the wrong place).
        不是 git 仓库且没给 --git-init:退出码 1,提示说明问题和解决办法,目录仍然是空的(多半是脚本复制错了位置)。"""
        r = run(self.d)
        self.assertEqual(r.returncode, 1)
        self.assertIn("not a git repository", r.stdout + r.stderr)
        self.assertIn("--git-init", r.stdout + r.stderr)
        self.assertEqual(list(self.d.iterdir()), [])

    def test_git_init_creates_repo_on_main_then_does_everything(self):
        """--git-init: creates the repo on branch `main`, then does all the normal work and passes the check.
        --git-init:先在 main 分支上创建仓库,再做全部正常工作,并通过实测。"""
        r = run(self.d, "--git-init")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((self.d / ".git").is_dir())
        self.assertEqual(git(self.d, "symbolic-ref", "--short", "HEAD").stdout.strip(), "main")
        self.assertTrue((self.d / "tests/README.md").is_file())
        self.assertIn(".gitignore check passed", r.stdout)

    def test_git_init_dry_run_creates_nothing(self):
        """--git-init --dry-run only prints; no .git and no files.
        --git-init --dry-run 只打印,不创建 .git 也不创建文件。"""
        r = run(self.d, "--git-init", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(list(self.d.iterdir()), [])

    def test_git_init_on_existing_repo_does_not_reinit(self):
        """On a repo that already exists, --git-init is a no-op for git (the branch name stays as it was).
        在已有仓库上,--git-init 对 git 不做任何事(分支名保持原样)。"""
        git(self.d, "init", "-q", "-b", "trunk")
        r = run(self.d, "--git-init")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("git init", r.stdout)
        self.assertEqual(git(self.d, "symbolic-ref", "--short", "HEAD").stdout.strip(), "trunk")

    def test_subfolder_of_a_repo_is_refused_without_flag_and_nested_with_it(self):
        """A subfolder of another repo: refused without --git-init (message mentions the flag, nothing written);
        with --git-init it becomes its own nested repository.
        别的仓库的子目录:不加 --git-init 被拒绝(提示里提到该选项,什么都不写);加了就成为独立的嵌套仓库。"""
        git(self.d, "init", "-q", "-b", "main")
        sub = self.d / "sub"
        sub.mkdir()
        r = run(sub)
        self.assertEqual(r.returncode, 1)
        self.assertIn("subfolder", r.stdout + r.stderr)
        self.assertIn("--git-init", r.stdout + r.stderr)
        self.assertEqual(list(sub.iterdir()), [])
        r = run(sub, "--git-init")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((sub / ".git").is_dir())

    def test_missing_directory_is_an_error(self):
        """A target path that does not exist is an error, not silently created.
        目标路径不存在是错误,不会被悄悄创建。"""
        r = run(self.d / "nope")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("does not exist", r.stdout + r.stderr)


class OutputAndDocs(TmpRepoCase):
    """CLI output language and consistency between the script, `docs/` and the READMEs.
    命令行输出的语言,以及脚本、docs/、README 三者之间的一致性。"""

    def test_cli_output_is_english(self):
        """CLI output is for developers worldwide: normal run, re-run, --dry-run and -h contain no Chinese
        (only the single "(中文)" link marker is allowed).
        命令行输出面向全球开发者:正常运行、重复运行、--dry-run 和 -h 都不含中文(只允许一个 "(中文)" 链接标记)。"""
        outs = [run(self.d), run(self.d), run(self.d, "--dry-run"),
                subprocess.run([sys.executable, str(SCRIPT), "-h"], capture_output=True, text=True)]
        for r in outs:
            text = (r.stdout + r.stderr).replace("(中文)", "")
            self.assertIsNone(CJK.search(text), f"non-English CLI output: {CJK.findall(text)[:5]}")

    def test_generated_docs_match_docs_dir(self):
        """docs/PROJECT_STRUCTURE*.md must equal what the script generates now. If this fails you changed
        DOC_EN / DOC_ZH / DOC_TREE: regenerate with --docs yes in a temp git repo and copy both files into docs/.
        docs/PROJECT_STRUCTURE*.md 必须和脚本现在生成的内容一致。失败说明你改了 DOC_EN / DOC_ZH / DOC_TREE:
        在临时 git 仓库里用 --docs yes 重新生成,再把两个文件复制到 docs/。"""
        run(self.d, "--docs", "yes")
        for name in ["PROJECT_STRUCTURE.md", "PROJECT_STRUCTURE.zh-CN.md"]:
            self.assertEqual((self.d / name).read_text(encoding="utf-8"),
                             (ROOT / "docs" / name).read_text(encoding="utf-8"),
                             f"docs/{name} is stale: regenerate it from the script")

    def test_docs_mention_every_created_directory(self):
        """Both generated structure docs explain every directory the script creates.
        两份生成的结构说明都解释了脚本创建的每一个目录。"""
        run(self.d)
        for name in ["PROJECT_STRUCTURE.md", "PROJECT_STRUCTURE.zh-CN.md"]:
            text = (self.d / name).read_text(encoding="utf-8")
            for rel in ["deploy/", "config-ops-template/", "config-ops/", "data-ops/", "tests/", "manual-tests/", "data/", "db/",
                        "upload/", "logs/", "tmp/", "private-docs/", "third-party/", "reference-data/", "assets/"]:
                self.assertIn(f"`{rel}`", text, f"{name} does not explain {rel}")

    def test_readmes_document_every_option(self):
        """Every `--option` registered with argparse appears in both README.md and README.zh-CN.md.
        argparse 里注册的每个 `--选项` 都出现在 README.md 和 README.zh-CN.md 里。"""
        text = SCRIPT.read_text(encoding="utf-8")
        flags = set(re.findall(r'add_argument\("(--[a-z-]+)"', text))
        self.assertTrue(flags)
        for readme in ["README.md", "README.zh-CN.md"]:
            body = (ROOT / readme).read_text(encoding="utf-8")
            for flag in flags:
                self.assertIn(flag, body, f"{readme} does not mention {flag}")

    def test_both_git_guides_exist_and_cover_same_sections(self):
        """The English and Chinese Git & GitHub guides exist and have the same number of `##` sections
        (cheap guard against updating only one language).
        中英文的 Git 与 GitHub 指南都存在,且 `##` 小节数量相同(粗略防止只更新了一种语言)。"""
        en = (ROOT / "docs/GIT_GITHUB.md").read_text(encoding="utf-8")
        zh = (ROOT / "docs/GIT_GITHUB.zh-CN.md").read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r"^## ", en, re.M)), len(re.findall(r"^## ", zh, re.M)))

    def test_every_listed_language_in_readme_has_a_section(self):
        """The languages promised in README.md are all named there, and the script has at least 20 sections
        (4 general + the languages). A loose guard: it catches a README/script mismatch, not wrong entries.
        README.md 里承诺的语言都有写出,脚本至少有 20 段(4 个通用段 + 各语言)。这是宽松的检查:只发现 README 与脚本不符,不检查条目对错。"""
        m = load_module()
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for lang in ["Python", "Rust", "Go", "Swift", "Android", "Flutter", "CUDA", "Julia", "Ada", "Fortran",
                     "Haskell", "Lua", "OCaml", "Perl", "Qt", "Ruby", "Delphi"]:
            self.assertIn(lang, readme)
        self.assertGreaterEqual(len(m.GITIGNORE_SECTIONS), 20)


if __name__ == "__main__":
    unittest.main()
