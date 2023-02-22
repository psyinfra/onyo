import csv
import logging
import sys
from pathlib import Path

from onyo import Repo, OnyoInvalidRepoError
from onyo.commands.edit import edit_asset, get_editor, request_user_response

logging.basicConfig()
log = logging.getLogger('onyo')


def create_assets_in_destination(assets: dict, repo: Repo) -> None:
    """
    Create and populate assets. Parent directories are created if necessary.
    """
    for asset in assets.keys():
        # create missing directories
        if not asset.parent.exists():
            repo.mkdir(asset.parent)
        if not asset.is_file():
            asset.touch()
        repo._write_asset(asset, assets[asset])
    repo.add(list(assets.keys()))


def read_assets_from_tsv(tsv: str, template_name: str, key_values: dict, repo: Repo) -> dict:
    """
    Read a tsv table with a header row and one row for each new asset to
    create. Check the information (e.g. filenames correct and unique), and add
    faux serial numbers to the name if needed.

    Returns a dictionary with paths and contents of assets on success, or
    informs the user about missing or invalid information and exits with error.
    """
    new_assets = {}
    row_count = 0

    with open(tsv, 'r') as tsv_file:
        # count and request the faux serial numbers needed
        table = csv.DictReader(tsv_file, delimiter='\t')
        faux_number = sum([1 for row in table if row['serial'] == 'faux'])
        if faux_number > 0:
            faux_serial_list = repo.generate_faux_serials(num=faux_number)

        # iterate over the table from the beginning to read asset information.
        tsv_file.seek(0)
        table = csv.DictReader(tsv_file, delimiter='\t')
        for row in table:
            row_count += 1
            new_path = ""
            contents = {}

            # error if any required field is empty
            if not all([row['type'], row['make'], row['model'], row['serial'], row['directory']]):
                row_str = "\t".join([value for value in row.values() if value])
                print(f"The fields 'type', 'make', 'model', 'serial' and 'directory' are required, but missing in line {row_count}: '{row_str}'", file=sys.stderr)
                sys.exit(1)

            # set asset name and directory, add faux serial numbers if needed
            if row['serial'] == 'faux':
                row['serial'] = faux_serial_list.pop()
            filename = f"{row['type']}_{row['make']}_{row['model']}.{row['serial']}"
            directory = row['directory']
            new_path = Path(repo.root, directory, filename).resolve()

            # verify that the asset name is valid and unique in repo and table
            try:
                repo.valid_asset_path_and_name_available(new_path, [*new_assets])
            except ValueError as e:
                print(e, file=sys.stderr)
                sys.exit(1)

            # either a template is given in table, CLI, or onyo config
            template = None
            try:
                if "template" in row.keys():
                    if row['template'] == "":
                        print(f"Template value missing in {row_count}", file=sys.stderr)
                        sys.exit(1)
                    template = repo.get_template(row['template'])
                elif template_name:
                    template = repo.get_template(template_name)
                else:
                    template = repo.get_template()
            except ValueError:
                sys.exit(1)

            # set the values from --keys and TSV columns, check for conflicts
            contents_valid = True
            contents = repo._read_asset(template)
            if key_values:
                contents.update(key_values)
            for col in row.keys():
                # these fields contain meta information, not values for content
                if col in ['type', 'make', 'model', 'serial', 'directory', 'template']:
                    continue
                # information from --keys is not allowed to conflict with columns
                if key_values and col in key_values.keys():
                    print(f"Can't use --keys '{col}' and have tsv column '{col}'", file=sys.stderr)
                    contents_valid = False
                    break
                contents[col] = row[col]
            if not contents_valid:
                sys.exit(1)

            new_assets[new_path] = contents

    return new_assets


