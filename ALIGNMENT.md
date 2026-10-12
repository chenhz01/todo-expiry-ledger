# ALIGNMENT — todo-expiry-ledger

16-point deliverable alignment for R13. Evidence measured 2026-10-11,
Python 3.13.14, Windows 10.

| # | Item | Status | Evidence |
| --- | --- | --- | --- |
| 1 | 可运行核心代码，纯标准库 | PASS | `todo_expiry_ledger.py` imports only `argparse/json/os/re/sys/datetime`; runs under 3.13.14 |
| 2 | CLI 入口 argparse | PASS | `python todo_expiry_ledger.py scan <path> --as-of --json --compare`; exercised by CLI self-tests |
| 3 | self_test.py 存在且可运行 | PASS | `python self_test.py` exit 0 |
| 4 | 用例数 ≥40 | PASS | 57 checks (SUMMARY: PASS 57/57), measured 2026-10-11 |
| 5 | 三类用例（功能/异常/极端边缘） | PASS | 功能 ~30；异常路径 ~12（损坏 JSON、二进制文件、坏 UTF-8、缺失路径）；极端边缘 ~15（空输入、10k 字符行、Unicode `@阿明`、CRLF、30 层目录） |
| 6 | 末行 `SUMMARY: PASS n/n` | PASS | self_test.py 最后一行输出 `SUMMARY: PASS 57/57` |
| 7 | README 英文文章级 | PASS | 全英文，10 个章节成文 |
| 8 | README 首段 ≤60 词 | PASS | 首段 52 词 |
| 9 | Quickstart 标耗时 | PASS | "~1 second, measured" + 复现命令 `python todo_expiry_ledger.py scan ./src` |
| 10 | why-not-X ≥3 替代含真锚 | PASS | 对比表引用 ttoyaj/ledger (0★)、Gaurang200/TodoLedger (0★)、dugnsdbs/nexus (0★)（名字+星数+一层不同点），均来自 _r13_design.json anchors |
| 11 | Minimal Fallback | PASS | grep 一行命令 fallback，并说明损失的能力 |
| 12 | Design Trade-offs | PASS | 4 条：regex vs parser、注释内日期 vs 元数据文件、快照+compare vs 历史存储、默认窗口 |
| 13 | Limits & Second-order Effects | PASS | 4 条，含 Goodhart 风险与"删 TODO 应对门禁"的二阶效应 |
| 14 | FAQ 含 When NOT to use | PASS | FAQ 4 问，含显式 "When NOT to use this?" |
| 15 | Core Assumptions ≥3 + 置信度 + as of | PASS | 4 条假设；"Confidence: high … medium … As of 2026-10-11" |
| 16 | LICENSE/CHANGELOG/数字纪律/零真名 | PASS | MIT ("zhengming contributors")；CHANGELOG v0.1.0→v0.1.1 修订留痕；耗时数字附实测命令；无真实姓名/密钥，唯一邮箱 hcac4735@agent.qq.com 未出现在仓库内 |
