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
assignment: *where* something is or *who* has it. A folder can also be used to
bundle multiple assets together into a larger asset (see "Advanced").


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

The `type`, `make`, or `model` fields reserve the `_` and `.` characters.

The `serial` field has no restrictions.

### Field Validation

Values for the `type`, `make`, and `model` fields are checked against a
field-specific allow-list in the config folder (see "Config Files"). Entries can
be strings or, for more complex needs, any valid [Python Regular Expression](https://docs.python.org/3/library/re.html#regular-expression-syntax).

Values are checked for reserved characters before they are checked against the
validation strings/patterns.

One can effectively disable validation for a field by adding `.*` to the
corresponding validation list.


## File Contents

Files are written in YAML and contain metadata about the asset. This can
describe the physical attributes of the hardware (CPU type, RAM size, ), but can
also extend to any metadata you wish to track (software, associated purchase
order numbers, etc).

TODO: template format

TODO: validation

TODO: template matching

TODO: pseudo-keys


## Config Files

Configuration files are stored in the `.onyo/` folder in the top-level of the
repository.

TODO: list the files and explain them


## Advanced

A folder can also bundle multiple assets together into a larger asset, such as a
server with a separately tracked network card, or a laptop with a specific
software license.


TODO:
- what is the file-name to describe the folder-asset?
  - server (tracked) and a NIC (tracked)
  - laptop (tracked) and software license (tracked)

If licensing is attached to a particular machine (such as an OEM licence), then
it is best encoded as a metadata field. If the license is transferable, then the
laptop asset should be converted to a folder, and the license moved into it.


## Commands

- `onyo init [directory]`:

  Initialize an Onyo repository. The directory will be initialized as a git
  repository (if it is not one already), the `.onyo/` configuration folder
  created, and template files generated and committed.

  The current working directory will be initialized if neither `directory` nor
  the `ONYO_REPOSITORY_DIR` environment variable are specified. If both are set,
  Onyo will throw an error.

  Running `onyo init` on an existing repository is safe. It will not overwrite
  anything; it will exit with an error.
- `onyo ls [asset | directory]...`:

  List the names of files and directories contained within a directory. If the
  argument is a file, the filename will be listed. The results are listed
  alphabetically.

  Arguments are relative to `ONYO_REPOSITORY_DIR` (if set); otherwise, arguments
  are relative to the current working directory.

  If no arguments are given, the contents of `ONYO_REPOSITORY_DIR` (if set) are
  listed; otherwise the current working directory is listed.

  If `ONYO_REPOSITORY_DIR` is not set and the current working directory is not
  in an Onyo repository, Onyo will throw an error.
- `onyo tree directory...`:

  List the assets and directories in `directory` using the `tree` program.
- `onyo mv [--force, -f] [--rename, -r] source... destination`:

  Move `source`(s) to the `destination` directory, or rename `source` directory
  to `destination`.

  - `--force`: silently overwrite the destination file if it already exists.
  - `--rename`: allow a `source` file to be renamed to a different (valid)
    file name.
- `onyo cat asset-file...`:

  Print the contents of `asset` to the terminal without parsing or validating
  the contents.
- `onyo edit asset-file`:

  Opens the asset file using the default text editor specified by the
  environment variable `EDITOR` (`nano` and then `vi` are used as fallbacks).

  TODO: Describe validation
- `onyo get [--depth num, -d] [--filter key=value[,key=value...], -f] [--machine-readable, -m] [--sort-ascending key, -s | --sort-descending key, -S] key[,key...] [asset | directory]...`:

  Print the requested `key`(s) in tabular form for matching assets.

  If no `asset` or `directory` is specified, the current working directory is
  used. If Onyo is invoked from outside of the Onyo repository, the root of the
  repository is used.

  Key names can be any valid YAML key name. Dictionary keys can be addressed
  using a `.` (e.g. `parent.child`). Multiple pseudo-keys (that do not appear in
  the actual asset file) are available for queries (see "File Contents").

  Multiple `key`s can be queried by joining them with a `,`.

  `value`s that are a dictionary or list are output literally as "[dict]" or
  "[list]"; the contents are not listed. Dictionary keys can be addressed using
  a `.` (e.g. `parent.child`).

  If the key does not exist, it is output literally as "[unset]".

  - `--depth num`: Limit the maximum number of levels of directories to search
    beneath `directory`. `--depth 1` limits to files that are direct children of
    `directory`.
  - `--filter key=value`: Only apply changes to assets that have `key` and it
    matches `value`. Multiple restrictions can be declared by joining with a `,`
    --- which acts as a logical AND operator. There is no "OR" equivalent.

    `value` can be a string or a Python regular expression. Onyo's string
    representation of types can also be used for queries, such as "[list]",
    "[dict]", or "[unset]" (for keys that don't exist).
  - `--machine-readable`: Display output in a form more easily parsed by
    scripts. Headers are omitted, and fields are separated by a single tab.
  - `--sort-ascending`: Sort the results in ascending order according to the
    value of `key`.

    Multiple invocation of `--sort-ascending` and/or `--sort-descending` are
    evaluated from left to right in decreasing order of importance.
  - `--sort-descending`: The same as `--sort-ascending`, but sort by `key` in
    descending order.

  Errors reading or parsing files print to STDERR, but do not halt Onyo.
- `onyo set [--depth num, -d] [--dry-run, -n ] [--filter key=value[,key=value...], -f] [--quiet, -q] [--rename, -r] [--yes, -y] key=value[,key=value...] [asset | directory]...`:

  Set the `value` of `key` for matching assets. If the key does not exist, it is
  added and set appropriately.

  Key names can be any valid YAML key name. Dictionary keys can be addressed
  using a `.` (e.g. `parent.child`).

  Multiple `key=value` pairs can be declared by joining with a `,`. Quotes can
  be used around `value`, which is necessary when it contains a comma,
  whitespace, etc.

  Key values can be initialized as a dictionary or list --- but only as empty.
  - lists: `key=[list]` or `key=[]`
  - dictionaries: `key=[dict]` or `key={}`

  The `type`, `make`, `model`, and `serial` pseudo-keys (see "File Contents")
  can be set when the `--rename` flag is used. It will result in the file(s)
  being renamed.

  See `onyo unset` to remove keys.

  If no `asset` or `directory` is specified, the current working directory is
  used. If Onyo is invoked from outside of the Onyo repository, the root of the
  repository is used.

  Changes are printed to the terminal in the style of `diff`.

  - `--depth num`: limit the maximum number of levels of directories to search
    beneath `directory`. `--depth 1` limits to files that are direct children of
    `directory`.
  - `--dry-run`: Perform a non-interactive trial run with no changes made.
  - `--filter key=value`: Only apply changes to assets that have `key` and it
    matches `value`. Multiple restrictions can be declared by joining with a `,`
    --- which acts as a logical AND operator. There is no "OR" equivalent.

    `value` can be a string or a Python regular expression. Onyo's string
    representation of types can also be used for queries, such as "[list]",
    "[dict]", or "[unset]" (for keys that don't exist).
  - `--rename`: permit assigning values to pseudo-keys that would result in the
    file(s) being renamed.
  - `--quiet`: silence the diff-like output of key-value changes.
  - `--yes`: Respond "yes" to all prompts and run non-interactively.

  Errors reading or parsing files print to STDERR, but do not halt Onyo. Any
  error encountered while writing a file will cause Onyo to error and exit
  immediately.
- `onyo git git-command-args...`:

  Pass `git-command-args` as arguments to `git`, using the Onyo repository as
  the git repository. This is most valuable when used in conjunction with
  `ONYO_REPOSITORY_DIR`.


TODO:
- onyo new
- onyo unset
- onyo rm
- onyo fsck
- onyo history


## Environment Variables

- `ONYO_REPOSITORY_DIR`:

   Location of an Onyo repository. This can be used to invoke `onyo` from
   anywhere on the filesystem.
- `EDITOR`:
   The text editor spawned by Onyo.


## Examples

**Inventory a new asset; add it to the warehouse**:
```
onyo new warehouse
<type>*: laptop
<make>*: lenovo
<model>*: T490s
<serial>*: abc123
<spawns VIM, the above fields are pre-filled. The user edits remaining fields>
<writes out to shelf/laptop_lenovo_T490s.abc123
```

**Assign an asset**:
```
onyo mv shelf/laptop_lenovo_T490s.abc123 accounting/Bingo Bob/
```

**Retire an asset**:
```
onyo mv accounting/Bingo Bob/laptop_lenovo_T490s retired/
```

**Upgrade an asset**:
```
onyo set RAM=16GB accounting/Bingo Bob/laptop_lenovo_T490s
- RAM: 8GB
+ RAM: 16GB
```
or
```
onyo edit accounting/Bingo Bob/laptop_lenovo_T490s
<spawns VIM; user edits ram field>
```

**List all assets on the shelf**:
```
onyo ls shelf
```
or
```
onyo tree shelf
```

**List all headsets on the shelf**:
```
onyo ls shelf/headset_*
```
or
```
onyo get filename --filter type=headset shelf
```

**List the history of an asset**:
```
onyo history accounting/Bingo Bob/laptop_lenovo_T490s
```

**Get the filename, make, model, and purchase data of all laptops assigned to the accounting department; sort first by make, then model, then purchase date**:
```
onyo get --filter type=laptop -s make -s model -s purchase_date filename,make,model,purchase_date accounting/
```


## Example Layout

TODO


## Names

TODO Short name vs long name. Globbing.
