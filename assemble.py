from pyedictor import fetch
from lingpy import *
from collections import defaultdict
from tabulate import tabulate
from csvw.dsv import UnicodeDictReader

wl = fetch("seabor", base_url="https://digling.org/edictor/", to_lingpy=True)
wl.output("tsv", filename="../raw/wordlist")

datasets = defaultdict(lambda : defaultdict(list))
langs = defaultdict(lambda : defaultdict(list))
for idx in wl:
    datasets[wl[idx, 'dataset']][wl[idx, 'concept']] += [wl[idx, 'doculect']]
    langs[wl[idx, 'dataset']][wl[idx, 'doculect']] += [wl[idx, 'concept']]

languages = {}
with UnicodeDictReader("languages.tsv", delimiter="\t") as reader:
    for row in reader:
        if row["ID"] in wl.cols:
            try:
                languages[row["ID"]]["Datasets"] += [row["Dataset"]]
            except:
                languages[row["ID"]] = row
                languages[row["ID"]]["Datasets"] = [row["Dataset"]]

tab = []
for dataset in datasets:
    tab += [[dataset, len(datasets[dataset]), len(langs[dataset])]]
print(tabulate(tab))

header = ["ID", "Dataset", "Name", "ChineseName", "Family", "SubGroup",
        "Latitude", "Longitude", "Datasets"]
with open("../etc/languages.tsv", "w") as f:
    f.write("\t".join(header)+"\n")
    for language, row in languages.items():
        f.write("\t".join([[x] for x in header])+"\n")

