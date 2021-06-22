from lingpy import *
from glob import glob
from cartopy import *
import cartopy.io.img_tiles as cimgt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
#import library.data
import library.map as lmap
from library.util import pcols

from csvw.dsv import UnicodeDictReader

languages = {}
with UnicodeDictReader("etc/languages.tsv", delimiter="\t") as reader:
    for row in reader:
        languages[row["ID"]] = row

filename='small-map'
markersize = 14
textsize = 8


lats, lons = [], []
for l, row in languages.items():
    lats += [float(row["Latitude"])]
    lons += [float(row["Longitude"])]
print(lats, lons)

fig = plt.figure(figsize=[20, 10])

print('figed')
ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
print('axed', min(lons), min(lats))
ax.set_extent(
        [
            round(min(lons)-1, 1), 
            round(max(lons)+1, 1), 
            round(min(lats)-1, 1),
            round(max(lats)+1, 1)
            ], crs=ccrs.PlateCarree())
print('exed')
#stamen_terrain = cimgt.Stamen('terrain-background')
#ax.add_image(stamen_terrain, 5)

ax.coastlines(resolution='50m')
#ax.stock_img(resolution='50m')
ax.add_feature(lmap.LAND)
#ax.add_feature(cfeature.NaturalEarthFeature('physical','admin_0_boundary_lines_land',
#    '50m'))
ax.add_feature(lmap.OCEAN)
ax.add_feature(lmap.COASTLINE)
ax.add_feature(lmap.BORDERS, linestyle=':')
ax.add_feature(lmap.LAKES, alpha=0.5)
ax.add_feature(lmap.RIVERS)

for i, (lid, language) in enumerate(sorted(languages.items())):
    print(i+1, lid, language['Name'])
    scaler = 1
    ax.plot(
            float(language['Longitude']), 
            float(language['Latitude']), 
            marker='o', 
            color=pcols.get(language['Family'], 'black'),
            markersize=markersize * scaler,
            )
    if textsize > -1:
        ax.text(
                float(language['Longitude'])+0.05,
                float(language['Latitude'])+0.05,
                lid[:10],
                fontsize=textsize
                )
for fam in sorted(["Sino-Tibetan", "Hmong-Mien", "Tai-Kadai"]):
    col = pcols[fam]
    ax.plot(0, 0, 'o', markersize=10, color=col, label=fam)
ax.legend(loc=3)
plt.savefig(filename+'.pdf', dpi=900)

