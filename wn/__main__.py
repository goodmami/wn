import argparse
from pathlib import Path

import wn


def _download(args):
    if args.index:
        wn.config.load_index(args.index)
    for target in args.target:
        wn.download(target)


def _lexicons(args):
    for lex in wn.lexicons(lgcode=args.lgcode, lexicon=args.lexicon):
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
                f"[{info['language']}]",
                info['label'],
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
    '-d', '--dir',
    type=_path_type,
    help="data directory for Wn's database and cache",
)
sub_parsers = parser.add_subparsers()


parser_download = sub_parsers.add_parser(
    'download',
    description="Download wordnets and add them to Wn's database."
)
parser_download.add_argument(
    'target', nargs='+', help='project specifiers or URLs'
)
parser_download.add_argument(
    '--index', type=_file_path_type, help='project index to use for downloading'
)
parser_download.set_defaults(func=_download)


parser_lexicons = sub_parsers.add_parser(
    'lexicons',
    description="Display a list of installed lexicons."
)
parser_lexicons.add_argument(
    '-l', '--lgcode', help='BCP 47 language codes'
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
    )
)
parser_projects.set_defaults(func=_projects)


args = parser.parse_args()
if args.dir:
    wn.config.data_directory = args.dir
args.func(args)