def read_assets_from_CLI(assets: list[str], template_name: str, key_values: dict, repo: Repo) -> dict:
    """
    Read information from `assets`, with a new asset file for each entry.
    Check the information (e.g. filename correct and unique), and add
    faux serial numbers to the names if needed.

    Returns a dictionary with paths and contents of assets on success, or
    informs the user about missing or invalid information and exits with error.
    """
    new_assets = {}

    # count and request the faux serial numbers needed
    faux_number = sum([1 for asset in assets if "faux" in asset.split('.')[-1]])
    if faux_number > 0:
        faux_serial_list = repo.generate_faux_serials(num=faux_number)

    for asset in assets:
        new_path = ""
        contents = dict()

        # set paths
        if asset[-5:] == ".faux":
            asset = asset[:-5] + asset[-5:].replace("faux", faux_serial_list.pop())
        new_path = Path(repo.opdir, asset).resolve()

        # verify that the asset name is valid and unique in repo and table
        try:
            repo.valid_asset_path_and_name_available(new_path, [*new_assets])
        except ValueError as e:
            print(e, file=sys.stderr)
            sys.exit(1)

        # get template and check its existence and validity
        template = None
        try:
            template = repo.get_template(template_name)
        except ValueError:
            sys.exit(1)

        # add values from --keys and template to asset:
        contents = repo._read_asset(template)
        if key_values:
            contents.update(key_values)

        new_assets[new_path] = contents

    return new_assets


def sanitize_asset_information(assets: list[str], template: str,
                               tsv: str, key_values: dict, repo: Repo) -> dict:
    """
    Collect and normalize information from TSV and CLI for the creation of
    new assets.

    Returns a dictionary with paths and contents of assets on success, or
    informs the user about missing or invalid information and exits with error.
    """
    new_assets = {}

    if tsv:
        new_assets = read_assets_from_tsv(tsv, template, key_values, repo)
    else:
        new_assets = read_assets_from_CLI(assets, template, key_values, repo)
    if not new_assets:
        print("No new assets given.", file=sys.stderr)
        sys.exit(1)
    return new_assets


def check_against_argument_conflicts(args) -> None:
    """
    Some arguments conflict with each other, e.g. it has to be checked that the
    information from a tsv table does not conflict with the information from
    the command line.
    """
    # have either tsv table describing paths and asset names, or have it as
    # input argument, but not both.
    if args.tsv and args.path:
        print("Can't have asset(s) and tsv file given.", file=sys.stderr)
        sys.exit(1)
    if not args.tsv and not args.path:
        print("Either asset(s) or a tsv file must be given.", file=sys.stderr)
        sys.exit(1)

    if args.tsv:
        if not Path(args.tsv).is_file():
            print(f"{args.tsv} does not exist.", file=sys.stderr)
            sys.exit(1)
        with open(args.tsv, 'r') as tsv_file:
            table = csv.reader(tsv_file, delimiter='\t')
            header = []
            # check that the first row (header) is complete
            for row in table:
                header = row
                break
            if not all(field in header for field in ['type', 'make', 'model', 'serial', 'directory']):
                print("onyo new --tsv needs columns 'type', 'make', 'model', 'serial' and 'directory'.", file=sys.stderr)
                sys.exit(1)
            if args.template and 'template' in header:
                print("Can't use --template and template column in tsv.", file=sys.stderr)
                sys.exit(1)


def new(args, opdir: str) -> None:
    """
    Create new ``<path>/asset``\(s) and add contents with ``--template``,
    ``--keys`` and ``--edit``. If the directories do not exist, they will be
    created.

    After the contents are added, the new ``assets``\(s) will be checked for the
    validity of its YAML syntax and based on the rules in ``.onyo/validation/``.
    """
    repo = None
    try:
        repo = Repo(opdir)
        repo.fsck()
    except OnyoInvalidRepoError:
        sys.exit(1)

    # verify that arguments do not conflict, otherwise exit
    check_against_argument_conflicts(args)

    # read and verify the information for new assets from TSV and CLI
    assets = sanitize_asset_information(args.path, args.template, args.tsv,
                                        args.keys, repo)

    # create all assets (and non-existing folder), and set their contents
    create_assets_in_destination(assets, repo)

    if args.edit:
        editor = get_editor(repo)
        for asset in assets:
            edit_asset(editor, asset)
            repo.add(asset)

    # TODO: validate assets before offering to commit. This has to be done after
    # they are build, their values are set, and they where opened to edit

    # print diff-like output and remember new directories and assets
    staged = sorted(repo.files_staged)
    changes = []
    if staged:
        print("The following will be created:")
        for path in staged:
            # display new folders, not anchors.
            if ".anchor" in str(path):
                print(path.parent)
                changes.append(path.parent)
            else:
                print(path)
                changes.append(path)

    # commit or discard changes
    if args.yes or request_user_response("Create assets? (y/n) "):
        repo.commit("new asset(s)", changes)
    else:
        repo._git(["rm", "-rf"] + [str(path) for path in changes])
        print('No new assets created.')
        sys.exit(0)
