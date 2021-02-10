import argparse
from pathlib import Path
import logging

import wn


def _download(args):
    if args.index:
        wn.config.load_index(args.index)
    for target in args.target:
        wn.download(target, add=args.add)


def _lexicons(args):
    for lex in wn.lexicons(lang=args.lang, lexicon=args.lexicon):
        print('\t'.join((lex.id, lex.version, f'[{lex.language}]', lex.label)))


def _projects(args):
    for info in wn.projects():
        key = 'i'
        key += 'c' if info['cache'] else '-'
        # key += 'a' if False else '-'  # TODO: check if project is added to db
        print(
            '\t'.join((
                key,
                info['id'],
                info['version'],
                f"[{info['language'] or '---'}]",
                info['label'] or '---',
            ))
        )


def _path_type(arg):
    return Path(arg)


def _file_path_type(arg):
    path = Path(arg)
    if not path.is_file():
        raise argparse.ArgumentTypeError(f'cannot file file: {arg}')
    return path


parser = argparse.ArgumentParser(
    prog='python3 -m wn',
    description="Manage Wn's wordnet data from the command line.",
)
parser.add_argument(
    '-V', '--version', action='version', version=f'Wn {wn.__version__}'
)
parser.add_argument(
    '-v', '--verbose', action='count', dest='verbosity', default=0,
    help='increase verbosity (can repeat: -vv, -vvv)'
)
parser.add_argument(
    '-d', '--dir',
    type=_path_type,
    help="data directory for Wn's database and cache",
)
parser.set_defaults(func=lambda _: parser.print_help())
sub_parsers = parser.add_subparsers(title='subcommands')


parser_download = sub_parsers.add_parser(
    'download',
    description="Download wordnets and add them to Wn's database.",
    help='download wordnets',
)
parser_download.add_argument(
    'target', nargs='+', help='project specifiers or URLs'
)
parser_download.add_argument(
    '--index', type=_file_path_type, help='project index to use for downloading'
)
parser_download.add_argument(
    '--no-add', action='store_false', dest='add',
    help='download and cache without adding to the database'
)
parser_download.set_defaults(func=_download)


parser_lexicons = sub_parsers.add_parser(
    'lexicons',
    description="Display a list of installed lexicons.",
    help='list installed lexicons',
)
parser_lexicons.add_argument(
    '-l', '--lang', help='BCP 47 language code'
)
parser_lexicons.add_argument(
    '--lexicon', help='lexicon specifiers'
)
parser_lexicons.set_defaults(func=_lexicons)


parser_projects = sub_parsers.add_parser(
    'projects',
    description=(
        "Display a list of known projects. The first column shows the "
        "status for a project (i=indexed, c=cached)."
    ),
    help='list known projects',
)
parser_projects.set_defaults(func=_projects)


args = parser.parse_args()

logging.basicConfig(level=logging.ERROR - (min(args.verbosity, 3) * 10))

if args.dir:
    wn.config.data_directory = args.dir

args.func(args)
