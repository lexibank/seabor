"""
Plot cross-family borrowings on a map.
"""
import itertools
import collections

from clldutils.misc import slug

from lexibank_seabor import Dataset
from .plotlanguages import pcols, Figure


def run(args):
    ds = Dataset()
    cldf = ds.cldf_reader()
    languages = collections.OrderedDict([(r.id, r) for r in cldf.objects('LanguageTable')])

    borids = collections.defaultdict(list)
    present = collections.defaultdict(set)
    tokens = collections.defaultdict(lambda: collections.defaultdict(list))

    for borid, forms in itertools.groupby(
            sorted(cldf['FormTable'], key=lambda f: f['autoborid'] or ''), lambda f: f['autoborid']):
        forms = [f for f in forms if f['Form']]
        for form in forms:
            tokens[form['Language_ID']][form['Parameter_ID']].append(form['Segments'])
            present[form['Language_ID']].add(form['Parameter_ID'])

        if borid and len(set(languages[f['Language_ID']].data['Family'] for f in forms)) > 1:
            borids[borid] = list(forms)

    for lid in list(tokens.keys()):
        # If a variety has counterparts for a concept that are not member of a borrowing cluster,
        # we display the longest counterpart on the map for comparison.
        tokens[lid] = {k: sorted(v, key=lambda s: len(s))[-1] for k, v in tokens[lid].items()}

    for borid, forms in borids.items():
        plot(
            forms[0]['Parameter_ID'], borid, forms, languages, present, tokens, ds.dir / 'concepts')
        break


def plot(concept, borid, forms, languages, present, tokens, outdir):
    borrowing_cluster = {f['Language_ID']: f for f in forms}
    has_concept = {k: concept in present[k] for k in languages}

    print('[i] making map for concept {}-{}'.format(concept, borid))

    with Figure(
            outdir / 'concept-{}-{}.pdf'.format(slug(concept, lowercase=False), borid), languages
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
