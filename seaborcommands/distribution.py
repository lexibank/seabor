"""
Calculate statistics for the likelihood of obtaining differences between Swadesh and other concepts.
"""
from pyconcepticon import Concepticon
from tabulate import tabulate
import random
from pylexibank import progressbar as pb
from clldutils.clilib import Table, add_format
from lexibank_seabor import Dataset
import itertools
from cldfbench.cli_util import add_catalog_spec
import collections



def register(parser):
    add_format(parser, default='simple')
    parser.add_argument('--conceptlist', action='store', default=None)
    add_catalog_spec(parser, 'concepticon')
    parser.add_argument('--runs', action="store", type=int, default=1000)


def get_distribution(wordlist, selected_concepts, B, C, charts):
    """
    Function identifies shared borrowings and cognates per language for a given selection of concepts.
    """
    L = {d: [0 for i in range(len(charts))] for d in wordlist.cols}
    for d in wordlist.cols:
        family = familyD[d]
        concepts = wordlist.get_dict(col=d)
        for concept in selected_concepts:
            vals = []
            for idx in concepts.get(concept, []):
                borid, cogid = wordlist[idx, "autoborid"], wordlist[idx, "autocogid"]
                if borid in B:
                    val = "--".join([
                        x for x in B[borid].split('--') if x != family])
                elif cogid in C:
                    val = C[cogid]
                vals += [val]
            if not vals:
                L[d][charts.index("missing")] += 1
            else:
                for v in set(vals):
                    L[d][charts.index(v)] += vals.count(v) / len(vals)
    table = []
    for language, vals in L.items():
        table += [[language, familyD[language]] + vals]
    return table


def run(args):
    
    def get_scores(subset, allforms, form_by_borid, concepts):
        scores = []
        for lid, forms in itertools.groupby(allforms, lambda f: f['Language_ID']):
            language = langs[lid]

            # forms by concept for this doculect:
            concepts_ = {
                pid: list(ff) for pid, ff in itertools.groupby(forms, lambda f: f['Parameter_ID'])}

            props = collections.defaultdict(float)
            total = 0
            for concept in subset:
                cid = concepts[concept]
                prop = []
                for form in concepts_.get(cid, []):
                    borrowing_cluster = forms_by_borid.get(form['autoborid'], [])
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
    
    ds = Dataset()
    cldf = ds.cldf_reader()
    langs = collections.OrderedDict(
        [(r.id, r) for r in cldf.objects('LanguageTable')])
    concepts = collections.OrderedDict(
        [(r['Concepticon_Gloss'], r['ID']) for r in cldf.iter_rows('ParameterTable')])
    all_concepts = set(concepts)
    args.log.info("loaded dataset")
        
    allforms = sorted(cldf['FormTable'], key=lambda f: (f['Language_ID'], f['Parameter_ID']))
    forms_by_borid = collections.defaultdict(list)
    for form in allforms:
        if form["autoborid"]:
            forms_by_borid[form["autoborid"]].append(form)
    
    if not args.conceptlist:
        with Table(args, "Conceptlist", "Proportion of Non-Borrowed Items", 
                "Number of Items") as tab:
            tab.append(["All items", get_scores(concepts, allforms,
                forms_by_borid, concepts)])
        return
    subset = set(c.concepticon_gloss for c in
            args.concepticon.api.conceptlists[args.conceptlist].concepts.values()
            if c.concepticon_gloss in concepts)
    otherset = all_concepts.difference(subset)
    sA, sB = (
            get_scores(subset, allforms, forms_by_borid, concepts),
            get_scores(otherset, allforms, forms_by_borid, concepts)
            )
    with Table(args, "Conceptlist", "Proportion of Non-Borrowed Items", 
            "Number of Items") as tab:
        tab.append([args.conceptlist, sA, len(subset)])
        tab.append(["!= "+args.conceptlist, sB, len(otherset)])
    dAB = sA - sB
    hits = 0
    for i in pb(range(args.runs), desc="permutation test"):
        new_subset = random.sample(list(concepts), len(subset))
        new_otherset = all_concepts.difference(new_subset)
        new_diff = get_scores(new_subset, allforms, forms_by_borid, concepts)-\
                get_scores(new_otherset, allforms, forms_by_borid, concepts)
        if new_diff >= dAB:
            hits += 1
    print("Significance: {0:.4f} ({1:.4f})".format(hits/args.runs, dAB))

