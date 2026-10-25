# tests

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
