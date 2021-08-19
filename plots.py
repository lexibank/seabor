"""
Plot cross-family borrowings on a map.
"""
import itertools
import collections
import urllib.request

from clldutils import svg
from csvw.dsv import reader
from matplotlib.patches import Wedge, Circle
from cartopy import crs as ccrs
import yattag

from cldfviz.map import MarkerFactory
from cldfviz.map.leaflet import LeafletMarkerSpec
from cldfviz.map.mpl import MPLMarkerSpec
from cldfviz.colormap import hextriplet

SWADESH = "https://raw.githubusercontent.com/concepticon/concepticon-data/v2.5.0/concepticondata/" \
          "conceptlists/Swadesh-1955-100.tsv"
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
hex_color = lambda color: hextriplet(color.replace('0.5', 'grey').lower())


class Map(MarkerFactory):
    def __init__(self, cldf, args, *custom):
        MarkerFactory.__init__(self, cldf, args)
        self.languages = collections.OrderedDict([(r.id, r) for r in cldf.objects('LanguageTable')])

        # We can plot two kinds of maps:
        if len(custom) == 2:
            # We plot a xenolog cluster
            pid, cluster_id = custom
            self.data = self.data_cluster(self.languages, cldf, pid, cluster_id)
            self.plot = 'cluster'
        else:
            # We plot "admixture" pie charts
            self.data = self.data_admixture(self.languages, cldf, custom[0] if custom else None)
            self.plot = 'admixture'

    def __call__(self, map, language, *_):
        if self.plot == 'cluster':
            return self.plot_cluster(map, language)
        else:
            return self.plot_admixture(map, language)

    def legend(self, fig, parameters, colormaps):
        if self.plot == 'admixture':
            if self.args.format == 'html':
                doc, tag, text = yattag.Doc().tagtext()

                with tag('table', klass="legend"):
                    for name, color in pcols.items():
                        with tag('tr'):
                            with tag('th'):
                                doc.stag(
                                    'img',
                                    src=svg.data_url(
                                        svg.icon(hex_color(color).replace('#', 'c'))),
                                    width="{}".format(min([20, self.args.markersize * 2])))
                            with tag('th', style="text-align: left;"):
                                text(name.replace('singleton', 'Unique'))
                fig.legend = doc.getvalue()
                return
            fig.ax.plot(1, 1, 'o', color='white', markeredgecolor='black', label='missing')
            fig.ax.plot(1, 1, 'o', color=pcols['singleton'], label='Unique')
            fig.ax.plot(1, 1, 'o', color=pcols['Hmong-Mien'], label='Hmong-Mien')
            fig.ax.plot(1, 1, 'o', color=pcols['Sino-Tibetan'], label='Sino-Tibetan')
            fig.ax.plot(1, 1, 'o', color=pcols['Tai-Kadai'], label='Tai-Kadai')
            fig.ax.plot(1, 1, 'o', color=pcols['Hmong-Mien--Sino-Tibetan'], label='HM/ST')
            fig.ax.plot(1, 1, 'o', color=pcols['Hmong-Mien--Tai-Kadai'], label='HM/TK')
            fig.ax.plot(1, 1, 'o', color=pcols['Sino-Tibetan--Tai-Kadai'], label='ST/TK')
            fig.ax.plot(
                1, 1, 'o', color=pcols['Hmong-Mien--Sino-Tibetan--Tai-Kadai'], label='Global')
            fig.ax.legend(loc=2)

    @staticmethod
    def data_admixture(langs, cldf, setid):
        concepts = collections.OrderedDict(
            [(r['Concepticon_Gloss'], r['ID']) for r in cldf.iter_rows('ParameterTable')])
        swadesh = set(
            c['CONCEPTICON_GLOSS'] for c in
            reader(
                urllib.request.urlopen(SWADESH).read().decode('utf8').split('\n'),
                dicts=True,
                delimiter='\t')
            if c['CONCEPTICON_GLOSS'] in concepts)

        if setid == 'swadesh':
            selected_concepts = {k: v for k, v in concepts.items() if k in swadesh}
        elif setid == 'borrowed':
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
                            langs[f['Language_ID']].data['Family'] for f in borrowing_cluster) if
                                                    k))  # != this_family]))
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

    @staticmethod
    def data_cluster(languages, cldf, pid, cluster_id):
        present = collections.defaultdict(set)
        tokens = collections.defaultdict(lambda: collections.defaultdict(list))

        allforms = {r['id']: r for r in cldf.iter_rows('FormTable', 'id')}
        for form in allforms.values():
            tokens[form['Language_ID']][form['Parameter_ID']].append(form['Segments'])
            present[form['Language_ID']].add(form['Parameter_ID'])

        borid_forms = None
        for borid, forms in itertools.groupby(
            sorted(cldf['BorrowingTable'], key=lambda f: f['Xenolog_Cluster_ID']),
            lambda f: f['Xenolog_Cluster_ID']
        ):
            if borid == 'auto-{}'.format(cluster_id):
                forms = [allforms[f['Target_Form_ID']] for f in forms]
                if len(set(languages[f['Language_ID']].data['Family'] for f in forms)) > 1:
                    borid_forms = forms

        for lid in list(tokens.keys()):
            # If a variety has counterparts for a concept that are not member of a borrowing cluster,
            # we display the longest counterpart on the map for comparison.
            tokens[lid] = {k: sorted(v, key=lambda s: len(s))[-1] for k, v in tokens[lid].items()}

        return (pid, cluster_id, borid_forms, present, tokens)

    def plot_cluster(self, map, language):
        languages = self.languages
        concept, borid, forms, present, tokens = self.data
        borrowing_cluster = {f['Language_ID']: f for f in forms}
        has_concept = {k: concept in present[k] for k in languages}
        color, text = 'white', language.id  # The default for languages with no words for a concept.

        lid = language.id
        if has_concept[lid]:
            form = borrowing_cluster[lid]['Segments'] if lid in borrowing_cluster \
                else tokens[lid][concept]
            color = pcols[languages[lid].data['Family']]
            text = ''.join(''.join([x.split('/')[1] if '/' in x else x for x in form]))
        color = color.lower()

        if lid in borrowing_cluster:
            if self.args.format == 'html':
                return LeafletMarkerSpec(
                    icon=svg.data_url(svg.icon(hextriplet(color).replace('#', 'c'), opacity=1)),
                    markersize=self.args.markersize + 3,
                    tooltip=text,
                    tooltip_class='tt-big-font',
                    css='div.tt-big-font {font-size: bigger !important; opacity: 90% !important;}',
                )
            else:
                return MPLMarkerSpec(
                    marker_kw=dict(markersize=15, zorder=8, color=color),
                    text=text,
                    text_offset_x=0.05,
                    text_offset_y=0.05,
                    text_kw=dict(
                    fontsize=10,
                    zorder=10,
                    bbox={'fc': 'white', 'boxstyle': 'round', 'ec': color}),
                )
        else:
            if self.args.format == 'html':
                return LeafletMarkerSpec(
                    icon=svg.data_url(svg.icon(hextriplet(color).replace('#', 'c'), opacity=0.5)),
                    tooltip=text,
                    tooltip_class='tt-small-font',
                    css='div.tt-small-font {font-size: smaller !important; opacity: 50% !important;}',
                    markersize=self.args.markersize if has_concept[lid] else self.args.markersize - 3,
                )
            if has_concept[lid]:
                return MPLMarkerSpec(
                    marker_kw=dict(markersize=10, zorder=2.5, color=color, alpha=0.7),
                    text=text,
                    text_offset_x=0.05,
                    text_offset_y=0.05,
                    text_kw=dict(
                        fontsize=6,
                        bbox={'fc': 'white', 'boxstyle': 'round', 'ec': 'black', 'alpha': 0.5},
                        zorder=2.5,
                    )
                )
            else:
                return MPLMarkerSpec(
                    marker_kw=dict(markersize=10, zorder=2.3, color=color, alpha=0.5),
                    text=str(language.id),
                    text_kw=dict(fontsize=6, zorder=5, alpha=0.6))

    def plot_admixture(self, fig, language):
        languages = self.languages
        lid = language.id
        coords = (language.lon, language.lat)
        language = languages[lid]

        if self.args.format == 'html':
            return LeafletMarkerSpec(icon=svg.data_url(svg.pie(
                [language.data['props'][p] for p in pcols],
                [hextriplet(v.lower() if v != '0.5' else 'grey') for v in pcols.values()]
            )))

        start = 0
        if 1:
            row = [lid, language.data['Family'], language.data['SubGroup']]
            circle = Circle(
                coords, 0.26,
                facecolor=pcols[language.data['Family']],
                transform=ccrs.PlateCarree())
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
        return True  # Signal that plotting is done!
