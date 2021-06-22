from pyconcepticon import Concepticon
from tabulate import tabulate
from lingpy import Wordlist
import random
from tqdm import tqdm as pb

def get_distribution(wordlist, selected_concepts, B, C, charts):
    """
    Function identifies shared borrowings and cognates per language for a given selection of concepts.
    """
    L = {d: [0 for i in range(len(charts))] for d in wordlist.cols}
    for d in wordlist.cols:
        family = familyD[d]
        concepts = wordlist.get_dict(col=d)
        for concept in selected_concepts:
            vals = []
            for idx in concepts.get(concept, []):
                borid, cogid = wordlist[idx, "autoborid"], wordlist[idx, "autocogid"]
                if borid in B:
                    val = "--".join([
                        x for x in B[borid].split('--') if x != family])
                elif cogid in C:
                    val = C[cogid]
                vals += [val]
            if not vals:
                L[d][charts.index("missing")] += 1
            else:
                for v in set(vals):
                    L[d][charts.index(v)] += vals.count(v) / len(vals)
    table = []
    for language, vals in L.items():
        table += [[language, familyD[language]] + vals]
    return table

# load data and swadesh lists
wl = Wordlist("wordlist-borrowings.tsv")
familyD = {wl[idx, "doculect"]: wl[idx, "family"] for idx in wl}
swadesh = [c.concepticon_gloss for c in
        Concepticon().conceptlists["Swadesh-1955-100"].concepts.values() if
        c.concepticon_gloss in wl.rows]
no_swadesh = [c for c in wl.rows if c not in swadesh]
jakarta = [c.concepticon_gloss for c in
        Concepticon().conceptlists["Tadmor-2009-100"].concepts.values() if
        c.concepticon_gloss in wl.rows]
no_jakarta = [c for c in wl.rows if c not in jakarta]
print("[i] loaded languages")

# load etymological data
etdb = wl.get_etymdict(ref="autoborid")
B = {}
for borid, vals in etdb.items():
    if borid != "0":
        idxs = []
        for v in vals:
            if v:
                idxs += v
        families = [wl[idx, "family"] for idx in idxs]
        if len(set(families)) == 3:
            B[borid] = "global"
        else:
            famstring = "--".join(sorted(set(families)))
            B[borid] = famstring

C = {}
for cogid, vals in wl.get_etymdict(ref="autocogid").items():
    idxs = []
    for v in vals:
        if v:
            idxs += v
    langs = [wl[idx, "doculect"] for idx in idxs]
    if len(set(langs)) > 1:
        families = [wl[idx, "family"] for idx in idxs]
        famstring = "--".join(sorted(set(families)))
        assert not "--" in famstring
        C[cogid] = famstring 
    else:
        C[cogid] = "singleton"
print("[i] loaded etymological data")

pies = ["missing", "singleton", 
        "Hmong-Mien", "Sino-Tibetan",
        "Tai-Kadai", "global"]

swad_table = get_distribution(wl, swadesh, B, C, pies)
no_swad_table = get_distribution(wl, no_swadesh, B, C, pies)
all_table = get_distribution(wl, wl.rows, B, C, pies)
jak_table = get_distribution(wl, jakarta, B, C, pies)
no_jak_table = get_distribution(wl, no_jakarta, B, C, pies)
print("[i] loaded tabular data")

inherited = []
for name, table, lst in [
        ("Swadesh", swad_table, swadesh), 
        ("No Swadesh", no_swad_table, no_swadesh), 
        ("Jakarta", jak_table, jakarta), 
        ("No Jakarta", no_jak_table, no_jakarta), 
        ("Full", all_table, wl.rows)]:
    sums = []
    for i, row in enumerate(table):
        if row[1] == "Hmong-Mien":
            sums += [(row[3]+row[4])/sum(row[3:])]
        if row[1] == "Sino-Tibetan":
            sums += [(row[3]+row[5])/sum(row[3:])]
        if row[1] == "Tai-Kadai":
            sums += [(row[3]+row[6])/sum(row[3:])]
    inherited += [[name, sum(sums)/len(sums), len(lst)]]
print(tabulate(inherited, floatfmt=".2f"))

samples = [0 for d in wl.cols]
sig = 1000
scores = []
for name, lst in [("Swadesh", swadesh), ("Jakarta", jakarta)]:
    counts = 0
    for i in pb(range(sig), desc="randomize"):
        new_concepts = random.sample(
                wl.rows, len(lst))
        table_A = get_distribution(wl, new_concepts, B, C, pies)
        table_B = get_distribution(wl, [c for c in wl.rows if c not in
            new_concepts], B, C, pies)
        sums_A, sums_B = [], []
        for i, row in enumerate(table_A):
            if row[1] == "Hmong-Mien":
                sums_A += [(row[3]+row[4])/sum(row[3:])]
            if row[1] == "Sino-Tibetan":
                sums_A += [(row[3]+row[5])/sum(row[3:])]
            if row[1] == "Tai-Kadai":
                sums_A += [(row[3]+row[6])/sum(row[3:])]
        for i, row in enumerate(table_B):
            if row[1] == "Hmong-Mien":
                sums_B += [(row[3]+row[4])/sum(row[3:])]
            if row[1] == "Sino-Tibetan":
                sums_B += [(row[3]+row[5])/sum(row[3:])]
            if row[1] == "Tai-Kadai":
                sums_B += [(row[3]+row[6])/sum(row[3:])]
        if sum(sums_A)/len(sums_A) - sum(sums_B)/len(sums_B) >= inherited[0][1]-inherited[1][1]:
            counts += 1
    scores += [[name, counts/sig]]
print(tabulate(scores, floatfmt=".4f"))

#tab = []
#for i, row in enumerate(base_table):
#    tab += [[row[0], row[1]]+[x/wl.height for x in row[2:]]+[propb[i], props[i], out[i] / sig]]
#print(tabulate(sorted(tab, key=lambda x: (x[1], x[0])), headers=[
#    "language", 
#    "family", "missing", "singleton", "HM", "ST", "TK", "all",
#    "proportion", "prop/swadesh", "significance"], 
#    floatfmt=".2f"))
#print(len([x for x in tab if x[-1] <= 0.05]))
#
#
#
#b_table = get_distribution(wl, wl.rows, B, C)
#sums = []
#for i, row in enumerate(b_table):
#    if row[1] == "Hmong-Mien":
#        sums += [(row[3]+row[4])/sum(row[3:])]
#    if row[1] == "Sino-Tibetan":
#        sums += [(row[3]+row[5])/sum(row[3:])]
#    if row[1] == "Tai-Kadai":
#        sums += [(row[3]+row[6])/sum(row[3:])]
#print(sum(sums)/len(sums))
#
#print(outs/sig)

