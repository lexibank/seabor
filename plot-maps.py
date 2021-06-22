from lingpy import *
from collections import defaultdict
from tabulate import tabulate
import networkx as nx
from itertools import combinations
from sys import argv
from cartopy import *
import cartopy.io.img_tiles as cimgt
import cartopy.crs as ccrs
import library.map as cfeature
from clldutils.misc import slug
from matplotlib import pyplot as plt
from time import sleep
from library.util import pcols, flatten
from csvw.dsv import UnicodeDictReader

languages = {}
with UnicodeDictReader("etc/languages.tsv", delimiter="\t") as reader:
    for row in reader:
        languages[row["ID"]] = row


wl = Wordlist("wordlist-borrowings.tsv")

etd = {k: v for k, v in wl.get_etymdict(ref='autoborid').items() if k not in ['0',
    0]}

# compute missing data
present = {k: set(wl.get_list(col=k, entry='concept')) for k in wl.cols}

# compute latitudes and longitudes for plot 
lats = [float(k['Latitude']) for k in languages.values()]
lons = [float(k['Longitude']) for k in languages.values()]

# get all borids shared across more than one language family
borids = [x for x, idxs in etd.items() if len(
    set([wl[idx, 'family'] for idx in flatten(idxs)])) > 1]

# make a plot for each borid with enough hits in terms of no missing data
for borid in borids:
    idxs = flatten(etd[borid])
    current = [wl[idx, 'doculect'] for idx in idxs]
    concept = wl[idxs[0], 'concept']
    hits = [1 if concept in present[k] else 0 for k in wl.cols]
    print('[i] making map for concept {0}'.format(concept))
    fname = 'concept-'+slug(concept, lowercase=False)+'-'+str(borid)
    plt.clf()        #ax.add_feature(cfeature.COASTLINE)

    fig = plt.figure(figsize=[20, 10])
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
    ax.set_extent([
            round(min(lons)-1, 1), 
            round(max(lons)+1, 1), 
            round(min(lats)-1, 1),
            round(max(lats)+1, 1)
        ], crs=ccrs.PlateCarree())
    ax.coastlines(resolution='50m')
    ax.add_feature(cfeature.LAND)
    ax.add_feature(cfeature.OCEAN)
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    ax.add_feature(cfeature.LAKES, alpha=0.5)
    ax.add_feature(cfeature.RIVERS)
    for i, (lid, language) in enumerate(sorted(
        languages.items(), key=lambda x: x[0])):
        lat, lon = float(language["Latitude"]), float(language["Longitude"])
        if not hits[i]:
            color = 'white'
            text = ''
        elif hits[i] and lid not in current:
            color = pcols[language['Family']]
            idx = wl.get_dict(col=lid).get(concept, [''])[0]
            text = ''.join(''.join([x.split('/')[1] if '/' in x else x for
                x in wl[idx, 'tokens']]))
        else:
            color = pcols[language['Family']]
            text = ''.join([x.split('/')[1] if '/' in x else x for x in
                wl[etd[borid][i][0], 'tokens']])

        ax.plot(
                lon, lat,
                marker='o', 
                color=color,
                markersize=10,
                alpha=0.5,
                zorder=4,
                )
        ax.text(
                lon-0.075, lat-0.075,
                str(i+1),
                fontsize=6,
                zorder=5,
                )

        if lid in current:
            ax.plot(
                    lon, lat,
                    marker='o',
                    color=pcols[language['Family']],
                    markersize=15,
                    zorder=8
                    )
            ax.text(
                    lon+0.05, lat+0.05,
                    text,
                    fontsize=10,
                    bbox={'fc': 'white', 'boxstyle': 'round', 
                        'ec': pcols[language['Family']]},
                    zorder=10
                    )
        else:
            ax.text(
                    lon+0.05, lat+0.05,
                    text,
                    fontsize=6,
                    bbox={'fc': 'white', 'boxstyle': 'round', 
                        'ec': 'black', 'alpha': 0.5},
                    zorder=6
                    )

    
    plt.title(fname)
    #plt.savefig('plots/'+folder+'/'+fname+'.png')
    plt.savefig('concepts/'+fname+'.pdf')
    plt.close()
    print('... done')
    sleep(1)

