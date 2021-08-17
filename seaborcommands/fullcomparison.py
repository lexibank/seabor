"""
Compare the alternative method for borrowing detection by Hantgan et al. 2020.
"""
from lingpy import *
from lexibank_seabor import Dataset as sb
from lingpy.evaluate.acd import bcubes
from clldutils.clilib import Table, add_format


def register(parser):
    add_format(parser, default='simple')
    parser.add_argument(
            "--lexstat",
            help="use lexstat algorithm",
            action="store_true",
            default=False)



def run(args):
    
    table = []
    lex = LexStat(str(sb().raw_dir / "seabor.sqlite3"))
    if args.lexstat:
        method = "lexstat"
        lex.get_scorer(method="lexstat", runs=1000)
    else:
        method = "sca"

    for i, t in enumerate([0.5, 0.55, 0.6, 0.65, 0.7]):
        args.log.info("loaded data")
        lex.cluster(method=method, threshold=t, ref="scallid_{0}".format(i))
        lex.add_entries("sca_{0}".format(i), "scallid_{0},family".format(i), lambda x, y:
                str(x[y[0]])+"-"+x[y[1]])
        lex.renumber("sca_{0}".format(i))
        etd = lex.get_etymdict(ref="scallid_{0}".format(i))
        nulls = {}
        for cogid, vals in etd.items():
            idxs = []
            for v in vals:
                if v:
                    idxs += v
            famis = [lex[idx, 'family'] for idx in idxs]
            if len(set(famis)) == 1:
                for idx in idxs:
                    lex[idx, 'scallid_{0}'.format(i)] = 0

        p1, r1, f1 = bcubes(lex, "ucogid", "sca_{0}id".format(i), pprint=False)
        p2, r2, f2 = bcubes(lex, "uborid", "scallid_{0}".format(i), pprint=False)
        table += [[t, p1, r1, f1, p2, r2, f2]]
    with Table(args, "Threshold", "P1", "R1", "F1", "P2", "R2", "F2") as tab:
        for row in table:
            tab.append(row)
    
