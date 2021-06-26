"""
Plot location of varieties on a map. See Figure 1.
"""
import webbrowser
import collections

from PIL import Image
import cartopy.feature as cfeature
import cartopy.crs as ccrs
from matplotlib import pyplot as plt

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


class Figure:
    def __init__(self, args, fname, languages, title=None):
        lats = [k.cldf.latitude for k in languages.values()]
        lons = [k.cldf.longitude for k in languages.values()]
        self.format = getattr(args, 'fig_format', 'pdf')
        self.fname = fname.parent / '{}.{}'.format(fname.name, self.format)
        self.title = title or self.fname.stem
        self.extent = [
            round(min(lons) - 1, 1),
            round(max(lons) + 1, 1),
            round(min(lats) - 1, 1),
            round(max(lats) + 1, 1)
        ]
        self.ax = None

    def __enter__(self):
        plt.clf()
        fig = plt.figure(figsize=[20, 10])
        ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
        ax.set_extent(self.extent, crs=ccrs.PlateCarree())
        ax.coastlines(resolution='50m')
        ax.add_feature(cfeature.LAND)
        ax.add_feature(cfeature.OCEAN)
        ax.add_feature(cfeature.BORDERS, linestyle=':')
        ax.add_feature(cfeature.LAKES, alpha=0.5)
        ax.add_feature(cfeature.RIVERS)
        self.ax = ax
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        plt.title(self.title)
        if self.format == 'jpg':
            mplfname = self.fname.parent / '{}.png'.format(self.fname.stem)
            plt.savefig(str(mplfname))
            img = Image.open(str(mplfname)).convert('RGB')
            img.save(str(self.fname), optimize=True, quality=95)
            mplfname.unlink()
        else:
            plt.savefig(str(self.fname))
        plt.close()

    def plot_language(
            self, language, text=None, text_offest=(-0.075, -0.075), plot_kw=None, text_kw=None):
        lat, lon = float(language.cldf.latitude), float(language.cldf.longitude)

        kw = dict(color=pcols[language.data['Family']], markersize=15, zorder=4, marker='o')
        if plot_kw:
            kw.update(plot_kw)
        self.ax.plot(lon, lat, **kw)

        kw = dict(fontsize=10, zorder=5)
        if text_kw:
            kw.update(text_kw)
        self.ax.text(lon + text_offest[0], lat + text_offest[1], text or language.cldf.name, **kw)

    def plot_text(self, language, text, text_offest=(-0.075, -0.075), **kw):
        lat, lon = float(language.cldf.latitude), float(language.cldf.longitude)
        self.ax.text(lon + text_offest[0], lat + text_offest[1], text, **kw)


def add_figformat(parser):
    parser.add_argument(
        '--fig-format',
        default='pdf',
        const='pdf',
        nargs='?',
        choices=('svg', 'png', 'pdf', 'jpg'),
        help='Output format for figures')


def register(parser):
    add_figformat(parser)


def run(args):
    ds = Dataset()
    cldf = ds.cldf_reader()
    languages = collections.OrderedDict([(r.id, r) for r in cldf.objects('LanguageTable')])

    with Figure(args, ds.dir / "plots" / 'languages_map', languages, title='Languages in the sample') as fig:
        for i, (lid, language) in enumerate(sorted(languages.items(), key=lambda x: x[0])):
            fig.plot_language(language)

    webbrowser.open(fig.fname.as_uri())
