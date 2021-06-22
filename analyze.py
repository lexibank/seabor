from lingrex.cognates import common_morpheme_cognates
from lingrex.borrowing import internal_cognates, external_cognates
from lingpy import Wordlist

wl = Wordlist("wordlist.tsv")
internal_cognates(wl, runs=10000, ref="autocogids", partial=True,
        method="lexstat", threshold=0.55, cluster_method="infomap")
common_morpheme_cognates(wl, ref="autocogid", cognates="autocogids",
        morphemes="automorphemes")
external_cognates(wl, cognates="autocogid", ref="autoborid")
wl.output("tsv", filename="wordlist-borrowings", ignore="all", prettify=False)
