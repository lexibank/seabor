"""

"""
import itertools
import webbrowser
import collections

from matplotlib.patches import Wedge, Circle
import cartopy.crs as ccrs
from cldfbench.cli_util import add_catalog_spec
from clldutils.clilib import Table, add_format

from lexibank_seabor import Dataset

from .plotlanguages import pcols, Figure


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
    fname = 'auto'

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

    allforms = sorted(cldf['FormTable'], key=lambda f: (f['Language_ID'], f['Parameter_ID']))

    forms_by_cogid, forms_by_borid = collections.defaultdict(list), collections.defaultdict(list)
    for row, d in [('autoborid', forms_by_borid), ('autocogid', forms_by_cogid)]:
        for form in allforms:
            if form[row]:
                d[form[row]].append(form)

    for lid, forms in itertools.groupby(allforms, lambda f: f['Language_ID']):
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
                borrowing_cluster = forms_by_borid.get(form['autoborid'], [])
                cognate_class = forms_by_cogid.get(form['autocogid'], [])

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

    with Figure(ds.cldf_dir / '{}.pdf'.format(fname), langs) as fig,\
            Table(args, 'doculect', 'family', 'subgroup',
                  'Single', 'ST', 'HM', 'TK', 'HM-ST', 'ST-TK', 'HM-TK', 'ALL') as table:
        for lid, language in langs.items():
            coords = (float(language.cldf.longitude), float(language.cldf.latitude))
            start = 0
            row = [lid, language.data['Family'], language.data['SubGroup']]
            circle = Circle(
                coords, 0.26, facecolor=pcols[language.data['Family']], transform=ccrs.PlateCarree())
            fig.ax.add_patch(circle)
            for p in pcols:
                row += [language.data['props'][p]]
                if language.data['props'][p] != 0:
                    this_prop = 360 * language.data['props'][p]
                    wedge = Wedge(
                        coords,
                        0.25,  # langs[node]['total'] * 0.0005,
                        start,
                        start + this_prop,
                        facecolor=pcols[p],
                        transform=ccrs.PlateCarree(),
                        zorder=50
                    )
                    fig.ax.add_patch(wedge)
                    start += this_prop

            fig.ax.text(coords[0] + 0.10, coords[1] + 0.10, lid[:10], fontsize=6, zorder=51)
            table.append(row)

        fig.ax.plot(1, 1, 'o', color='white', markeredgecolor='black', label='missing')
        fig.ax.plot(1, 1, 'o', color=pcols['singleton'], label='Unique')
        fig.ax.plot(1, 1, 'o', color=pcols['Hmong-Mien'], label='Hmong-Mien')
        fig.ax.plot(1, 1, 'o', color=pcols['Sino-Tibetan'], label='Sino-Tibetan')
        fig.ax.plot(1, 1, 'o', color=pcols['Tai-Kadai'], label='Tai-Kadai')
        fig.ax.plot(1, 1, 'o', color=pcols['Hmong-Mien--Sino-Tibetan'], label='HM/ST')
        fig.ax.plot(1, 1, 'o', color=pcols['Hmong-Mien--Tai-Kadai'], label='HM/TK')
        fig.ax.plot(1, 1, 'o', color=pcols['Sino-Tibetan--Tai-Kadai'], label='ST/TK')
        fig.ax.plot(1, 1, 'o', color=pcols['Hmong-Mien--Sino-Tibetan--Tai-Kadai'], label='Global')

        fig.ax.legend(loc=2)
        table.sort(key=lambda x: (x[1], x[4], x[5], x[6]))

    webbrowser.open(fig.fname.as_uri())
