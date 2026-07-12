#!/usr/bin/env python
"""Release script for sparkmeter."""

import logging
import subprocess
import sys

import urlparse

logger = logging.getLogger("create-branch")


def parse_revision(tag):
    """Get the name of the current branch."""
    try:
        output = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", tag])
    except subprocess.CalledProcessError:
        raise LookupError("no such revision: {}".format(tag))
    return output.rstrip()


def get_remote(name):
    """Get the url for a remote.

    :param name: name of the remote
    """
    return subprocess.check_output(["git", "config", "--get", "remote.{}.url".format(name)])


def create_branch(branch, start):
    """
    Create a new gerrit branch.

    :param branch: name of the branch
    :param start: starting point of the branch
    """
    url = urlparse.urlparse(get_remote("gerrit"))
    host, port = url.netloc.split(":")
    subprocess.call(
        [
            "ssh",
            "-p",
            port,
            host,
            "gerrit",
            "create-branch",
            "sparkmeter",
            branch,
            start,
        ]
    )


def main(args):
    """Release script entrypoint."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(name)-8s %(message)s",
    )
    if len(args) != 3:
        logging.error("Usage: {} BRANCH STARTING-POINT".format(args[0]))
        return 1

    branch = args[1]
    if not branch.startswith("v") or not branch.endswith(".x"):
        logging.error("Branch must be formatted like v1.7.0")
        return 1

    start = parse_revision(args[2])
    create_branch(branch, start)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
