"""

"""
import collections
import itertools
from collections import defaultdict

from tabulate import tabulate
from lingpy import *
import networkx as nx

import matplotlib.pyplot as plt
from matplotlib.patches import Wedge, Circle, FancyArrowPatch
import cartopy.crs as ccrs
from cldfbench.cli_util import add_catalog_spec

from lexibank_bds import Dataset
import library.map as cfeature
from library.util import flatten

ordercols = [
    'missing',
    'singleton',
    'Sino-Tibetan',
    'Hmong-Mien',
    'Tai-Kadai',
    'Hmong-Mien--Sino-Tibetan',
    'Sino-Tibetan--Tai-Kadai',
    'Hmong-Mien--Tai-Kadai',
    'Hmong-Mien--Sino-Tibetan--Tai-Kadai',
]


def register(parser):
    parser.add_argument('--swadesh100', action='store_true', default=False)
    parser.add_argument('--borrowed', action='store_true', default=False)
    add_catalog_spec(parser, 'concepticon')


def run(args):
    ds = Dataset()
    cldf = ds.cldf_reader()

    concepts = set(r['Concepticon_Gloss'] for r in cldf.iter_rows('ParameterTable'))
    wl = Wordlist('wordlist-borrowings.tsv')
    fname = 'auto'

    swadesh = set(
        c.concepticon_gloss for c in
        args.concepticon.api.conceptlists["Swadesh-1955-100"].concepts.values() if
        c.concepticon_gloss in concepts)

    # basic data for plotting and calculation
    data_crs = ccrs.PlateCarree()

    if args.swadesh100:
        selected_concepts = concepts.intersection(swadesh)
        fname = 'swadesh-100-' + fname
    elif args.borrowed:
        fname = "borrowed-" + fname
        selected_concepts = concepts - swadesh
    else:
        selected_concepts = concepts

    langs = {l.id: l for l in cldf.objects('LanguageTable')}

    G = nx.Graph()
    lats, lons = [], []
    for lang, data in langs.items():
        G.add_node(
            lang,
            family=data.data['Family'],
            subgroup=data.data['SubGroup'],
            latitude=float(data.cldf.latitude),
            longitude=float(data.cldf.longitude),
            name=data.cldf.name
        )
        lats += [float(data.cldf.latitude)]
        lons += [float(data.cldf.longitude)]

    etc, etb = defaultdict(list), defaultdict(list)
    for col, d in [('autoborid', etb), ('autocogid', etc)]:
        for key, forms in itertools.groupby(
                sorted(cldf['FormTable'], key=lambda f: f[col] or ''), lambda f: f[col]):
            d[key] = list(forms)

    #etb = wl.get_etymdict(ref='autoborid')
    #etc = wl.get_etymdict(ref='autocogid')

    for doc, language in langs.items():
        # forms by concept for this doculect:
        concepts = wl.get_dict(col=doc)
        this_family = language.data['Family']
        props = defaultdict(float)
        total = 0
        for concept in selected_concepts:
            prop = []
            # for form in ...
            for idx in concepts.get(concept, []):
                borid, cogid = wl[idx, 'autoborid'], wl[idx, 'autocogid']
                # get the other members of the cognate class and borrowing cluster respectively:
                borids, cogids = [x for x in flatten(etb.get(borid, [])) if
                              wl[x, 'autoborid'] != '0'], [x for x in flatten(
                    etc.get(cogid, [])) if wl[x, 'autocogids'] != '0']
                if len(borids) > 1:
                    families = '--'.join(sorted([k for k in set([wl[idx, 'family'] for idx
                                                             in borids]) if k]))  # != this_family]))
                    prop += [families]
                elif len(cogids) > 1:
                    prop += [this_family]
                else:
                    prop += ['singleton']
            for p in prop:
                props[p] += 1 / len(prop)

            if prop:
                total += 1
            elif not concept in concepts:
                props['missing'] += 1
                total += 1

        for k, v in props.items():
            print('{0:30} | {1:20} | {2:20} | {3:25} | {4:.2f}'.format(
                doc,
                this_family,
                language['SubGroup'],
                k,
                v / total))
            props[k] = v / total
        langs[doc]['props'] = props
        langs[doc]['total'] = total

    table = []
    fig = plt.figure(figsize=[20, 10])
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
    ax.set_extent(
        [
            round(min(lons) - 1, 1),
            round(max(lons) + 1, 1),
            round(min(lats) - 1, 1),
            round(max(lats) + 1, 1)
        ], crs=ccrs.PlateCarree())

    ax.coastlines(resolution='50m')
    # ax.stock_img()
    ax.add_feature(cfeature.LAND)
    ax.add_feature(cfeature.OCEAN)
    # ax.add_feature(cfeature.COASTLINE)
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    ax.add_feature(cfeature.LAKES, alpha=0.5)
    ax.add_feature(cfeature.RIVERS)

    # network
    for node, language in G.nodes(data=True):
        start = 0
        col = [node, language['family'], language['subgroup']]
        circle = Circle(
            [language['longitude'],
            language['latitude']],
            0.26,
            facecolor=pcols[language['family']],
            transform=data_crs,
        )
        ax.add_patch(circle)
        for p in ordercols:
            col += [langs[node]['props'][p]]
            if langs[node]['props'][p] != 0:
                this_prop = 360 * langs[node]['props'][p]
                wedge = Wedge(
                    [
                        language['longitude'],
                        language['latitude'],
                    ],
                    0.25,  # langs[node]['total'] * 0.0005,
                    start,
                    start + this_prop,
                    facecolor=pcols[p],
                    transform=data_crs,
                    zorder=50
                )
                ax.add_patch(wedge)
                start += this_prop

        ax.text(
            language['longitude'] + 0.10,
            language['latitude'] + 0.10,
            node[:10],
            fontsize=6,
            zorder=51
        )
        table += [col]

    ax.plot(1, 1, 'o', color='white', markeredgecolor='black', label='missing')
    ax.plot(1, 1, 'o', color=pcols['singleton'], label='Unique')
    ax.plot(1, 1, 'o', color=pcols['Hmong-Mien'], label='Hmong-Mien')
    ax.plot(1, 1, 'o', color=pcols['Sino-Tibetan'], label='Sino-Tibetan')
    ax.plot(1, 1, 'o', color=pcols['Tai-Kadai'], label='Tai-Kadai')
    ax.plot(1, 1, 'o', color=pcols['Hmong-Mien--Sino-Tibetan'], label='HM/ST')
    ax.plot(1, 1, 'o', color=pcols['Hmong-Mien--Tai-Kadai'], label='HM/TK')
    ax.plot(1, 1, 'o', color=pcols['Sino-Tibetan--Tai-Kadai'], label='ST/TK')
    ax.plot(1, 1, 'o', color=pcols['Hmong-Mien--Sino-Tibetan--Tai-Kadai'], label='Global')

    ax.legend(loc=2)
    plt.savefig(fname + '.pdf', dpi=900)
    plt.close()
    print(tabulate(
        sorted(
            table,
            key=lambda x: (x[1], x[4], x[5], x[6])
        ),
        headers=['doculect', 'family', 'subgroup'] + [
            'Single', 'ST', 'HM', 'TK', 'HM-ST', 'ST-TK', 'HM-TK', 'ALL'],
        tablefmt='pipe', floatfmt='4.2f'))


# colors
pcols = {
    'Hmong-Mien--Sino-Tibetan--Tai-Kadai': 'black',
    'Hmong-Mien': 'Crimson',
    'Sino-Tibetan': 'DodgerBlue',
    'Tai-Kadai': 'Gold',
    'Hmong-Mien--Sino-Tibetan': 'Orchid',
    'Hmong-Mien--Tai-Kadai': 'Orange',
    'Sino-Tibetan--Tai-Kadai': 'Green',
    'singleton': '0.5',
    "missing": "white"
}
families = {
    'Hmong-Mien': 'Crimson',
    'Sino-Tibetan': 'DodgerBlue',
    'Tai-Kadai': 'Gold',
}
