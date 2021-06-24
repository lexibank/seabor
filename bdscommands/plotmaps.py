"""
Plot cross-family borrowings on a map.
"""
import itertools
import collections

from clldutils.misc import slug

from lexibank_bds import Dataset
from .plotlanguages import pcols, Figure


def run(args):
    ds = Dataset()
    cldf = ds.cldf_reader()
    languages = collections.OrderedDict([(r.id, r) for r in cldf.objects('LanguageTable')])

    borids = collections.defaultdict(list)
    present = collections.defaultdict(set)
    tokens = collections.defaultdict(dict)

    for borid, forms in itertools.groupby(
            sorted(cldf['FormTable'], key=lambda f: f['autoborid'] or ''), lambda f: f['autoborid']):
        forms = [f for f in forms if f['Form']]
        for form in forms:
            tokens[form['Language_ID']][form['Parameter_ID']] = form['Segments']
        if borid:
            for form in forms:
                present[form['Language_ID']].add(form['Parameter_ID'])
            if len(set(languages[f['Language_ID']].data['Family'] for f in forms)) > 1:
                borids[borid] = list(forms)
    for borid, forms in borids.items():
        plot(borid, forms, languages, present, tokens, ds.dir / 'concepts')


def plot(borid, forms, languages, present, tokens, outdir):
    concept = forms[0]['Parameter_ID']
    current = {f['Language_ID']: f for f in forms}
    hits = {k: concept in present[k] for k in languages}

    print('[i] making map for concept {0}'.format(concept))

    fname = outdir / 'concept-{}-{}.pdf'.format(slug(concept, lowercase=False), str(borid))
    with Figure(fname, languages) as fig:
        for i, (lid, language) in enumerate(sorted(languages.items(), key=lambda x: x[0])):
            lat, lon = float(language.cldf.latitude), float(language.cldf.longitude)
            if not hits[lid]:
                color = 'white'
                text = ''
            elif hits[lid] and lid not in current:
                color = pcols[language.data['Family']]
                text = ''.join(''.join([x.split('/')[1] if '/' in x else x for
                                    x in tokens[lid][concept]]))
            else:
                color = pcols[language.data['Family']]
                text = ''.join([x.split('/')[1] if '/' in x else x for x in
                            current[lid]['Segments']])

            fig.plot_language(
                language,
                str(i + 1),
                plot_kw=dict(color=color, markersize=10, alpha=0.5, zorder=4),
                text_kw=dict(fontsize=6, zorder=5))

            if lid in current:
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
                fig.ax.text(
                    lon + 0.05, lat + 0.05,
                    text,
                    fontsize=6,
                    bbox={'fc': 'white', 'boxstyle': 'round', 'ec': 'black', 'alpha': 0.5},
                    zorder=6
                )
        return fig.fname
