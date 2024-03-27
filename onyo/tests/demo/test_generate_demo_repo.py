import subprocess
from pathlib import Path


def test_generate_demo_repo(tmp_path, request) -> None:
    r"""
    Generate an Onyo demo repository, and compare it against the git log of
    another known-good-demo-repo.
    """
    script = Path(request.path.parent.parent.parent.parent, 'demo/', 'generate_demo_repo.sh')

    ret = subprocess.run([script, tmp_path],
                         capture_output=True, text=True)
    assert ret.returncode == 0

    #
    # compare the git log of the freshly-generated-repo against the reference
    #
    ret = subprocess.run(['git', '-C', tmp_path, 'log'],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert ret.stdout == Path(request.path.parent, 'reference_git_log.txt').read_text()
