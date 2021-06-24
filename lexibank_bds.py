import pathlib
from collections import defaultdict

import attr
from lingpy import Wordlist
from collabutils.edictor import fetch
from pylexibank import Dataset as BaseDataset, Language, Lexeme
from clldutils.misc import slug
from clldutils.markup import Table


@attr.s
class Word(Lexeme):
    autoborid = attr.ib(
        default=None,
        converter=lambda s: None if s in ('0', 0) else int(s),
        metadata={'dc:description': 'Automatically inferred borrowing Identifier'}
    )
    autocogid = attr.ib(
        default=None,
        metadata={'dc:description': 'Automatically inferred cognate class'}
    )
    autocogids = attr.ib(
        default=None,
        metadata={'dc:description': 'Automatically inferred cognate classes'}
    )


@attr.s
class Doculect(Language):
    Dataset = attr.ib(default=None)
    ChineseName = attr.ib(default=None)
    Family = attr.ib(default=None)
    SubGroup = attr.ib(default=None)
    Datasets = attr.ib(default=None)


class Dataset(BaseDataset):
    dir = pathlib.Path(__file__).parent
    id = "borrowing-detection-study"
    language_class = Doculect
    lexeme_class = Word

    _wlname = 'seabor.sqlite3'

    def wl(self):
        return Wordlist(str(self.raw_dir / self._wlname))

    def cldf_specs(self):  # A dataset must declare all CLDF sets it creates.
        return super().cldf_specs()

    def cmd_download(self, args):
        fetch("seabor", outdir=self.raw_dir, remote_dbase=self._wlname, base_url="https://digling.org/edictor/")
        wl = self.wl()
        datasets = defaultdict(lambda: defaultdict(list))
        langs = defaultdict(lambda: defaultdict(list))
        for idx in wl:
            datasets[wl[idx, 'dataset']][wl[idx, 'concept']] += [wl[idx, 'doculect']]
            langs[wl[idx, 'dataset']][wl[idx, 'doculect']] += [wl[idx, 'concept']]

        with Table('ID', 'Source', 'Language Family', 'Varieties', 'Concepts', tablefmt='simple') as t:
            for dataset in datasets:
                t.append([dataset, '', '', len(langs[dataset]), len(datasets[dataset])])

    def cmd_makecldf(self, args):
        from lingrex.cognates import common_morpheme_cognates
        from lingrex.borrowing import internal_cognates, external_cognates

        wl = self.wl()
        # See paper, section "4 Results"!
        internal_cognates(
            wl,
            runs=10000,
            ref="autocogids",
            partial=True,
            method="lexstat",
            threshold=0.55,
            cluster_method="infomap")
        common_morpheme_cognates(
            wl, ref="autocogid", cognates="autocogids",
            morphemes="automorphemes")
        external_cognates(wl, cognates="autocogid", ref="autoborid", threshold=0.3)

        #
        # FIXME: print Table 2 from the paper!
        #

        wl = Wordlist('wordlist-borrowings.tsv')
        args.writer.add_languages()

        concepts = set()
        header = [k for k, _ in sorted(wl.header.items(), key=lambda i: i[1])]
        for index in wl:
            row = dict(zip(header, wl[index]))
            if row['concept'] not in concepts:
                args.writer.add_concept(
                    ID=slug(row['concept']),
                    Concepticon_Gloss=row['concept'].upper(),
                    Name=row['concept_in_source'])
                concepts.add(row['concept'])
            args.writer.add_form_with_segments(
                ID='{}-{}'.format(row['dataset'], row['lexibank_id']),
                Language_ID=row['doculect'],
                Parameter_ID=slug(row['concept']),
                Value=row['value'],
                Form=row['form'],
                Segments=row['tokens'],
                autoborid=row['autoborid'],
                autocogid=row['autocogid'],
                autocogids=row['autocogids'],
            )

        # autocogids, autocogid, autoborid.
        # ALIGNMENT>------
        # BORID>--
        # CHINESE_GLOSS>--  --> parameters
        # CLASSES>
        # COGID>--
        # COGIDS>-
        # CONCEPT>
        # CONCEPT_IN_SOURCE>------ --> parameters
        # CROSSIDS>-------
        # DATASET> --> ID (+ LEXIBANK_ID) (also: Source!)
        # DOCULECT>-------languges['ID']
        # DUPLICATES>-----
        # FAMILY>-  -> languages
        # FORM>---
        # IPA>----
        # LEXIBANK_ID>---- --> ID (see above)
        # MORPHEMES>------
        # NUMBERS>
        # PATTERNS>-------
        # PROSTRINGS>-----
        # SONARS>-
        # STRUCTURE>------
        # SUBGROUP>------- --> languages
        # TOKENS>-
        # UBORID>-
        # UCOGID>-
        # UCOGIDS>
        # VALUE>--
        # WEIGHTS>
        # VISITED>
        # NOTE>---
        # SOURCE>-
        # AUTOCOGIDS>-----
        # AUTOCOGID>------
        # AUTOMORPHEMES>--
        # AUTOBORID
