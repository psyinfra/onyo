import subprocess
import pytest
from pathlib import Path

from onyo.lib.onyo import OnyoRepo


prefilled_assets = [
    ['warehouse/monitor_dell_PH123.86JZho',
     "type: 'monitor'\nmake: 'dell'\nmodel: 'PH123'\nserial: '86JZho'\n"
     "display: 22.0\nfzj_inventory: '45FZ18'\n"],
    ['warehouse/monitor_dell_NoIdea.S0M3',
     "type: 'monitor'\nmake: 'dell'\nmodel: 'NoIdea'\nserial: 'S0M3'\n"
     "display: 27.0\n"],
    ['warehouse/laptop_apple_macbook.oiw629',
     "type: 'laptop'\nmake: 'apple'\nmodel: 'macbook'\nserial: 'oiw629'\n"
     "RAM: '8GB'\ndisplay: 13.3\nUSB_A: 2\nfzj_inventory: '28FZ34'\nbuild-date: '20160501'\n"],
    ['warehouse/laptop_apple_macbook.9r32he',
     "type: 'laptop'\nmake: 'apple'\nmodel: 'macbook'\nserial: '9r32he'\n"
     "RAM: '8GB'\ndisplay: 13.3\nfzj_inventory: '28FJ34'\nbuild-date: '20180501'\n"],
    ['somegroup/userA/laptop_apple_macbook.9r5qlk',
     "type: 'laptop'\nmake: 'apple'\nmodel: 'macbook'\nserial: '9r5qlk'\n"
     "RAM: '8GB'\ndisplay: 15.0\nhostname: 'first.host'\n"],
    ['somegroup/userB/laptop_lenovo_thinkpad.owh8e2',
     "type: 'laptop'\nmake: 'lenovo'\nmodel: 'thinkpad'\nserial: 'owh8e2'\n"
     "RAM: '8GB'\ndisplay: 14.6\nfzj_inventory: '13BH9F'\n"],
    ['warehouse/laptop_lenovo_thinkpad.iu7h6d',
     "type: 'laptop'\nmake: 'lenovo'\nmodel: 'thinkpad'\nserial: 'iu7h6d'\n"
     "RAM: '8GB'\ndisplay: 13.3\nfzj_inventory: '63AH90'\n"],
    ['warehouse/laptop_microsoft_surface.oq782j',
     "type: 'laptop'\nmake: 'microsoft'\nmodel: 'surface'\nserial: 'oq782j'\n"
     "RAM: '8GB'\ndisplay: 12.4\nfzj_inventory: '73CDA45'\ntouchscreen: 'yes'\n"]]

preset_dirs = ['retired', 'lost']


