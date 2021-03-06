import random
import pathlib
import collections

import attr
from lingpy import Wordlist, evaluate
from collabutils.edictor import fetch
from pylexibank import Dataset as BaseDataset, Language, Lexeme, Cognate
from clldutils.misc import slug
from clldutils.markup import Table
from pycldf import Sources
import lingrex.cognates
import lingrex.borrowing


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


@attr.s
class MultiCognate(Cognate):
    """
    This dataset provides three kinds of cognacy judgements, distinguished by
    Cognate_Detection_Method:

    - expert: Cognate classes assigned by an expert
    - lingrex.borrowing.internal_cognates: Partial cognates computed with the lingrex package.
    - lingrex.cognates.common_morpheme_cognates: Cognates derived from partial cognacy relations
      computed with the lingrex package.
    """


class Dataset(BaseDataset):
    dir = pathlib.Path(__file__).parent
    id = "seabor"
    language_class = Doculect
    lexeme_class = Word
    cognate_class = MultiCognate

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
        random.seed(int(input('Random seed [int]: ') or 1234))
        args.writer.add_sources()
        t = args.writer.cldf.add_component(
            'BorrowingTable',
            {
                'name': 'Xenolog_Cluster_ID',
                'dc:description': 'Identifier for a Xenolog cluster',
            },
            {
                'name': 'Borrowing_Detection_Method',
                'dc:description': 'Method used to assign Xenolog clusters',
                'datatype': {
                    'base': 'string', 'format': 'expert|lingrex.borrowing.external_cognates'}
            }
        )
        t.common_props['dc:description'] = """\
This dataset provides two kinds of borrowing judgements distinguished by
Borrowing_Detection_Method. Borrowings are clustered into "Xenolog clusters",
i.e. sets of words which are not entirely related by common descent, but also
by lateral transfer.

- expert: Xenolog clusters assigned by an export
- lingrex.borrowing.external_cognates: Xenolog clusters are computed with the
  lingrex package"""

        c2cid = {c.gloss: c.id for c in args.concepticon.api.conceptsets.values()}

        wl = self.wl()
        # we represent non-borrowed words in their own cluster in our
        # user-defined "borid"
        clusterid = max([int(x) for x in wl.get_etymdict("uborid")])+1
        wl.add_entries("userborid", "uborid", lambda x: int(x))
        for idx in wl:
            if wl[idx, "userborid"] == 0:
                wl[idx, "userborid"] = clusterid
                clusterid += 1
        # we compute baselines for lumper and splitter
        wl.add_entries("splitid", {idx: idx for idx in wl}, lambda x: x)
        wl.add_entries("lumpid", "concept", lambda x: x)
        wl.add_entries("lumpfamid", "concept,family", lambda x, y: x[y[0]]+"-"+x[y[1]])

        # See paper, section "4 Results" and section "3.2 Methods".
        # Detect partial cognates:
        lingrex.borrowing.internal_cognates(
            wl,
            runs=100 if args.dev else 10000,
            ref="autocogids",
            partial=True,
            method="lexstat",
            threshold=0.50,
            cluster_method="infomap")
        # Convert partial cognates into full cognates:
        lingrex.cognates.common_morpheme_cognates(
            wl,
            ref="autocogid",
            cognates="autocogids",
            morphemes="automorphemes")
        # Detect cross-family shallow cognates:
        lingrex.borrowing.external_cognates(
            wl,
            cognates="autocogid",
            ref="autoborid",
            threshold=0.35)
        wl.output("tsv", filename="temp", ignore="all")
        # renumber wordlist to place 0 into their own cluster
        clusterid = max(wl.get_etymdict("autoborid"))+1
        for idx in wl:
            if wl[idx, "autoborid"] == 0:
                wl[idx, "autoborid"] = clusterid
                clusterid += 1

                
        # add a combined score

        # Output the evaluation:
        p1, r1, f1 = evaluate.acd.bcubes(wl, "ucogid", "autocogid", pprint=False)
        p2, r2, f2 = evaluate.acd.bcubes(wl, "userborid", "autoborid", pprint=False)
        p3, r3, f3 = evaluate.acd.bcubes(wl, "ucogid", "lumpfamid",
                pprint=False)
        p4, r4, f4 = evaluate.acd.bcubes(wl, "userborid", "lumpid",
                pprint=False)
        p5, r5, f5 = evaluate.acd.bcubes(wl, "ucogid", "splitid", pprint=False)
        p6, r6, f6 = evaluate.acd.bcubes(wl, "userborid", "splitid",
                pprint=False)

        print('')
        with Table("method", "precision", "recall", "f-score",
                tablefmt="simple", floatfmt=".4f") as tab:
            tab.append(["automated cognate detection", p1, r1, f1])
            tab.append(["automated borrowing detection", p2, r2, f2])
            tab.append(["lumper bl for cognate detection", p3, r3, f3])
            tab.append(["lumper bl for borrowing detection", p4, r4, f4])
            tab.append(["splitter bl for cognate detection", p5, r5, f5])
            tab.append(["splitter bl for borrowing detection", p6, r6, f6])

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
                    Concepticon_ID=c2cid[row['concept'].upper()],
                    Name=row['concept_in_source'])
                concepts.add(row['concept'])
            lex = args.writer.add_form_with_segments(
                ID='{}-{}'.format(row['dataset'], row['lexibank_id']),
                Language_ID=row['doculect'],
                Parameter_ID=slug(row['concept']),
                Value=row['value'],
                Form=row['form'],
                Segments=row['tokens'],
                ID_In_Source=row["lexibank_id"],
                Source=row["dataset"],
                Prosodic_String=row["structure"]
            )
            if row['ucogid'] and row['ucogid'] not in ('0', 0):
                args.writer.add_cognate(
                    lexeme=lex,
                    Cognateset_ID='expert-{}'.format(row['ucogid']),
                    Cognate_Detection_Method='expert')
            if row['autocogid'] and row['autocogid'] not in ('0', 0):
                args.writer.add_cognate(
                    lexeme=lex,
                    Cognateset_ID='auto-full-{}'.format(row['autocogid']),
                    Cognate_Detection_Method='lingrex.cognates.common_morpheme_cognates')
            if row['autocogids'] and row['autocogids'] not in ('0', 0):
                for cogid in row['autocogids']:
                    args.writer.add_cognate(
                        lexeme=lex,
                        Cognateset_ID='auto-partial-{}'.format(cogid),
                        Cognate_Detection_Method='lingrex.borrowing.internal_cognates')
            if row['uborid'] and row['uborid'] not in ('0', 0):
                args.writer.objects['BorrowingTable'].append(dict(
                    ID='expert-' + lex['ID'],
                    Target_Form_ID=lex['ID'],
                    Xenolog_Cluster_ID='expert-{}'.format(row['uborid']),
                    Comment=row['source'],
                ))
            if row['autoborid'] and row['autoborid'] not in ('0', 0):
                args.writer.objects['BorrowingTable'].append(dict(
                    ID='auto-' + lex['ID'],
                    Target_Form_ID=lex['ID'],
                    Xenolog_Cluster_ID='auto-{}'.format(row['autoborid']),
                ))
