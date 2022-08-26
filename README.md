# Onyo

Onyo is a text-based inventory system backed by git. There is no server, SQL
database, web interface, etc. It is inspired by [pass](https://www.passwordstore.org)
(password management) and [ledger](https://www.ledger-cli.org) (of [plain text accounting](https://plaintextaccounting.org)
fame).

Onyo uses the filesystem as the index and git to track history. This allows much
of Onyo's functionality to be just a thin wrapper around git commands.

# ONYO IS UNDER DEVELOPMENT

Onyo is currently being developed, and what follows is the equivalent of a
design document. It is not yet complete.


## Just Files and Folders

Everything is based on text files and folders. This simplicity makes Onyo
adaptable to alternate layouts and workflows beyond what was imagined when
designing it.

Every asset is a file, and there is only one asset per file. Folders denote
assignment: *where* something is or *who* has it.


## Inventory Concepts

**Tracking** involves *where* something is or *who* is belongs to. In an Onyo
repository, every asset is tracked. In file system terms, this means that every
file (asset) is in a folder (named after a location or person). A common example
is a power adapter; it is unimportant to know which exact adapter someone has,
but it is desired to know that a user has one.

**Identification** is when the specificity of an asset is important. For
example: one may wish to know that a user has a specific laptop (e.g. the
MacBook Pro with the inventory number `ABC123`).

The identify of assets is tracked via its **serial** (see "Asset Name Scheme").

**Counting** is for assets that are neither tracked nor identified. A typical
example is counting the number of USB cables or mice available in inventory, but
who receives these items is *not tracked*. Onyo does *not* address this use
case, and has no mechanism to count or tally without tracking.


## Asset Name Scheme

Onyo asset names use the following pattern:

```
type_make_model.serial
```

**Type**: The type of asset (e.g. laptop, display, PDU, etc)

**Make**: The manufacturer/brand (e.g. Lenovo, Apple, Supermicro, etc)

**Model**: The model (e.g. RX2135 or MBPlate2020). User preferences will vary
widely here. Some will wish to use the user-friendly model names (e.g. NUC8),
the precise manufacturer model (BOXNUC8I5BEK2), or their own naming convention.

**Serial**: A unique identifier for the asset. Assets for which the **identity**
is important will use either an inventory number (if present) or manufacturer
serial number (if present).

Assets for which the identity is *not* important receive a unique
**faux-serial** to prevent filename conflicts. These serials are prepended with
the word `faux`.

### Uniqueness

Each filename is unique within the repository. The **serial** alone *should* be
unique, but cross-manufacturer conflicts is theoretically possible. In practice,
the combination of type, make, model, and serial is sufficient to avoid all
(reasonable) chance of conflicts.

### Reserved Characters

The `type`, `make`, or `model` fields reserve the `_`
and `.` characters. The `serial` field has no restrictions.

Values for the `type`, `make`, and `model` name fields are checked against a
list of reserved characters.

## File Contents

Files are written in YAML and contain metadata about the asset. This can
describe the physical attributes of the hardware (CPU type, RAM size, etc), but
can also extend to any metadata you wish to track (software, associated purchase
order numbers, etc).

## Config Files

Configuration files are stored in the `.onyo/` folder in the top-level of the
repository.

- `.onyo/config` specifies:
  - tools used by `onyo history`.
    The values can be updated with e.g.:
    - `onyo config history.interactive "tig --follow"`
    - `onyo config history.non-interactive "git --no-pager log --follow"`
  - default template to use with `onyo new <dir>`
    The standard template can be updated with e.g.:
    - `onyo config template.default standard`
- `.onyo/templates/` contains:
  - the templates for the `onyo new --template <template>` command (see
    "Template Files")
- `.onyo/validation/validation.yaml`
  - File describing rules for asset files and their fields (see "Field
    Validation")

## Template Files

Templates can be used with the command `onyo new --template <template>
<directory>` and are stored in the folder `.onyo/templates/`.
Templates will be copied as a basis for a new asset file, and can then be
edited. After saving the newly created asset, the file will be checked for
valid YAML syntax.

The default template that gets used when `onyo new` is called is
`.onyo/templates/standard`. It can be updated with
`onyo config template.default standard`.

For examples, see the section "Example Templates" at the end of the README.

## Field Validation

To keep meta data fields consistent between different assets, rules for fields
in assets can be defined in `.onyo/validation/validation.yaml` in an onyo
repository. The validation file will be read from the top down, and the first
path in the validation file that fits a asset file will be used to validate
it's contents.

The structure for rules is:
```
<directory>/*:
- <Key>:
    - Type: <type>
```

The options that are currently supported are:
- Type:
    - can be int/float/str

A file will be automatically validated every time after creation with
`onyo new`, and after changing it with `onyo edit`, `onyo set` and `onyo mv`.
`onyo fsck` will validate all fields in all assets in an onyo repository.

Onyo differentiates between `<directory>/*` (files directly in `<directory>`)
and `<directory>/**` (all assets in `<directory>` and all its
sub-directories). YAML pointers can be used to define a set of rules once and
apply it to multiple sub-directories.

For further help, see "Example Validation".

## Commands

- `onyo init [directory]`:

  Initialize an Onyo repository. The directory will be initialized as a git
  repository (if it is not one already), the .onyo/ directory created
  (containing default config files, templates, etc), and everything committed.

  The current working directory will be initialized if neither `directory` nor
  the `onyo -C <dir>` option are specified.

  Running `onyo init` on an existing repository is safe. It will not overwrite
  anything; it will exit with an error.
- `onyo tree directory...`:

  List the assets and directories in `directory` using the `tree` program.
- `onyo mv [--force, -f] [--rename, -r] source... destination`:

  Move `source`(s) to the `destination` directory, or rename `source` directory
  to `destination`. Onyo will validate the contents of moved assets to make sure
  that they still follow to specified rules. See "Field Validation".

  - `--force`: Silently overwrite the destination file if it already exists.
  - `--rename`: Allow a `source` file to be renamed to a different (valid)
    file name.
- `onyo mkdir directory...`:

  Create `directory`(s). Intermediate directories will be created as needed
  (i.e. parent and child directories to be created in one call).

  Onyo creates a `.anchor` file in every folder to track directories with git
  even when they are empty.

  If the directory already exists, Onyo will throw an error. When multiple
  directories are passed to Onyo, all will be checked before attempting to
  create them.
- `onyo cat asset...`:

  Print the contents of `asset`(s) to the terminal without parsing or validating
  the contents.
- `onyo rm [--quiet, -q] [--yes, -y] asset | directory...`:

  Delete the `asset`(s) and `directory`(s).

  Onyo will present a complete list of all files and folders to delete, and
  prompt the user for confirmation.

  - `--quiet`: Silence the output (requires the `--yes` flag)
  - `--yes`: Respond "yes" to the prompt and run non-interactively
- `onyo edit [--non-interactive, -I] asset...`:

  Open the `asset` file(s) using the default text editor specified by the
  environment variable `EDITOR` (`nano` and then `vi` are used as fallbacks).

  When multiple asset files are given, Onyo will open them in sequence.
  - `--non-interactive`: Suppress opening of editor

  After editing an `asset`, `onyo` will check the validity of the YAML syntax
  and check if the changed file still follows the rules specified in
  `.onyo/validation/validation.yaml`, and if problems are found it gives the
  choice to either correct them or discard the changes to make sure that the
  repository stays in a valid state.
- `onyo set [--recursive, -R] [--depth num, -d] [--dry-run, -n ] [--quiet, -q] [--yes, -y] key=value[,key=value...] [asset | directory]...`:

  Set the `value` of `key` for matching assets. If the key does not exist, it is
  added and set appropriately.

  Key names can be any valid YAML key name.

  Multiple `key=value` pairs can be declared by joining with a `,`. Quotes can
  be used around `value`, which is necessary when it contains a comma,
  whitespace, etc.

  If no `asset` or `directory` is specified, the current working directory is
  used. If Onyo is invoked from outside of the Onyo repository, the root of the
  repository is used.

  Changes are printed to the terminal in the style of `diff`.

  - `--recursive`: Update assets in directories recursively.
  - `--depth num`: Limit the maximum number of levels of directories to search
    beneath `directory`. `--depth 1` limits to files that are direct children of
    `directory`.
  - `--dry-run`: Perform a non-interactive trial run with no changes made.
  - `--quiet`: Silence the diff-like output of key-value changes.
  - `--yes`: Respond "yes" to all prompts and run non-interactively.

  Errors reading or parsing files print to STDERR, but do not halt Onyo. Any
  error encountered while writing a file will cause Onyo to error and exit
  immediately.
- `onyo git git-command-args...`:

  Pass `git-command-args` as arguments to `git`, using the Onyo repository as
  the git repository.
- `onyo new [--template template, -t template] [--non-interactive, -I] directory`:

  Creates a new `asset` in `directory`. The command opens a dialog that asks for
  the field names defined by the asset name scheme, and after creation opens the
  new `asset` file with the editor.
  After the editing is done, the new file will be checked for the validity of
  it's YAML syntax and based on the rules in `.onyo/validation/validation.yaml`.
  - `--template template`: specifies the template copied by the command. If not
    specified, it uses the standard template.
  - `--non-interactive` : Suppress opening of editor after file creation.
- `onyo history [--non-interactive, -I] asset | directory`:

  Show the history of a `directory` or `asset` file.
  By default, to show the history in interactive mode, the command uses
  `tig --follow asset | directory`, and for the non-interactive mode it calls
  `git --no-pager log --follow asset | directory`. The default tools can be
  changed with `onyo config`.

  - `--non-interactive` : Force usage of the non-interactive tool to show the
  history of a `asset` or `directory`, and do not detect whether the TTY is
  interactive.
- `onyo config variable value`:

  Set a `variable` to `value` in the `.onyo/config` file. This command can for
  example change the default tool for the interactive mode of `onyo history`
  with `onyo config history.interactive "git log --follow"`.
- `onyo fsck`:

  Runs a comprehensive suite of checks to verify the integrity and validity of
  an onyo repository and it's contents:
  - Checks first if an `onyo repository` is given (a valid git repository, which
    contains an `.onyo` folder), otherwise it errors out and does no further
    checks. If the directory is valid, `onyo fsck` runs these checks for the
    whole onyo repository and it's contents, and lists all problems encountered:
    - all asset names are unique
    - all files are valid YAML
    - all files follow the rules specified in `.onyo/validation/validation.yaml`
    - the git working tree is clean (no untracked or changed files)
    - all directories and sub-directories have a .anchor file

  Files and directories that should not be checked for their validity can be
  added to .gitignore.


## Environment Variables

- `EDITOR`:
   The text editor spawned by Onyo.


## Examples

**Inventory a new asset; add it to the shelf**:
```
onyo new shelf
<type>*: laptop
<make>*: lenovo
<model>*: T490s
<serial>*: abc123
<spawns editor. The user edits fields>
<writes out to shelf/laptop_lenovo_T490s.abc123
```

**Assign an asset**:
```
onyo mv shelf/laptop_lenovo_T490s.abc123 accounting/Bingo\ Bob/
```

**Retire an asset**:
```
onyo mv accounting/Bingo\ Bob/laptop_lenovo_T490s retired/
```

**Upgrade an asset**:
```
onyo set RAM=16GB accounting/Bingo\ Bob/laptop_lenovo_T490s
- RAM: 8GB
+ RAM: 16GB
```
or
```
onyo edit accounting/Bingo\ Bob/laptop_lenovo_T490s
<spawns $EDITOR; user edits RAM field>
```

**List all assets on the shelf**:
```
onyo tree shelf
```

**List the history of an asset**:
```
onyo history accounting/Bingo\ Bob/laptop_lenovo_T490s
```

**List the history of all assets of a user**:
```
onyo history accounting/Bingo\ Bob
```

## Example Templates

This section describes some of the templates provided with `onyo init` in the
directory `.onyo/templates/`.

`onyo new <dir>` (equivalent to `onyo new --template standard <dir>`) as defined
by `.onyo/templates/standard` is a plain YAML file:

```
---
```

This template passes the YAML syntax check when onyo is called while the editor
is suppressed with `onyo new --non-interactive <directory>`.

`onyo new --template laptop.example <dir>` as defined by
`.onyo/templates/laptop.example` contains a simple example for a laptop asset
which already contains some fields, which are relevant for all assets of that
device type.

```
---
RAM:
Size:
USB:
```

## Example Validation

The following sections give examples how one can use the `validation.yaml` to
keep assets and their metadata consistent in an onyo repository. Onyo reads the
`validation.yaml` file from top to bottom and will apply the first rule for
which the name scheme fits an asset.

**Example 1: Rules for different files and directories**

For each directory/path, a separate set of rules can be specified (e.g.
`shelf/*` and `user1/*`). The user can also define rules, that just apply to
files, that match certain asset names (`shelf/*laptop*` in the example).

```
"shelf/*laptop*":
- RAM:
    - Type: int
"shelf/*":
- RAM:
    - Type: float
"user1/*":
- Size:
    - Type: int
- USB:
    - Type: int
```

For the assets in `shelf` with "laptop" in their file name, the value RAM must
have the type int. All other assets in `shelf` can have a float as RAM value.
For assets under the directory `user1/*` the rules for the RAM key do not apply,
instead it has a different set of rules for the keys `Size` and `USB`.

**Example 2: Directories, Sub-Directories and onyo-wide Rules**

Onyo differentiates between `shelf/*` (to define rules for assets directly under
`shelf/`) and `shelf/**` (for all assets in shelf and all it's sub-directories).
The user can also use `"**":` at the end of `validation.yaml` to specify a set of
rules that will be applied to all assets anywhere in onyo, if no other rule
defined before applies to an asset file.

```
"shelf/*":
- RAM:
    - Type: int
"shelf/**":
- Size:
    - Type: int
"**":
- RAM:
    - Type: float
- Size:
    - Type: float
```

When assets directly in `shelf/` have a key `RAM`, it must be integer. Because
onyo uses just the first set of rules where the asset matches the path
defined in validation.yaml, the later rules under `shelf/**` do not apply to
assets directly in `shelf/`.

When assets are in a sub-folder of `shelf/`, the rule for RAM does not apply,
instead the separate set of rules under `shelf/**` will be used to validate
these assets.

Asset files in sub-directories of shelf, e.g. `shelf/left/top_row/` have no
rules regarding the `RAM` key, just the rule for `Size` does apply.

The rule `**` enforces for all assets outside of `shelf/` that keys for RAM
and Size must be at least float (e.g. "RAM: 12GB" as string are invalid for all
assets anywhere in the onyo repository).
The rules for `**` do not apply to assets in `shelf/`, because onyo uses just
the first set of rules where a path matches, and `shelf/` has a separate set of
rules already defined above.

**Example 3: Using pointer to define a set of rules for multiple Directories**

To define a single set of rules, that is applied to multiple other directories
(users in the example), YAML pointers can be used.

```
"generic_rules_for_users/**": &pointer_user
- RAM:
    - Type: int
- Size:
    - Type: int
"user1/**":
    *pointer_user
"user2/**":
    *pointer_user
```

A generic set of rules can be defined and marked with `&pointer_user`, to enable
the usage of the set of rules for other directories. With `*pointer_user` the
rules for `RAM` and `Size` will be a applied for the directories `user1/**`
and `user2/**`.
