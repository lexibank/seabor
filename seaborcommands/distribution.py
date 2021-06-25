"""
Calculate statistics for the likelihood of obtaining differences between Swadesh and other concepts.
"""
import random
import itertools
import collections

from pylexibank import progressbar as pb
from clldutils.clilib import Table, add_format
from cldfbench.cli_util import add_catalog_spec

from lexibank_seabor import Dataset


def register(parser):
    add_format(parser, default='simple')
    parser.add_argument('--conceptlist', action='store', default=None)
    add_catalog_spec(parser, 'concepticon')
    parser.add_argument('--runs', action="store", type=int, default=1000)
    parser.add_argument(
        '--seed',
        type=lambda s: random.seed(int(s)),
        default=None)


class Scorer:
    def __init__(self, allforms, forms_by_borid, borid_by_formid, concepts):
        self.forms_by_language = [
            list(forms) for _, forms in itertools.groupby(allforms, lambda f: f['Language_ID'])]
        self.f_by_b = forms_by_borid
        self.b_by_f = borid_by_formid
        self.concepts = concepts

    def __call__(self, subset):
        scores = []
        for forms in self.forms_by_language:
            # forms by concept for this doculect:
            concepts_ = {
                pid: list(ff) for pid, ff in itertools.groupby(forms, lambda f: f['Parameter_ID'])}

            props = collections.defaultdict(float)
            total = 0
            for concept in subset:
                cid = self.concepts[concept]
                prop = []
                for form in concepts_.get(cid, []):
                    borrowing_cluster = self.f_by_b.get(self.b_by_f.get(form['ID']), [])
                    if len(borrowing_cluster) > 1:
                        prop.append("1")
                    else:
                        prop.append("0")

                for p in prop:
                    props[p] += 1 / len(prop)
                if prop:
                    total += 1
            for k in list(props.keys()):
                props[k] = props[k] / total
            scores += [props["0"]]
        return sum(scores)/len(scores)


def run(args):
    ds = Dataset()
    cldf = ds.cldf_reader()
    concepts = collections.OrderedDict(
        [(r['Concepticon_Gloss'], r['ID']) for r in cldf.iter_rows('ParameterTable')])
    all_concepts = set(concepts)
    args.log.info("loaded dataset")
        
    allforms = collections.OrderedDict([
        (f['ID'], f) for f in
        sorted(cldf['FormTable'], key=lambda f: (f['Language_ID'], f['Parameter_ID']))])

    forms_by_borid = collections.defaultdict(list)
    borid_by_formid = {}

    for row in cldf['BorrowingTable']:
        if row['Xenolog_Cluster_ID'].startswith('auto-'):
            forms_by_borid[row['Xenolog_Cluster_ID']].append(allforms[row['Target_Form_ID']])
            borid_by_formid[row['Target_Form_ID']] = row['Xenolog_Cluster_ID']

    scorer = Scorer(allforms.values(), forms_by_borid, borid_by_formid, concepts)
    with Table(args, "Conceptlist", "Proportion of Non-Borrowed Items", "Number of Items") as tab:
        if not args.conceptlist:
            tab.append(["All items", scorer(concepts), len(concepts)])
            return

        subset = set(c.concepticon_gloss for c in
            args.concepticon.api.conceptlists[args.conceptlist].concepts.values()
            if c.concepticon_gloss in concepts)
        otherset = all_concepts.difference(subset)
        sA, sB = (scorer(subset), scorer(otherset))

        tab.append([args.conceptlist, sA, len(subset)])
        tab.append(["!= "+args.conceptlist, sB, len(otherset)])

    dAB = sA - sB
    hits = 0
    for _ in pb(range(args.runs), desc="permutation test"):
        new_subset = random.sample(list(concepts), len(subset))
        new_otherset = all_concepts.difference(new_subset)
        new_diff = scorer(new_subset) - scorer(new_otherset)
        if new_diff >= dAB:
            hits += 1
    print("Significance: {0:.4f} ({1:.4f})".format(hits / args.runs, dAB))
