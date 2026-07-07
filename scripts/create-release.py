#!/usr/bin/env python
"""Release script for sparkmeter."""
import collections
import logging
import os
import re
import subprocess
import sys

logger = logging.getLogger('create-release')
BaseVersionInfo = collections.namedtuple('VersionInfo', 'major minor patch')


class VersionInfo(BaseVersionInfo):

    """Represents a version."""

    def __str__(self):
        """String representation, like 1.2.3."""
        return "{0.major}.{0.minor}.{0.patch}".format(self)

    @property
    def tag_name(self):
        """Git tag name, like v1.2.3."""
        return 'v{}'.format(self)

    @property
    def message(self):
        """Git commit message, like 'Release 1.2.3'."""
        return 'Release {}'.format(self)


def update_version(version_info):
    """Update __version__.py with the supplied version_info."""
    logger.info("Updating __version__.py")
    path = os.path.join(
        os.path.dirname(__file__), '..', 'sparkmeter', '__version__.py')
    with open(path, 'rt') as f:
        data = f.read()
    for name, value in zip(['major', 'minor', 'patch'],
                           version_info):
        data = re.sub(
            r'{} = \d+'.format(name),
            '{} = {}'.format(name, value),
            data)

    with open(path, 'wt') as f:
        f.write(data)


def git_commit(version_info):
    """Commit the git release message."""
    logger.info("Creating git commit")
    subprocess.check_call(
        ["git", "commit",
         "-m", version_info.message,
         "sparkmeter/__version__.py"])


def git_tag(version_info):
    """Tag the commit."""
    logger.info("Creating git tag")
    subprocess.check_call(
        ["git", "tag",
         "-am", version_info.message,
         version_info.tag_name])


def git_fetch():
    """Fetch data from git."""
    logger.info("Fetching from git")
    subprocess.check_call(["git", "fetch", "--all"])


def git_rebase_origin(branch):
    """Rebase git origin."""
    logger.info("Rebasing from origin/{}".format(branch))
    subprocess.check_call(["git", "rebase", "origin/" + branch])


def git_show_log():
    """Show the last 3 git commits on screen."""
    logger.info("Showing log")
    subprocess.check_call(["git", "log", "-n", "3"])


def get_branch():
    """Get the name of the current branch."""
    output = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'])
    return output.rstrip()


def git_push(branch, version_info):
    """Push a git commit and tag."""
    logger.info("Pushing git tag")
    subprocess.check_call(
        ["git", "push", "origin", "{0}:refs/tags/{0}".format(version_info.tag_name)])

    logger.info("Pushing HEAD to {}, submitting directly, skipping review".format(branch))
    subprocess.check_call(
        ["git", "push", "origin", "HEAD:refs/for/{}%submit".format(branch)])


def main(args):
    """Release script entrypoint."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(name)-8s %(message)s',
    )
    if len(args) != 2:
        logging.error("Usage: {} VERSION".format(args[0]))
        return 1
    version = args[1]
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)$', version)
    if match is None:
        logging.error("Invalid version: {!r}, must be X.Y.Z".format(version))
        return 1
    version_info = VersionInfo(*map(int, match.groups()))
    branch = get_branch()
    git_fetch()
    git_rebase_origin(branch)
    update_version(version_info)
    git_commit(version_info)
    git_tag(version_info)
    git_show_log()
    response = raw_input("About to release {} on branch {}, confirm? [y/N] ".format(version, branch))
    if response != 'y':
        logging.error("Aborting, will revert commit, modifications and tag")
        subprocess.check_call(['git', 'reset', '-q', 'HEAD^'])
        subprocess.check_call(['git', 'checkout', '-q', 'sparkmeter/__version__.py'])
        subprocess.check_call(['git', 'tag', '-d', version_info.tag_name])
        return 1

    git_push(branch, version_info)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
