import pathlib
import collections

import attr
from lingpy import Wordlist, evaluate
from collabutils.edictor import fetch
from pylexibank import Dataset as BaseDataset, Language, Lexeme
from clldutils.misc import slug
from clldutils.markup import Table
from pycldf import Sources
from lingrex.cognates import common_morpheme_cognates
from lingrex.borrowing import internal_cognates, external_cognates


def ref(src):
    persons = src.entry.persons.get('author') or src.entry.persons.get('editor', [])
    s = ' '.join(persons[0].last_names)
    if len(persons) == 2:
        s += ' and {}'.format(' '.join(persons[1].last_names))
    elif len(persons) > 2:
        s += ' et al.'
    return s.replace('{', '').replace('}', '') + ' ({})'.format(src['year'])


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
    Xenolog_Cluster = attr.ib(
        default=None,
        converter=lambda s: None if s in ('0', 0) else int(s),
        metadata={'dc:description': 'Etymologically related words with a known borrowing history.'}
    )
    Prosodic_String=attr.ib(
        default=None,
        metadata={"dc:description": "Prosodic string representation."}
    )
    ID_In_Source=attr.ib(
        default=None,
        metadata={"dc:description": "Identifier in the lexibank dataset."}
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
    id = "seabor"
    language_class = Doculect
    lexeme_class = Word

    _wlname = 'seabor.sqlite3'

    def wl(self):
        return Wordlist(str(self.raw_dir / self._wlname))

    def cmd_download(self, args):
        fetch("seabor",
              outdir=self.raw_dir,
              remote_dbase=self._wlname,
              base_url="https://digling.org/edictor/")
        sources = Sources.from_file(self.raw_dir / 'sources.bib')
        wl = self.wl()
        datasets = collections.defaultdict(lambda: collections.defaultdict(list))
        langs = collections.defaultdict(lambda: collections.defaultdict(list))
        for idx in wl:
            datasets[wl[idx, 'dataset']][wl[idx, 'concept']] += [wl[idx, 'doculect']]
            langs[wl[idx, 'dataset']][wl[idx, 'doculect']] += [wl[idx, 'concept']]

        with Table('ID', 'Source', 'Varieties', 'Concepts', tablefmt='simple') as t:
            for dataset in datasets:
                t.append([
                    dataset, ref(sources[dataset]), len(langs[dataset]), len(datasets[dataset])])

    def cmd_makecldf(self, args):
        args.writer.add_sources()

        wl = self.wl()
        # See paper, section "4 Results" and section "3.2 Methods".
        # Detect partial cognates:
        internal_cognates(
            wl,
            runs=10000,
            ref="autocogids",
            partial=True,
            method="lexstat",
            threshold=0.55,
            cluster_method="infomap")
        # Convert partial cognates into full cognates:
        common_morpheme_cognates(
            wl,
            ref="autocogid",
            cognates="autocogids",
            morphemes="automorphemes")
        # Detect cross-family shallow cognates:
        external_cognates(
            wl,
            cognates="autocogid",
            ref="autoborid",
            threshold=0.3)

        # Output the evaluation:
        p1, r1, f1 = evaluate.acd.bcubes(wl, "ucogid", "autocogid", pprint=False)
        p2, r2, f2 = evaluate.acd.bcubes(wl, "uborid", "autoborid", pprint=False)
        print('')
        with Table("method", "precision", "recall", "f-score",
                tablefmt="simple", floatfmt=".4f") as tab:
            tab.append(["automated cognate detection", p1, r1, f1])
            tab.append(["automated borrowing detection", p2, r2, f2])
        print('')

        # Write the wordlist to a proper CLDF dataset:
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
                ID_In_Source=row["lexibank_id"],
                Cognacy=row["ucogid"],
                Xenolog_Cluster=row["uborid"],
                Source=row["dataset"],
                Prosodic_String=row["structure"]
            )