@pytest.mark.repo_dirs(*preset_dirs)
@pytest.mark.repo_contents(*prefilled_assets)
def test_workflow_cli(repo: OnyoRepo) -> None:

    # 1. create new group
    workgroup = Path("newgroup")
    cmd = ['onyo', '--yes', '--quiet', 'mkdir', str(workgroup)]
    ret = subprocess.run(cmd, capture_output=True, text=True)
    assert ret.returncode == 0

    # 2. New member joining group
    member = workgroup / "Sam User"

    # 2a. Create the user
    cmd = ['onyo', '--yes', '--quiet', 'mkdir', str(member)]
    ret = subprocess.run(cmd, capture_output=True, text=True)
    assert ret.returncode == 0

    # 2b. Check the warehouse for a display
    cmd = ['onyo', 'get', '-p', 'warehouse', '-H', '--match', 'type=monitor', "display=22.0"]
    ret = subprocess.run(cmd, capture_output=True, text=True)
    assert ret.returncode == 0
    monitor = Path(ret.stdout.splitlines()[0].split('\t')[-1].strip("\""))

    # 2c. Assign display to user
    cmd = ['onyo', '--yes', '--quiet', 'mv', str(monitor), str(member)]
    ret = subprocess.run(cmd, capture_output=True, text=True)
    assert ret.returncode == 0

    # 2d. Assign newly purchased laptop to user
    laptop = member / "lenovo_thinkpad_laptop.123"
    cmd = ['onyo', '--yes', 'new', '-p', str(member), '-m', "New purchase: ThinkPad",
           '--keys', 'memory=8GB', 'model=laptop', 'type=lenovo', 'make=thinkpad', 'serial=123']
    ret = subprocess.run(cmd, capture_output=True, text=True)
    assert ret.returncode == 0
    # 2e. That was completely wrong data entry. Essentially all the wrong keys.
    # Let's remove asset entirely and redo.
    cmd = ['onyo', '--yes', 'rm', str(laptop), '-m', "Delete asset due to erroneous data entry"]
    ret = subprocess.run(cmd, capture_output=True, text=True)
    assert ret.returncode == 0

    cmd = ['onyo', '--yes', 'new', '-p', str(member), '-m', "New purchase: ThinkPad",
           '--keys', 'RAM=8GB', 'build-date=20160310', 'type=laptop', 'make=lenovo', 'model=thinkpad', 'serial=SN123Z']
    ret = subprocess.run(cmd, capture_output=True, text=True)
    assert ret.returncode == 0

    # 3. Laptop got an FZJ inventory number
    # 3a. Find the laptop based on serial number:
    cmd = ['onyo', 'get', '--match', 'serial=SN123Z', '-H']
    ret = subprocess.run(cmd, capture_output=True, text=True)
    assert ret.returncode == 0
    laptop = Path(ret.stdout.splitlines()[0].split('\t')[-1].strip("\""))

    # 3b. Set the inventory number
    cmd = ['onyo', '--yes', 'set', '-k', 'fzj_inventory=123A4', '-p', str(laptop)]
    ret = subprocess.run(cmd, capture_output=True, text=True)
    assert ret.returncode == 0

    # 4. Member switches workgroup
    # 4a. Member left display behind -> assign to their former group
    cmd = ['onyo', 'get', '-H', '-p', str(member), '--match', 'type=monitor']
    ret = subprocess.run(cmd, capture_output=True, text=True)
    assert ret.returncode == 0
    display = Path(ret.stdout.splitlines()[0].split('\t')[-1].strip("\""))
    cmd = ['onyo', '--yes', '--quiet', 'mv', str(display), str(member.parent)]
    ret = subprocess.run(cmd, capture_output=True, text=True)
    assert ret.returncode == 0

    # 4b. Move the user with remaining assets
    cmd = ['onyo', '--yes', '--quiet', 'mv', str(member), 'somegroup']
    ret = subprocess.run(cmd, capture_output=True, text=True)
    assert ret.returncode == 0
    member = Path('somegroup') / member.name

    # 5. Laptop gets an upgrade
    # 5a. Find based on inventory number
    cmd = ['onyo', 'get', '-H', '--match', 'fzj_inventory=123A4']
    ret = subprocess.run(cmd, capture_output=True, text=True)
    assert ret.returncode == 0
    laptop = Path(ret.stdout.splitlines()[0].split('\t')[-1].strip("\""))
    # 5b. Change recorded RAM size
    cmd = ['onyo', '--yes', 'set', '-k', 'RAM=16GB', '-p', str(laptop)]
    ret = subprocess.run(cmd, capture_output=True, text=True)
    assert ret.returncode == 0

    # 6. Member changes name
    member_new = member.parent / "Sam Married"
    cmd = ['onyo', '--yes', 'mv', str(member), str(member_new)]
    ret = subprocess.run(cmd, capture_output=True, text=True)
    assert ret.returncode == 0
    member = member_new

    # 7. Member leaves institute
    # 7a. Retire laptop
    cmd = ['onyo', 'get', '-H', '-p', str(member), '--match', "type=laptop"]
    ret = subprocess.run(cmd, capture_output=True, text=True)
    assert ret.returncode == 0
    laptop = Path(ret.stdout.splitlines()[0].split('\t')[-1].strip("\""))
    cmd = ['onyo', '--yes', 'mv', str(laptop), "retired"]
    ret = subprocess.run(cmd, capture_output=True, text=True)
    assert ret.returncode == 0
    laptop = Path("retired") / laptop.name
    # 7b. Remove member
    cmd = ['onyo', '--yes', 'rm', str(member)]
    ret = subprocess.run(cmd, capture_output=True, text=True)
    assert ret.returncode == 0

    #  QUERIES
    # 1. What is available in the warehouse?
    cmd = ['onyo', 'get', '-H', '-p', 'warehouse']
    ret = subprocess.run(cmd, capture_output=True, text=True)
    assert ret.returncode == 0
    # warehouse was prefilled with 6 assets. We previously took one display out.
    assert len(ret.stdout.splitlines()) == 5

    # 2. List all assets that have an FZJ inventory number
    cmd = ['onyo', 'get', '-H', '--match', 'fzj_inventory=.*']
    ret = subprocess.run(cmd, capture_output=True, text=True)
    assert ret.returncode == 0
    # Prefilled assets had 6, we purchased an additional laptop that got an inventory too
    assert len(ret.stdout.splitlines()) == 7

    # 3. Find an asset based on a key
    cmd = ['onyo', 'get', '-H', '--match', 'hostname=first.host']
    ret = subprocess.run(cmd, capture_output=True, text=True)
    assert ret.returncode == 0
    output_lines = ret.stdout.splitlines()
    assert len(output_lines) == 1
    assert "somegroup/userA/laptop_apple_macbook.9r5qlk" in output_lines[0]

    # 4. Find an asset bases on pseudo keys (particular laptop model)
    cmd = ['onyo', 'get', '-H', '--match', 'type=laptop', 'model=macbook']
    ret = subprocess.run(cmd, capture_output=True, text=True)
    assert ret.returncode == 0
    # We set up the repo with 3 macbooks
    assert len(ret.stdout.splitlines()) == 3

    # 5. Find all lenovo laptops used in a workgroup
    cmd = ['onyo', 'get', '-H', '-p', 'somegroup', '--match', 'make=lenovo']
    ret = subprocess.run(cmd, capture_output=True, text=True)
    assert ret.returncode == 0
    # 'somegroup' got an apple and a lenovo from the start;
    # second lenovo when user switched groups - was retired later;
    # One should remain:
    assert len(ret.stdout.splitlines()) == 1

    # All assets not in "retired" location of a certain type, that match something like
    # `"20160101 <= build-date <= 20171231"`
    # Apple recall on battery of all 13" MacBook Pros built between 2016-2017
    # -> query for all matching laptops not in 'retired'.

    # TODO: Not directly possible via CLI at the moment. Best I can think of is
    # `onyo get -H --match type=laptop --keys build-date -s | grep -v retired | grep -v unset`
    # and do the date comparison in a loop over its output.
    cmd = ['onyo', 'get', '-H', '--match', 'type=laptop', '--keys', 'build-date']
    ret = subprocess.run(cmd, capture_output=True, text=True)
    assert ret.returncode == 0
    results = []
    for date, path in [line.split('\t') for line in ret.stdout.splitlines()]:
        date = date.strip("\"")
        path = path.strip("\"")
        if "retired" in path or date == "<unset>":
            continue
        if 20160101 <= int(date) <= 20171231:
            results.append(path)
    # We have:
    # - one macbook matching display but not build date
    # - one lenovo matching the build date
    # - one actual match in warehouse
    # - one match in retired
    # -> only one hit overall
    assert len(results) == 1
    assert results[0] == "warehouse/laptop_apple_macbook.oiw629"

    # 6. History of an asset
    # Tell the history of the retired laptop
    cmd = ['onyo', 'history', '-I', str(laptop)]
    ret = subprocess.run(cmd, capture_output=True, text=True)
    assert ret.returncode == 0

    # TODO: No assertions yet. History seems insufficiently defined ATM.
