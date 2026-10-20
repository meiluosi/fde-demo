# 示例

`claims-demo/` 承接 fde-problem-framing 的车险材料核对教学案例，演示一次发现期 Demo 的简报、现场记录和复盘。全部为虚构：人物、数字、时间和客户反应都是示意，不是客户事实，也不是通用默认值。

- [brief.md](claims-demo/brief.md)：简报，含事前登记的成败信号。
- [session-log.md](claims-demo/session-log.md)：现场记录，演示了类型分级和被排除的“解读”。
- [debrief.md](claims-demo/debrief.md)：复盘。信任轴已验证，价值轴与技术轴为部分，结论 Iterate，并保留了一个反向信号。

校验：
```sh
python3 scripts/check_brief.py examples/claims-demo/brief.md
python3 scripts/check_debrief.py examples/claims-demo/debrief.md --log examples/claims-demo/session-log.md --brief examples/claims-demo/brief.md
```
