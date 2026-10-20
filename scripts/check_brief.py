"""Demo 简报完整性检查：只查结构与规则，不验证 Demo 是否有效或证据是否真实。"""
import argparse
import json
import re
import sys
from pathlib import Path

# (标题关键词, 说明)；关键词在二级标题中匹配
SECTIONS = [
    ('唯一主张', '唯一主张'),
    ('类型', 'Demo 类型与权重'),
    ('观众', '观众与角色'),
    ('最痛', '最痛的一步与基线'),
    ('数据', '数据与案例'),
    ('失败样例', '失败样例'),
    ('预跑', '预跑与披露'),
    ('动手', '让客户动手的环节与兜底'),
    ('边界', '现场可改的边界'),
    ('缺口', '留的缺口'),
    ('ask', '结尾的 ask'),
    ('信号', '成败信号（事前登记）'),
]
DEMO_TYPES = ('发现期', '建立信任期', '上线前评审')
BEHAVIOR_WORDS = ('上传', '批', '引荐', '主动', '自己', '动手', '邀请', '指定', '提出', '开通', '提供')


def split_sections(text):
    secs, cur = {}, None
    for line in text.splitlines():
        m = re.match(r'^##\s+(.*)', line)
        if m:
            cur = m.group(1).strip()
            secs[cur] = []
        elif cur is not None:
            secs[cur].append(line)
    return secs


def unfilled(s):
    s = s.strip().lstrip('-* ').strip()
    if s == '待填':
        return True
    m = re.match(r'^[^：:]*[：:]\s*(.*)$', s)
    return bool(m) and m.group(1).strip() in ('', '待填')


def filled(lines):
    out = []
    for line in lines:
        s = line.strip()
        if not s or s.startswith('>') or s.startswith('<!--') or unfilled(s):
            continue
        out.append(s)
    return out


def value_of(lines, key):
    for line in lines:
        m = re.match(r'^\s*[-*]\s*' + key + r'[^：:]*[：:]\s*(.*)$', line)
        if m:
            return m.group(1).strip()
    return None


def bullets_with(lines, prefix):
    n = []
    for line in lines:
        m = re.match(r'^\s*[-*]\s*' + prefix + r'[^：:]*[：:]\s*(.*)$', line)
        if m and m.group(1).strip() not in ('', '待填'):
            n.append(m.group(1).strip())
    return n


def missing(value):
    return value in (None, '', '待填')


def check(text, allow_synthetic=False):
    errors, warnings = [], []
    secs = split_sections(text)
    found = {}
    for key, label in SECTIONS:
        head = next((h for h in secs if key in h.lower()), None)
        if head is None:
            errors.append('缺少章节：%s' % label)
            continue
        found[key] = secs[head]
        if not filled(secs[head]):
            errors.append('未填写：%s' % label)

    if '唯一主张' in found and missing(value_of(found['唯一主张'], '最简替代方案')):
        warnings.append('未写最简替代方案（规则/原文直出/客户现有方法）及其对照；技术轴无法判断“最简单的办法够不够”')

    if '类型' in found:
        if not re.search(r'Demo 类型[：:]\s*(%s)' % '|'.join(DEMO_TYPES), '\n'.join(found['类型'])):
            errors.append('Demo 类型须为：' + ' / '.join(DEMO_TYPES))

    if '观众' in found:
        if missing(value_of(found['观众'], '使用者')):
            errors.append('观众中未写使用者；使用者缺席时价值轴最多“部分”')
        if missing(value_of(found['观众'], '决策者')):
            warnings.append('观众中未写决策者')

    if '数据' in found:
        src = value_of(found['数据'], '数据来源')
        if missing(src):
            errors.append('未写数据来源')
        elif not re.search('真实脱敏|客户现场自带|合成', src):
            errors.append('数据来源须含：真实脱敏 / 客户现场自带 / 合成')
        elif '合成' in src:
            msg = '数据来源含合成数据：不满足红线一，须标注为低保真预演，不得称为客户数据 Demo'
            (warnings if allow_synthetic else errors).append(msg)
        if missing(value_of(found['数据'], '合规状态')):
            warnings.append('未写数据合规状态（授权人、脱敏、是否出域、留存）')
        if missing(value_of(found['数据'], '为什么不是软柿子')):
            errors.append('未说明为什么不是软柿子（红线二）')
        if missing(value_of(found['数据'], '样本量')):
            warnings.append('未写样本量与难度分层')

    if '失败样例' in found:
        n = len(bullets_with(found['失败样例'], r'F\d*'))
        if n < 2:
            errors.append('失败样例不足 2 个（现有 %d）' % n)

    if 'ask' in found:
        if missing(value_of(found['ask'], 'ask')):
            errors.append('未写具体的 ask')
        if missing(value_of(found['ask'], '过去同类请求')):
            warnings.append('未记录过去同类请求的等待时间，之后无法判断“更快”')

    if '信号' in found:
        ok = bullets_with(found['信号'], '成功信号')
        bad = bullets_with(found['信号'], '失败信号')
        if not ok:
            errors.append('事前登记缺少成功信号')
        if not bad:
            errors.append('事前登记缺少失败信号')
        if ok and not any(w in s for s in ok for w in BEHAVIOR_WORDS):
            warnings.append('成功信号看起来都是言语类；建议写成可观察的行为（启发式检查）')
    return errors, warnings


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('brief', type=Path)
    p.add_argument('--allow-synthetic', action='store_true', help='合成数据降为警告（低保真预演）')
    p.add_argument('--json', action='store_true')
    a = p.parse_args()
    try:
        text = a.brief.read_text(encoding='utf-8')
    except OSError as e:
        p.error(str(e))
    errors, warnings = check(text, a.allow_synthetic)
    if a.json:
        print(json.dumps({'errors': errors, 'warnings': warnings, 'ok': not errors}, ensure_ascii=False, indent=2))
    else:
        for e in errors:
            print('错误：' + e)
        for w in warnings:
            print('警告：' + w)
        print('通过结构检查（不代表 Demo 有效）' if not errors else '未通过：%d 个错误' % len(errors))
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
