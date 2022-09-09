# Onyo

# ONYO IS UNDER DEVELOPMENT

Onyo is currently being developed, and what follows is the equivalent of a
design document. It is not yet complete.

## Commands

- `onyo cat asset...`:

  Print the contents of `asset`(s) to the terminal without parsing or validating
  the contents.
- `onyo config variable value`:

  Set a `variable` to `value` in the `.onyo/config` file. This command can for
  example change the default tool for the interactive mode of `onyo history`
  with `onyo config history.interactive "git log --follow"`.
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
- `onyo fsck`:

  Runs a comprehensive suite of checks to verify the integrity and validity of
  an onyo repository and its contents:
  - Checks first if an `onyo repository` is given (a valid git repository, which
    contains an `.onyo` folder), otherwise it errors out and does no further
    checks. If the directory is valid, `onyo fsck` runs these checks for the
    whole onyo repository and its contents, and lists all problems encountered:
    - all asset names are unique
    - all files are valid YAML
    - all files follow the rules specified in `.onyo/validation/validation.yaml`
    - the git working tree is clean (no untracked or changed files)
    - all directories and sub-directories have a .anchor file

  Files and directories that should not be checked for their validity can be
  added to .gitignore.
- `onyo git git-command-args...`:

  Pass `git-command-args` as arguments to `git`, using the Onyo repository as
  the git repository.
- `onyo history [--non-interactive, -I] asset | directory`:

  Show the history of a `directory` or `asset` file.
  By default, to show the history in interactive mode, the command uses
  `tig --follow asset | directory`, and for the non-interactive mode it calls
  `git --no-pager log --follow asset | directory`. The default tools can be
  changed with `onyo config`.

  - `--non-interactive` : Force usage of the non-interactive tool to show the
  history of a `asset` or `directory`, and do not detect whether the TTY is
  interactive.
- `onyo init [directory]`:

  Initialize an Onyo repository. The directory will be initialized as a git
  repository (if it is not one already), the .onyo/ directory created
  (containing default config files, templates, etc), and everything committed.

  The current working directory will be initialized if neither `directory` nor
  the `onyo -C <dir>` option are specified.

  Running `onyo init` on an existing repository is safe. It will not overwrite
  anything; it will exit with an error.
- `onyo mkdir directory...`:

  Create `directory`(s). Intermediate directories will be created as needed
  (i.e. parent and child directories to be created in one call).

  Onyo creates a `.anchor` file in every folder to track directories with git
  even when they are empty.

  If the directory already exists, Onyo will throw an error. When multiple
  directories are passed to Onyo, all will be checked before attempting to
  create them.
- `onyo mv [--force, -f] [--rename, -r] source... destination`:

  Move `source`(s) to the `destination` directory, or rename `source` directory
  to `destination`. Onyo will validate the contents of moved assets to make sure
  that they still follow to specified rules. See "Field Validation".

  - `--force`: Silently overwrite the destination file if it already exists.
  - `--rename`: Allow a `source` file to be renamed to a different (valid)
    file name.
- `onyo new [--template template, -t template] [--non-interactive, -I] directory`:

  Creates a new `asset` in `directory`. The command opens a dialog that asks for
  the field names defined by the asset name scheme, and after creation opens the
  new `asset` file with the editor.
  After the editing is done, the new file will be checked for the validity of
  its YAML syntax and based on the rules in `.onyo/validation/validation.yaml`.
  - `--template template`: specifies the template copied by the command. If not
    specified, it uses the standard template.
  - `--non-interactive` : Suppress opening of editor after file creation.
- `onyo rm [--quiet, -q] [--yes, -y] asset | directory...`:

  Delete the `asset`(s) and `directory`(s).

  Onyo will present a complete list of all files and folders to delete, and
  prompt the user for confirmation.

  - `--quiet`: Silence the output (requires the `--yes` flag)
  - `--yes`: Respond "yes" to the prompt and run non-interactively
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
- `onyo shell-completion`:

  Print a shell script for onyo shell completion.

  The output of this command should be "sourced" by bash or zsh to enable shell
  completion for onyo.

  Example:
  ```
  $ source <(onyo shell-completion)
  $ onyo --<press TAB to display available options>
  ```
- `onyo tree directory...`:

  List the assets and directories in `directory` using the `tree` program.
