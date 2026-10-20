# fde-demo · v0.1.3

FDE Skill 系列中管 Demo 的一个：针对一次具体的客户 Demo，按需设计、彩排审查、现场记录、复盘判定，也可对已发生的 Demo 做回溯复盘。fde-ramp 负责行业入门，fde-problem-framing 负责把需求变成可验证的问题，fde-comms 负责与人的沟通，fde-pilot 负责 Demo 之后的试点；本 Skill 承接选定场景，把 Demo 当作一次沟通来设计，并用行为证据判断它换到了什么。可独立运行，不需要安装系列中的其他 Skill，也不修改它们的仓库。系列约定（编号前缀、结论词含义、边界、回写）见 [references/series.md](references/series.md)。

## 核心观点
Demo 同时承担三件事：验证技术可行、验证价值判断、换取信任与访问权限。第一件最容易被高估，第三件最容易被忽略。本 Skill 要求：事前登记主张与成败信号；事后看客户**做了什么**，而不是说了什么；三轴分别判定，再给出 Proceed / Iterate / Pivot / Stop-Defer。

## 安装与使用
将整个 `fde-demo` 文件夹放入宿主的 skills 目录，保留目录名与 SKILL.md。Codex 常用 `${CODEX_HOME:-$HOME/.codex}/skills/`。已有同名目录时先检查，不覆盖：
```sh
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R -n fde-demo "${CODEX_HOME:-$HOME/.codex}/skills/"
```
安装后运行 `python3 "${CODEX_HOME:-$HOME/.codex}/skills/fde-demo/scripts/manifest.py" --check`，核对 references/、templates/、scripts/ 等子目录和文件是否齐全。宿主未发现技能时开启新会话。也可不安装，直接让助手读取本目录 SKILL.md。本 Skill 尚未在用户自己的宿主做实机行为测试；做过的模拟测试见 [tests/RESULTS.md](tests/RESULTS.md)。

可直接说：
- “用 $fde-demo 为这张定义卡设计一次 Demo，先问最影响设计的问题。”
- “彩排审查这份简报，重点看红线、失败样例和 ask。”
- “把这份纪要整理成现场记录表，原话和解读分开。”
- “根据简报和记录表做复盘，判定三轴并给出建议结论。”
- “我想回溯去年做过的一次 Demo，帮我用回溯模式整理，别替我补记不得的细节。”

## 工程内容
- SKILL.md：入口与四种模式路由。
- references/：三个作用与权重、三条红线、七条原则及张力、信号阶梯、三轴规则与结论、证据协议、模式动作、回溯、系列约定、与上下游衔接。
- templates/：简报、彩排审查、现场记录、复盘报告、回溯访谈提纲、回溯适配报告。
- scripts/check_brief.py：简报完整性与红线检查。
- scripts/check_debrief.py：复盘是否越过证据阶梯、结论是否满足条件；`--retro` 用于回溯复盘。
- scripts/small_sample.py：小样本比例的 Wilson 区间，提醒对外写“n 件中 k 件”。
- scripts/manifest.py：生成与校验 MANIFEST.json，发现安装缺失。
- examples/claims-demo/：承接车险材料核对案例的简报、记录、复盘，均为虚构示例，结论为 Iterate。
- 回溯模式的访谈提纲与适配报告模板在 templates/ 中；作者自己的回溯案例记录未公开，不在本仓库。
- tests/：单元测试、行为用例及两轮模拟运行的原始输出。

## 运行验证
Python 3.9+，仅用标准库。
```sh
python3 -I -m unittest discover -s tests -v
python3 scripts/check_brief.py examples/claims-demo/brief.md
python3 scripts/check_debrief.py examples/claims-demo/debrief.md --log examples/claims-demo/session-log.md --brief examples/claims-demo/brief.md
python3 scripts/small_sample.py --k 2 --n 3
python3 scripts/manifest.py --check
```
脚本只检查结构与规则：简报是否写了 ask、失败样例、事前登记；复盘是否把解读当证据、是否在证据不足时判“已验证”或 Proceed。它们不能证明记录真实，不能证明 Demo 有效，也不能代替真人演练。静态检查不能证明模型必然遵守流程；按 tests/behavioral-cases.md 可在目标宿主重跑行为测试。实际结果见 tests/RESULTS.md。

## 参考与致谢

本系列各 Skill 在方法设计上不同程度参考了《FDE:AI落地实战指南》，以及作者本人的 FDE 实践经历。各 Skill 的流程、模板、规则与脚本是在此基础上改写和扩展的方法。示例中的人物、数字与场景均为虚构，不是客户事实。

## 来源与局限
设计依据来自《FDE:AI落地实战指南》与作者个人的实践经历（三个作用、三条红线、七条原则），以及本版在此基础上的优化，见 [DEVELOPMENT.md](DEVELOPMENT.md)。示例的数字、人物、阈值都是示意，不是客户事实。推进计划见 [ROADMAP.md](ROADMAP.md)。

## 许可
MIT，见 [LICENSE](LICENSE)。
