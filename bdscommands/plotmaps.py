"""
Plot cross-family borrowings on a map.
"""
import itertools
import collections

import cartopy.crs as ccrs
import library.map as cfeature
from clldutils.misc import slug
from matplotlib import pyplot as plt

from lexibank_bds import Dataset


def run(args):
    ds = Dataset()
    cldf = ds.cldf_reader()

    languages = collections.OrderedDict([(r.id, r) for r in cldf.objects('LanguageTable')])
    lats = [k.cldf.latitude for k in languages.values()]
    lons = [k.cldf.longitude for k in languages.values()]

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
        plot(borid, forms, languages, lats, lons, present, tokens, ds.dir / 'concepts')


def plot(borid, forms, languages, lats, lons, present, tokens, outdir):
    # colors for transitions
    pcols = {
        'missing': 'white',
        'Hmong-Mien--Sino-Tibetan--Tai-Kadai': 'black',
        'Hmong-Mien': 'Crimson',
        'Sino-Tibetan': 'DodgerBlue',
        'Tai-Kadai': 'Gold',
        'Hmong-Mien--Sino-Tibetan': 'Orchid',
        'Hmong-Mien--Tai-Kadai': 'Orange',
        'Sino-Tibetan--Tai-Kadai': 'Green',
        'singleton': '0.5',
    }
    concept = forms[0]['Parameter_ID']
    current = {f['Language_ID']: f for f in forms}
    hits = {k: concept in present[k] for k in languages}

    print('[i] making map for concept {0}'.format(concept))
    plt.clf()  # ax.add_feature(cfeature.COASTLINE)

    fig = plt.figure(figsize=[20, 10])
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
    ax.set_extent([
        round(min(lons) - 1, 1),
        round(max(lons) + 1, 1),
        round(min(lats) - 1, 1),
        round(max(lats) + 1, 1)
    ], crs=ccrs.PlateCarree())
    ax.coastlines(resolution='50m')
    ax.add_feature(cfeature.LAND)
    ax.add_feature(cfeature.OCEAN)
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    ax.add_feature(cfeature.LAKES, alpha=0.5)
    ax.add_feature(cfeature.RIVERS)
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

        ax.plot(
            lon, lat,
            marker='o',
            color=color,
            markersize=10,
            alpha=0.5,
            zorder=4,
        )
        ax.text(lon - 0.075, lat - 0.075, str(i + 1), fontsize=6, zorder=5)

        if lid in current:
            ax.plot(
                lon, lat,
                marker='o',
                color=pcols[language.data['Family']],
                markersize=15,
                zorder=8
            )
            ax.text(
                lon + 0.05, lat + 0.05,
                text,
                fontsize=10,
                bbox={'fc': 'white', 'boxstyle': 'round',
                      'ec': pcols[language.data['Family']]},
                zorder=10
            )
        else:
            ax.text(
                lon + 0.05, lat + 0.05,
                text,
                fontsize=6,
                bbox={'fc': 'white', 'boxstyle': 'round', 'ec': 'black', 'alpha': 0.5},
                zorder=6
            )

    fname = 'concept-' + slug(concept, lowercase=False) + '-' + str(borid)
    plt.title(fname)
    plt.savefig(str(outdir / '{}.pdf'.format(fname)))
    plt.close()
