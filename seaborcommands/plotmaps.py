"""
Plot cross-family borrowings on a map.
"""
import itertools
import webbrowser
import collections

from clldutils.misc import slug

from lexibank_seabor import Dataset
from .plotlanguages import pcols, Figure, add_figformat


def register(parser):
    add_figformat(parser)
    parser.add_argument("--concepts", action="store", nargs="+", default="and")


def run(args):
    ds = Dataset()
    cldf = ds.cldf_reader()
    languages = collections.OrderedDict([(r.id, r) for r in cldf.objects('LanguageTable')])

    present = collections.defaultdict(set)
    tokens = collections.defaultdict(lambda: collections.defaultdict(list))

    allforms = {r['id']: r for r in cldf.iter_rows('FormTable', 'id')}
    for form in allforms.values():
        tokens[form['Language_ID']][form['Parameter_ID']].append(form['Segments'])
        present[form['Language_ID']].add(form['Parameter_ID'])

    borids = collections.defaultdict(list)
    for borid, forms in itertools.groupby(
        sorted(cldf['BorrowingTable'], key=lambda f: f['Xenolog_Cluster_ID']),
        lambda f: f['Xenolog_Cluster_ID']
    ):
        if borid.startswith('auto'):
            borid = borid.split('-')[-1]
            forms = [allforms[f['Target_Form_ID']] for f in forms]
            if len(set(languages[f['Language_ID']].data['Family'] for f in forms)) > 1:
                borids[borid] = forms

    for lid in list(tokens.keys()):
        # If a variety has counterparts for a concept that are not member of a borrowing cluster,
        # we display the longest counterpart on the map for comparison.
        tokens[lid] = {k: sorted(v, key=lambda s: len(s))[-1] for k, v in tokens[lid].items()}

    for borid, forms in borids.items():
        if forms[0]["Parameter_ID"] in args.concepts:
            fname = plot(
                args, forms[0]['Parameter_ID'], borid, forms, languages, present, tokens,
                ds.dir / 'plots')
            args.log.info('Plot saved to {}'.format(fname))
            webbrowser.open(fname.as_uri())


def plot(args, concept, borid, forms, languages, present, tokens, outdir):
    borrowing_cluster = {f['Language_ID']: f for f in forms}
    has_concept = {k: concept in present[k] for k in languages}

    with Figure(
            args, outdir / 'concept-{}-{}'.format(slug(concept, lowercase=False), borid), languages
    ) as fig:
        for i, (lid, language) in enumerate(sorted(languages.items(), key=lambda x: x[0])):
            color, text = 'white', ''  # The default for languages with no words for a concept.
            if has_concept[lid]:
                form = borrowing_cluster[lid]['Segments'] if lid in borrowing_cluster \
                    else tokens[lid][concept]
                color = pcols[language.data['Family']]
                text = ''.join(''.join([x.split('/')[1] if '/' in x else x for x in form]))

            fig.plot_language(
                language,
                str(i + 1),
                plot_kw=dict(color=color, markersize=10, alpha=0.5, zorder=4),
                text_kw=dict(fontsize=6, zorder=5))

            if lid in borrowing_cluster:
                fig.plot_language(
                    language,
                    text,
                    text_offest=(0.05, 0.05),
                    plot_kw=dict(markersize=15, zorder=8),
                    text_kw=dict(
                        fontsize=10,
                        zorder=10,
                        bbox={
                            'fc': 'white',
                            'boxstyle': 'round',
                            'ec': pcols[language.data['Family']]},
                    ))
            else:
                fig.plot_text(
                    language,
                    text,
                    text_offest=(0.05, 0.05),
                    fontsize=6,
                    bbox={'fc': 'white', 'boxstyle': 'round', 'ec': 'black', 'alpha': 0.5},
                    zorder=6
                )
        return fig.fname
