from collections import defaultdict
import html
import networkx as nx
from lingpy import *
from clldutils.path import Path
from pyconcepticon.api import Concepticon
import attr

def librarypath(*comps):
    return Path(__file__).parent.parent.joinpath(*comps).as_posix()


def write_gml(graph, fn):
    with open(fn, 'w') as f:
        f.write('\n'.join(html.unescape(line) for line in nx.generate_gml(graph)))


def flatten(values):
    return [x[0] for x in values if x]


def score_pairs(pair1, pair2, struc1, struc2, weights=None, scorer=None, gop=-2):
    struc1 = class2tokens(struc1, pair1)
    struc2 = class2tokens(struc2, pair2)
    weights = weights or {
            'i': 4,
            'm': 1,
            'n': 3,
            'c': 2,
            't': 1,
            'M': 1,
            '+': 0,
            'N': 1
            }
    scorer = scorer or rc('sca').scorer
    scoresA, scoresB, scoresAB = [], [], []
    for a, sa, b, sb in zip(pair1, struc1, pair2, struc2):
        if not '-' in (a, b):
            scoresAB += [scorer[a, b] * weights[sa]]
            scoresA += [scorer[a, a] * weights[sa]]
            scoresB += [scorer[b, b] * weights[sb]]
        elif a == '-':
            scoresAB += [gop * weights[sb]]
            scoresB += [scorer[b, b] * weights[sb]]
        elif b == '-':
            scoresAB += [gop * weights[sa]]
            scoresA += [scorer[a, a] * weights[sa]]
    #print(sum(scoresA), scoresA)
    #print(sum(scoresB), scoresB)
    #print(sum(scoresAB), scoresAB)
    try: 
        score = 2 * (sum(scoresAB)) / (sum(scoresA)+sum(scoresB))
    except:
        score = 0
        print(pair1, pair2, struc1, struc2, scoresAB, scoresA, scoresB)
        input()
    return 1 - score


doculects = ['BiaoMin', 'CentralGuizhouChuanqiandian', 'Changsha', 'Chengdu',
        'Chuanqiandian', 'DahuaYantan', 'Dongnu', 'DuAnBaiwang',
        'EasternBahen', 'EasternLuobuohe', 'EasternQiandong', 'EasternXiangxi',
        'GangbeiZhongli', 'Guangzhou', 'Guilin', 'Guiyang', 'Haikou',
        'Jiongnai', 'KimMun', 'Kunming', 'LuzhaiLuzhai', 'MashanBaishan',
        'Meixian', 'Mien', 'Nanning', 'NortheastYunnanChuanqiandian',
        'NorthernQiandong', 'Numao', 'Nunu', 'Pandong', 
        'RenliEasternSandong', 'She', 'ShuigenCentralSandong',
        'SouthernGuizhouChuanqiandian', 'SouthernQiandong', 'Tuoluo',
        'WesternBaheng', 'WesternLuobuohe', 'WesternXiangxi', 'Wuhan',
        'WuxuanHuangmao', 'Xianggang', 'XiangzhouYunjiang', 'XinfengSonaga',
        'XingbinQianjiang', 'Yangjiang', 'Younuo', 'ZaoMin']

# colors for transitions
pcols = {
        'missing': 'white',
        'Hmong-Mien--Sino-Tibetan--Tai-Kadai': 'black',
        'Hmong-Mien': 'Crimson',
        'Sino-Tibetan': 'DodgerBlue',
        'Tai-Kadai': 'Gold',
        'Hmong-Mien--Sino-Tibetan': 'Orchid',
        'Hmong-Mien--Tai-Kadai':    'Orange',
        'Sino-Tibetan--Tai-Kadai':  'Green',
        'singleton': '0.5',
        }

