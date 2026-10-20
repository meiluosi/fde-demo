"""复盘规则检查：核对三轴状态是否越过证据阶梯、结论是否满足条件。不验证记录本身是否真实。"""
import argparse
import json
import re
import sys
from pathlib import Path

LOG_TYPES = ('行为', '承诺', '具体言语', '泛泛言语', '技术观测', '解读')
AXES = ('技术可行', '价值判断', '信任与权限')
ALLOWED = {  # 该轴“已验证”可计入的记录类型
    '技术可行': ('技术观测', '行为'),
    '价值判断': ('行为', '承诺'),
    '信任与权限': ('行为', '承诺'),
}
PARTIAL_TYPES = ('行为', '承诺', '具体言语', '技术观测')
REFUTE_TYPES = ('行为', '承诺', '技术观测')
VERDICTS = ('Proceed', 'Iterate', 'Pivot', 'Stop-Defer')
NEXT_KEYS = {'Proceed': ('试点范围建议',), 'Iterate': ('补验证', '下次改什么'),
             'Pivot': ('转向',), 'Stop-Defer': ('重开条件',)}


def parse_log(text):
    log = {}
    for line in text.splitlines():
        if not line.strip().startswith('|'):
            continue
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) >= 3 and re.fullmatch(r'L\d+', cells[0]):
            log[cells[0]] = cells[1]
    return log


def field(text, key):
    for line in text.splitlines():
        m = re.match(r'^\s*[-*]\s*' + key + r'[：:]\s*(.*)$', line)
        if m:
            v = m.group(1).strip()
            return None if v in ('', '待填') else v
    return None


def section_filled(text, keyword):
    cur, body = None, {}
    for line in text.splitlines():
        m = re.match(r'^##\s+(.*)', line)
        if m:
            cur = m.group(1).strip()
            body[cur] = []
        elif cur:
            s = line.strip()
            if s and not s.startswith('>') and s != '待填':
                body[cur].append(s)
    return any(keyword in h and body[h] for h in body)


def check(debrief, log, brief=None, retro=False):
    errors, warnings = [], []
    is_retro_text = bool(re.search(r'复盘类型[：:]\s*回溯', debrief))
    if retro and not is_retro_text:
        errors.append('回溯复盘须写明“复盘类型：回溯”')
    if is_retro_text and not retro:
        warnings.append('复盘类型为回溯，请加 --retro 复查（回溯记录均为转述，不得已验证或 Proceed）')
    for i, t in log.items():
        if t not in LOG_TYPES:
            errors.append('记录 %s 的类型“%s”不在：%s' % (i, t, ' / '.join(LOG_TYPES)))

    m = re.search(r'建议结论[：:]\s*(Proceed|Iterate|Pivot|Stop-Defer)\b', debrief)
    verdict = m.group(1) if m else None
    if not verdict:
        errors.append('未找到有效的建议结论（Proceed / Iterate / Pivot / Stop-Defer）')

    status = {}
    for axis in AXES:
        m = re.search(r'^\s*[-*]\s*' + axis + r'[：:]\s*(已验证|部分|未验证|被推翻)\s*[｜|]\s*证据[：:]\s*([^｜|\n]*)',
                      debrief, re.M)
        if not m:
            errors.append('未找到“%s”的判定（格式：- 轴：状态｜证据：L1,L2｜范围：…）' % axis)
            continue
        st, ids = m.group(1), re.findall(r'L\d+', m.group(2))
        status[axis] = st
        if retro and st == '已验证':
            errors.append('%s：回溯复盘的记录均为转述，不得判已验证' % axis)
        unknown = [i for i in ids if i not in log]
        if unknown:
            errors.append('%s引用了记录表中不存在的 ID：%s' % (axis, ', '.join(unknown)))
        types = {i: log[i] for i in ids if i in log}
        cited_inference = [i for i, t in types.items() if t == '解读']
        if cited_inference:
            errors.append('%s把解读当证据引用：%s' % (axis, ', '.join(cited_inference)))
        if st == '已验证':
            good = [i for i, t in types.items() if t in ALLOWED[axis]]
            if len(set(good)) < 2:
                errors.append('%s判为已验证，但只有 %d 条可计入记录（需≥2，类型限：%s）'
                              % (axis, len(set(good)), '、'.join(ALLOWED[axis])))
        elif st == '部分':
            if not any(t in PARTIAL_TYPES for t in types.values()):
                errors.append('%s判为部分，但没有行为/承诺/具体言语/技术观测类记录' % axis)
        elif st == '被推翻':
            if not any(t in REFUTE_TYPES for t in types.values()):
                errors.append('%s判为被推翻，但没有行为/承诺/技术观测类反证' % axis)

    if retro and verdict == 'Proceed':
        errors.append('回溯复盘不作新决策，不得给出 Proceed')
    if verdict == 'Proceed' and len(status) == 3:
        if status['价值判断'] != '已验证' or status['信任与权限'] != '已验证':
            errors.append('Proceed 要求价值判断与信任与权限均为已验证')
        if status['技术可行'] not in ('已验证', '部分'):
            errors.append('Proceed 要求技术可行为已验证或部分')
    if verdict == 'Proceed' and '被推翻' in status.values():
        errors.append('存在被推翻的轴，不能 Proceed')
    if verdict == 'Iterate' and len(status) == 3 and all(v == '已验证' for v in status.values()):
        warnings.append('三轴均已验证，考虑是否应为 Proceed')
    if verdict:
        for key in NEXT_KEYS[verdict]:
            if field(debrief, key) is None:
                errors.append('结论 %s 须填写“%s”' % (verdict, key))

    if not re.search(r'ask 结果[：:]\s*(部分获批|未获批|获批|待回复)', debrief):
        errors.append('未写 ask 结果（获批 / 部分获批 / 未获批 / 待回复）')

    if brief is not None and not section_filled(debrief, '对照事前登记'):
        errors.append('提供了简报，但复盘“对照事前登记”一节为空')
    if not log:
        warnings.append('记录表中没有解析出 L 编号记录；所有轴最高只能判“部分”且须标仅用户转述')
    return errors, warnings


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('debrief', type=Path)
    p.add_argument('--log', type=Path, required=True, help='现场记录表')
    p.add_argument('--brief', type=Path, help='简报（提供则检查是否对照事前登记）')
    p.add_argument('--retro', action='store_true', help='回溯复盘：记录均为转述，不得已验证或 Proceed')
    p.add_argument('--json', action='store_true')
    a = p.parse_args()
    try:
        debrief = a.debrief.read_text(encoding='utf-8')
        log = parse_log(a.log.read_text(encoding='utf-8'))
        brief = a.brief.read_text(encoding='utf-8') if a.brief else None
    except OSError as e:
        p.error(str(e))
    errors, warnings = check(debrief, log, brief, a.retro)
    if a.json:
        print(json.dumps({'errors': errors, 'warnings': warnings, 'ok': not errors}, ensure_ascii=False, indent=2))
    else:
        for e in errors:
            print('错误：' + e)
        for w in warnings:
            print('警告：' + w)
        print('通过规则检查（不代表记录真实、不代表 Demo 有效）' if not errors else '未通过：%d 个错误' % len(errors))
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
