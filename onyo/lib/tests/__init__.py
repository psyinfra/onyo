from onyo.lib.inventory import Inventory


def check_commit_msg(inventory: Inventory,
                     message: str | None,
                     auto_message: bool,
                     cmd_prefix: str):
    commit_msg = inventory.repo.git.get_commit_msg().splitlines()
    assert bool(cmd_prefix in commit_msg[0]) == bool(auto_message)
    # There's always an operation record.
    # Note, that index() raises if the string isn't found
    op_idx = commit_msg.index("--- Inventory Operations ---")
    assert op_idx > 0  # It's never in the subject line
    if message:
        # If a message was provided, it's inserted before the operations record.
        # If the subject is auto generated, `message` is inserted after:
        assert message in "".join(commit_msg[1 if auto_message else 0:op_idx])
