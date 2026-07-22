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

Relevant coding style guidelines are outlined in [CodingStyle.md](CodingStyle.md). You can use [autopep8](https://pypi.org/project/autopep8/) to automatically format your contribution. Ensure contributions are properly formatted before submitting a Pull Request.


## Reporting Feature Requests, Bugs and other Issues

If you find a bug in ThunderCloud, please file a detailed report as a GitHub Issue. We currently do not utilize an Issue template, but please be as thorough as possible in your report. There is no such thing as too much information.

Likewise, if you have a Feature Request, please file a detailed Issue, explaining the feature's functionality and use cases. New Features should be beneficial to the broader community, so be sure to consider that before filing.
