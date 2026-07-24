# Contributing

This project welcomes contributions. If you have a trivial fix or improvement, go ahead and create a pull request with the change. However, if you plan to do something more involved, first file an issue to discuss it with the project maintainers. This will avoid unnecessary work that may not be accepted.

Should you wish to work on an open, unassigned GitHub Issue, please claim it first by commenting on the issue that you want to work on it and wait for it to be assigned. This prevents duplicated efforts from contributors on the same issue. If you have questions about one of the issues, please leave a comment on it and one of the maintainers will clarify.

### Steps to Contribute
 
 * If you have not already, fork the GitHub repository
 * Clone your fork (not the base repository) locally 
 * In your local repository, create a new branch for your contribution
 * Make the desired changes and commit to your branch. Commits should be as small as possible, while ensuring that each commit is correct independently (e.g., each commit should compile and pass tests).
 * Push the branch back to your remote fork on GitHub
 * Submit a Pull Request to the base repository via GitHub

### Before Submitting a Pull Request

Test all contributions locally before submitting Pull Requests by running `./run_tests.sh` from the project root or in a docker container via `docker compose -f docker-compose.test.yml run --rm test`.

Relevant coding style guidelines are outlined in [CodingStyle.md](CodingStyle.md). This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting; run `uv run ruff format .` to format and `uv run ruff check .` to lint before submitting a Pull Request. Both run in CI, and the [pre-commit](https://pre-commit.com) hooks in `.pre-commit-config.yaml` apply them automatically on commit once installed with `uv run pre-commit install`.


## Recognizing Contributions

This project uses the [All Contributors](https://allcontributors.org) bot to recognize everyone who helps out, for contributions of any kind — not just code. To add someone (or yourself) to the Contributors list in the README, comment on an issue or pull request:

> @all-contributors please add @username for code, doc, test

See the [emoji key](https://allcontributors.org/docs/en/emoji-key) for the full list of contribution types. The bot opens a pull request updating the README and `.all-contributorsrc`.


## Reporting Feature Requests, Bugs and other Issues

If you find a bug in ThunderCloud, please file a detailed report as a GitHub Issue. We currently do not utilize an Issue template, but please be as thorough as possible in your report. There is no such thing as too much information.

Likewise, if you have a Feature Request, please file a detailed Issue, explaining the feature's functionality and use cases. New Features should be beneficial to the broader community, so be sure to consider that before filing.
