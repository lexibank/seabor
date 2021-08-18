"""
Compare the alternative method for borrowing detection by Hantgan et al. 2020.
"""
import random
from lingpy import *
from lingpy.compare.partial import Partial
from lexibank_seabor import Dataset as sb
from lingpy.evaluate.acd import bcubes
from clldutils.clilib import Table, add_format
from lingrex import cognates, borrowing
from tabulate import tabulate
from matplotlib import pyplot as plt



def register(parser):
    add_format(parser, default='simple')
    parser.add_argument(
            "--lexstat",
            help="use lexstat algorithm",
            action="store_true",
            default=False)
    parser.add_argument(
            "--partial",
            help="use partial lexstat algorithm for cognate detection",
            action="store_true",
            default=False)


def run(args):
    random.seed(int(input('Random seed [int]: ') or 1234))
    if args.lexstat:
        method = "lexstat"
    else:
        method = "sca"
    try:
        from igraph import Graph
        cluster_method = "infomap"
    except:
        cluster_method = "upgma"
        args.log.warning("Using UPGMA as cluster method")

    table = []
    if args.partial:
        lex = Partial(str(sb().raw_dir / "seabor.sqlite3"))
        args.log.info("loading partial object")
    else:
        lex = LexStat(str(sb().raw_dir / "seabor.sqlite3"))
        args.log.info("loading lexstat object")

    # renumber borrowings !
    clusterid = max([int(x) for x in lex.get_etymdict("uborid")])+1
    for idx in lex:
        if lex[idx, "uborid"] == "0":
            lex[idx, "uborid"] = clusterid
            clusterid += 1

    # add lumper and splitter baseline

    if method == "lexstat":
        if not args.partial:
            lex.get_scorer(runs=10000)
        else:
            lex.get_partial_scorer(runs=10000)

    for i, t in enumerate([0.05 * j for j in range(1, 20)]):
        if args.partial:
            lex.partial_cluster(
                    method=method, threshold=t,
                    ref="scallids_{0}".format(i),
                    cluster_method=cluster_method)
            cognates.common_morpheme_cognates(
                lex,
                ref="scallid_{0}".format(i),
                cognates="scallids_{0}".format(i),
                morphemes="automorphemes_{0}".format(i))
        else:
            lex.cluster(method=method, threshold=t,
                    ref="scallid_{0}".format(i), cluster_method=cluster_method)
        lex.add_entries("sca_{0}".format(i), "scallid_{0},family".format(i), lambda x, y:
                str(x[y[0]])+"-"+x[y[1]])
        lex.renumber("sca_{0}".format(i))
        etd = lex.get_etymdict(ref="scallid_{0}".format(i))
        nulls = {}
        clusterid = max(etd)+1
        for cogid, vals in etd.items():
            idxs = []
            for v in vals:
                if v:
                    idxs += v
            famis = [lex[idx, 'family'] for idx in idxs]
            if len(set(famis)) == 1:
                for idx in idxs:
                    lex[idx, 'scallid_{0}'.format(i)] = clusterid
                    clusterid += 1

        p1, r1, f1 = bcubes(lex, "ucogid", "sca_{0}id".format(i), pprint=False)
        p2, r2, f2 = bcubes(lex, "uborid", "scallid_{0}".format(i), pprint=False)
        table += [[t, p1, r1, f1, p2, r2, f2]]
    with Table(
            args, "Threshold", "P1", "R1", "F1", "P2", "R2", "F2",
            floatfmt=".4f") as tab:
        for row in table:
            tab.append(row)

    fig = plt.Figure()
    plt.plot(
            1, table[0][3], 'o', color="Crimson", 
            label="family-internal cognates")
    plt.plot(
            1, table[0][-1], 'o', color="CornFlowerBlue",
            label="family-external xenologs")

    for i, row in enumerate(table[1:]):
        plt.plot(i+2, row[3], 'o', color="Crimson")
        plt.plot(i+2, row[-1], 'o', color="CornFlowerBlue")
    plt.xticks(
            list(
                range(1, 20)
                ), ["{0:.2f}".format(i*0.05) for i in range(1, 20)], rotation=90)
    plt.yticks([i*0.1 for i in range(3, 10)])
    plt.ylim(0.3, 1.0)
    plt.xlabel("cognate detection thresholds")
    plt.ylabel("B-cubed F-scores")
    plt.title("Cognate vs. Xenolog Detection ({0}, {1})".format(
        "LexStat" if args.lexstat else "SCA",
        "Full Cognates" if not args.partial else "Partial Cognates"))
    plt.legend(loc=4)
    plt.savefig("plots/full_comparison-{0}-{1}.pdf".format(
        "lexstat" if args.lexstat else "sca",
        "full" if not args.partial else "partial"
        ))

    
