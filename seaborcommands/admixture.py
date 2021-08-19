"""
Create admixture plots from the lexical borrowing data.
"""
import itertools
import collections

from cldfbench.cli_util import add_catalog_spec
from clldutils.clilib import Table, add_format

from lexibank_seabor import Dataset

pcols = collections.OrderedDict([
    ('missing', 'white'),
    ('singleton', '0.5'),
    ('Sino-Tibetan', 'DodgerBlue'),
    ('Hmong-Mien', 'Crimson'),
    ('Tai-Kadai', 'Gold'),
    ('Hmong-Mien--Sino-Tibetan', 'Orchid'),
    ('Sino-Tibetan--Tai-Kadai',  'Green'),
    ('Hmong-Mien--Tai-Kadai',    'Orange'),
    ('Hmong-Mien--Sino-Tibetan--Tai-Kadai', 'black'),
])


def register(parser):
    add_format(parser, default='simple')
    parser.add_argument('--swadesh100', action='store_true', default=False)
    parser.add_argument('--borrowed', action='store_true', default=False)
    add_catalog_spec(parser, 'concepticon')


def run(args):
    ds = Dataset()
    cldf = ds.cldf_reader()
    langs = collections.OrderedDict(
        [(r.id, r) for r in cldf.objects('LanguageTable')])

    concepts = collections.OrderedDict(
        [(r['Concepticon_Gloss'], r['ID']) for r in cldf.iter_rows('ParameterTable')])
    fname = 'admixture'

    swadesh = set(
        c.concepticon_gloss for c in
        args.concepticon.api.conceptlists["Swadesh-1955-100"].concepts.values() if
        c.concepticon_gloss in concepts)

    if args.swadesh100:
        selected_concepts = {k: v for k, v in concepts.items() if k in swadesh}
        fname = 'swadesh-100-' + fname
    elif args.borrowed:
        fname = "borrowed-" + fname
        selected_concepts = {k: v for k, v in concepts.items() if k not in swadesh}
    else:
        selected_concepts = concepts

    allforms = collections.OrderedDict([
        (f['ID'], f) for f in
        sorted(cldf['FormTable'], key=lambda f: (f['Language_ID'], f['Parameter_ID']))])

    forms_by_cogid, forms_by_borid = collections.defaultdict(list), collections.defaultdict(list)
    cogid_by_formid, borid_by_formid = {}, {}
    for row in cldf['CognateTable']:
        if row['Cognateset_ID'].startswith('auto-full-'):
            forms_by_cogid[row['Cognateset_ID']].append(allforms[row['Form_ID']])
            cogid_by_formid[row['Form_ID']] = row['Cognateset_ID']

    for row in cldf['BorrowingTable']:
        if row['Xenolog_Cluster_ID'].startswith('auto-'):
            forms_by_borid[row['Xenolog_Cluster_ID']].append(allforms[row['Target_Form_ID']])
            borid_by_formid[row['Target_Form_ID']] = row['Xenolog_Cluster_ID']

    for lid, forms in itertools.groupby(allforms.values(), lambda f: f['Language_ID']):
        language = langs[lid]

        # forms by concept for this doculect:
        concepts = {
            pid: list(ff) for pid, ff in itertools.groupby(forms, lambda f: f['Parameter_ID'])}

        props = collections.defaultdict(float)
        total = 0
        for concept, cid in selected_concepts.items():
            prop = []
            for form in concepts.get(cid, []):
                # get the other members of the cognate class and borrowing cluster respectively:
                borrowing_cluster = forms_by_borid.get(borid_by_formid.get(form['ID']), [])
                cognate_class = forms_by_cogid.get(cogid_by_formid.get(form['ID']), [])

                if len(borrowing_cluster) > 1:
                    families = '--'.join(sorted(k for k in set(
                        langs[f['Language_ID']].data['Family'] for f in borrowing_cluster) if k))  # != this_family]))
                    prop.append(families)
                elif len(cognate_class) > 1:
                    prop.append(language.data['Family'])
                else:
                    prop.append('singleton')

            for p in prop:
                props[p] += 1 / len(prop)

            if prop:
                total += 1
            elif cid not in concepts:
                props['missing'] += 1
                total += 1

        for k in list(props.keys()):
            props[k] = props[k] / total

        language.data['props'] = props
        language.data['total'] = total

    with Table(args, 'doculect', 'family', 'subgroup',
               'Single', 'ST', 'HM', 'TK', 'HM-ST', 'ST-TK', 'HM-TK', 'ALL') as table:
        for lid, language in langs.items():
            row = [lid, language.data['Family'], language.data['SubGroup']]
            for p in pcols:
                row += [language.data['props'][p]]
            table.append(row)

        table.sort(key=lambda x: (x[1], x[4], x[5], x[6]))

