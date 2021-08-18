"""
Compare the alternative method for borrowing detection by Hantgan et al. 2020.
"""
from lingpy import *
from lexibank_seabor import Dataset as sb
from lingpy.evaluate.acd import bcubes
from clldutils.clilib import Table, add_format
from lingrex import cognates, borrowing
from tabulate import tabulate


def register(parser):
    add_format(parser, default='simple')
    parser.add_argument(
            "--lexstat",
            help="use lexstat algorithm",
            action="store_true",
            default=False)
    parser.add_argument(
            "--lingrex",
            help="use lingrex algorithm",
            action="store_true",
            default=False)
    parser.add_argument(
            "--partial",
            help="use partial lexstat algorithm for cognate detection",
            action="store_true",
            default=False)





def run(args):
    if args.lexstat:
        method = "lexstat"
    else:
        method = "sca"
    try:
        from igraph import Graph
        cluster_method = "infomap"
    except:
        cluster_method="upgma"

    if args.lingrex: 
        table = []
        wl = Wordlist(str(sb().raw_dir / "seabor.sqlite3"))
        for i, t in enumerate([0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7]):
            ref = "cog-{0}".format(i)
            borrowing.internal_cognates(
                    wl,
                    partial=args.partial
                    runs=10000,
                    ref=ref,
                    method="lexstat",
                    threshold=t,
                    cluster_method=cluster_method)
            if args.partial:
                cognates.common_morpheme_cognates(
                        wl,
                        ref=ref+"id",
                        cognates=ref,
                        morphemes=ref+"-morphemes")
            else:
                wl.add_entries(ref+"id", ref, lambda x: x)

            # renumber wordlist to place 0 into their own cluster
            clusterid = max(wl.get_etymdict(ref+"id"))+1
            for idx in wl:
                if wl[idx, ref+"id"] == 0:
                    wl[idx, ref+"id"] = clusterid
                    clusterid += 1

            p1, r1, f1 = evaluate.acd.bcubes(wl, "ucogid", ref+"id", pprint=False)
            table += [["cognates", t, 0, p1, r1, f1]]
            for j, t2 in enumerate([0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5]):
                borrowing.external_cognates(
                        wl,
                        cognates=ref+"id",
                        ref=ref+"{0}-borid".format(j),
                        threshold=t2)
                p2, r2, f2 = evaluate.acd.bcubes(
                        wl, "uborid", ref+"{0}-borid".format(j), pprint=False)
                table += [[t, t2, p1, r1, f1, p2, r2, f2]]
        with Table(
                args, "Threshold A", "Threshold B", "P1", "R1", "F1", "P2", "R2", "F2") as tab:
            for row in table:
                tab.append(row)
    else:
        table = []
        lex = LexStat(str(sb().raw_dir / "seabor.sqlite3"))
        if method == "lexstat":
            lex.get_scorer(runs=10000)

        for i, t in enumerate([0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.85, 0.9]):
            args.log.info("loaded data")
            lex.cluster(method=method, threshold=t, ref="scallid_{0}".format(i))
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
        with Table(args, "Threshold", "P1", "R1", "F1", "P2", "R2", "F2") as tab:
            for row in table:
                tab.append(row)
    
