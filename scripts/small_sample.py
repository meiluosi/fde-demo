"""小样本比例的 Wilson 区间。只描述抽样不确定性，不验证样本代表性、判定标准或记录真实性。"""
import argparse
import json
import math
import sys

Z = {0.90: 1.6448536, 0.95: 1.9599640, 0.99: 2.5758293}


def wilson(k, n, conf=0.95):
    if n <= 0 or k < 0 or k > n:
        raise ValueError('需要 n>0 且 0<=k<=n')
    if conf not in Z:
        raise ValueError('conf 只支持 %s' % ', '.join(str(c) for c in Z))
    z = Z[conf]
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--k', type=int, required=True, help='一致/成功的件数')
    p.add_argument('--n', type=int, required=True, help='总件数（分母）')
    p.add_argument('--conf', type=float, default=0.95)
    p.add_argument('--json', action='store_true')
    a = p.parse_args()
    try:
        lo, hi = wilson(a.k, a.n, a.conf)
    except ValueError as e:
        p.error(str(e))
    out = {
        'k': a.k, 'n': a.n, 'point_estimate': a.k / a.n,
        'wilson_interval': [lo, hi], 'confidence': a.conf,
        'suggested_wording': '%d 件中 %d 件' % (a.n, a.k),
        'notes': ['区间只反映抽样不确定性，假设样本可视为随机抽取',
                  '不验证样本代表性、判定标准和记录真实性',
                  '外部引用写“n 件中 k 件”，不要单独写百分比'],
    }
    if a.n < 30:
        out['notes'].append('n<30，小样本：只说明机制与失败模式，不代表总体')
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print('点估计 %.1f%%（%d/%d）；%d%% Wilson 区间 %.1f%%–%.1f%%'
              % (100 * out['point_estimate'], a.k, a.n, round(100 * a.conf), 100 * lo, 100 * hi))
        for n in out['notes']:
            print('提示：' + n)
    sys.exit(0)


if __name__ == '__main__':
    main()
