import subprocess


# command does not explode
def test_good_returncode():
    ret = subprocess.run(["onyo", "shell-completion"])
    assert ret.returncode == 0


# There should be no "None"s in the output. If so, it is usually due to an unset
# metavar variable in the argparse arguments.
def test_no_empty_metavars():
    ret = subprocess.run(["onyo", "shell-completion"], capture_output=True, text=True)
    assert 'None' not in ret.stdout


# A naive test to see if there are "enough" lines. Boilerplate alone was 54
# lines at the time of this writing and the full script at 168. If there's
# fewer than 100 lines, then something significant is missing (or has changed).
def test_script_length():
    ret = subprocess.run(["onyo", "shell-completion"], capture_output=True, text=True)
    lines = ret.stdout.count('\n')
    assert lines >= 100


# zsh parses the script successfully
def test_zsh_parseable():
    # "compinit -C" disables security-related checks. This is necessary for
    # non-interactive environments. See the compinit source for more info.
    ret = subprocess.run(["zsh", "-c", "autoload -Uz compinit && compinit -C && source <(onyo shell-completion)"])
    assert ret.returncode == 0
