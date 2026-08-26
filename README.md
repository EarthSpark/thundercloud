# sparkmeter
<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-19-orange.svg?style=flat-square)](#contributors-)
<!-- ALL-CONTRIBUTORS-BADGE:END -->

<small>Also known as ThunderCloud (when deployed to the cloud) or GroundBolt (when deployed to the base station on the ground)</small>
___

> [!WARNING]
> **Developer preview — not for production use.**
>
> This version is a developer preview, intended for evaluation and development
> only. It is not ready to manage a live micro-grid and must not be deployed to
> production or used for real customer metering or billing. Expect breaking
> changes between preview versions.

A web application used by utility companies to manage their micro-grids remotely.

## Contributing

We accept pull requests! Read the instructions in our [contribution guidelines](/CONTRIBUTING.md) for more details.

## Flask CLI Commands

SparkMeter uses Flask CLI for management commands. All commands use `uv run flask` as the prefix.

### User Management

```bash
# Create a user (interactive)
uv run flask user create

# Create a user with options
uv run flask user create -u username -e email@example.com -p password -r operator

# List all users
uv run flask user list
```

Available roles: `operator` (admin), `vendor`, `api`

### Meter Management

```bash
# Create a new meter
uv run flask meter create -s SERIAL_NUMBER

# Create a meter with address
uv run flask meter create -s SERIAL_NUMBER --street1 "123 Main St"

# Remove a meter
uv run flask meter remove -s SERIAL_NUMBER

# Convert customer meter to totalizer
uv run flask meter convert-to-totalizer -s SERIAL_NUMBER

# Convert totalizer to customer meter
uv run flask meter convert-to-customer -s SERIAL_NUMBER -t TARIFF_NAME
```

### Tariff Management

```bash
# Create a new tariff
uv run flask tariff create -n TARIFF_NAME -r RATE [-l LOAD_LIMIT]

# Example: Create tariff with rate 80 and load limit 12W
uv run flask tariff create -n ET1 -r 80 -l 12

# List all tariffs
uv run flask tariff list
```

### Database Management

```bash
# Reset the database
uv run flask database reset --force

# Reset and load demo data
uv run flask database reset-demo --force
```

The bare commands `resetdb`, `demo`, and `initdb` still work as deprecated aliases.

### Other Commands

```bash
# Run development server
uv run flask run

# Open interactive shell
uv run flask shell

# Show application status
uv run flask status
```

For Docker deployments, run the same commands inside the webapp container with `docker compose exec`:
```bash
docker compose exec ground uv run flask user create
```

## Development

This document is to help you get the development environment up and running. You can choose between two options, hit either of the links below for more details:

1. [Docker](#docker)
2. [Local](#local)


### Docker

Dockerized development happens in the **groundbolt-dev workspace metarepo**, which clones this repo and its sibling component repos side by side and runs the whole system — the ground and cloud webapps, their databases, the SymmetricDS sync pair, and the `sparknet-http` metering provider — from a single compose file. See that repo's README for setup.

This repo's `docker-compose.test.yml` is the self-contained test harness: a throwaway Postgres plus the test-image runner, needing nothing outside this repo. It's what CI runs.

#### Useful commands

##### Run unit tests

```bash
$ docker compose -f docker-compose.test.yml run --rm test
```

##### Run a subset of unit tests

Override the `test` service's command with a pytest invocation. Any pytest arguments can be passed:

```bash
$ docker compose -f docker-compose.test.yml run --rm test uv run pytest <path/to/test>[::ClassName][::method_name]
```

For example, running the tests for the AddCustomer endpoint in the API:

```bash
docker compose -f docker-compose.test.yml run --rm test uv run pytest sparkmeter/api/tests/test_customerviews0.py::CustomerAddTest
```

##### Create a new database migration

Database schema migrations are managed via Alembic.  To get started, you must first create a migration file:

```bash
uv run flask database new-revision "<short description of the migration>"
```

(Or run the same command inside the webapp container of a running Docker stack, via `docker compose exec`.)

This will generate a skeleton migration file in `sparkmeter/alembic/versions/`. From there, customize it your liking.

##### Tail the logs of a service

Logs for a single service can be tailed via

```bash
$ docker compose logs <service> --tail=500
```

Live logs from a service can be streamed via

```bash
$ docker compose logs <service> -f
```

To follow every service's logs in one stream:

```bash
$ docker compose logs -f
```

### Local


To setup a development environment locally, you need to follow the steps below:

#### 1. Setup the project and install the dependencies

Head to the [dependencies section](#installing-dependencies) and make sure you have all the necessary tools installed before you proceed with this step.

```bash
$ uv sync --group dev
```

#### 2. Create the database

For an empty database:

```bash
$ uv run flask database reset --force
```

Or, for a database pre-populated with demo data (this also resets, so there's no need to run both):

```bash
$ uv run flask database reset-demo --force
```

#### 3. Create an admin user

Create an operator (admin) user:

```bash
$ uv run flask user create -u admin -e admin@example.com -p password -r operator
```

Or interactively:

```bash
$ uv run flask user create
```

#### 4. Run the server
1. You can now run the development web server using the following command:

    ```bash
    $ uv run flask run
    ```

2. Open up your browser, and go http://localhost:5000/ and login with the credentials you created.


### Installing Dependencies

#### Python Requirements

The requirements are kept in `pyproject.toml` where only the actual modules we want installed are kept. All child dependencies are calculated using `uv` to generate a `uv.lock` file of pinned packages.

The requirements are split into two groups. `[project] dependencies` holds only production requirements. `[dependency-groups] dev` is the development-only group.

To resync the venv from the lockfile:

```bash
uv sync --group dev
```

#### OS Requirements

Install `uv` per the instructions at [docs.astral.sh/uv/getting-started/installation](https://docs.astral.sh/uv/getting-started/installation/). `uv` manages Python, the virtual environment, and the locked dependencies.

If you plan to run the database locally (instead of via the `postgres-ground` Compose service), install PostgreSQL too.

If you plan to work on frontend assets under `scripts/config/`, install Node.js as well.

##### Ubuntu

    $ sudo apt-get update
    $ sudo apt-get install postgresql       # only for local-DB workflows
    $ sudo apt-get install nodejs npm       # only for frontend work

##### macOS

Install Homebrew per the instructions at [brew.sh](https://brew.sh), then:

    $ brew install postgresql               # only for local-DB workflows
    $ brew install node                     # only for frontend work

## Contributors

Thanks goes to these wonderful people ([emoji key](https://allcontributors.org/en/reference/emoji-key/#contributions)):
<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tbody>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/tescalada"><img src="https://avatars.githubusercontent.com/u/355457?v=4?s=100" width="100px;" alt="Tristan Escalada"/><br /><sub><b>Tristan Escalada</b></sub></a><br /><a href="https://github.com/EarthSpark/thundercloud/commits?author=tescalada" title="Code">💻</a> <a href="https://github.com/EarthSpark/thundercloud/commits?author=tescalada" title="Documentation">📖</a> <a href="#infra-tescalada" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a> <a href="#security-tescalada" title="Security">🛡️</a> <a href="#ideas-tescalada" title="Ideas, Planning, & Feedback">🤔</a> <a href="#maintenance-tescalada" title="Maintenance">🚧</a> <a href="#platform-tescalada" title="Packaging/porting to new platform">📦</a> <a href="https://github.com/EarthSpark/thundercloud/pulls?q=is%3Apr+reviewed-by%3Atescalada" title="Reviewed Pull Requests">👀</a> <a href="#tool-tescalada" title="Tools">🔧</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/AGLJCM"><img src="https://avatars.githubusercontent.com/u/5478635?v=4?s=100" width="100px;" alt="Arthur Jacquiau-Chamski"/><br /><sub><b>Arthur Jacquiau-Chamski</b></sub></a><br /><a href="https://github.com/EarthSpark/thundercloud/issues?q=author%3AAGLJCM" title="Bug reports">🐛</a> <a href="#business-AGLJCM" title="Business development">💼</a> <a href="https://github.com/EarthSpark/thundercloud/commits?author=AGLJCM" title="Code">💻</a> <a href="#data-AGLJCM" title="Data">🔣</a> <a href="https://github.com/EarthSpark/thundercloud/commits?author=AGLJCM" title="Documentation">📖</a> <a href="#design-AGLJCM" title="Design">🎨</a> <a href="#example-AGLJCM" title="Examples">💡</a> <a href="#ideas-AGLJCM" title="Ideas, Planning, & Feedback">🤔</a> <a href="#mentoring-AGLJCM" title="Mentoring">🧑‍🏫</a> <a href="#platform-AGLJCM" title="Packaging/porting to new platform">📦</a> <a href="#projectManagement-AGLJCM" title="Project Management">📆</a> <a href="#question-AGLJCM" title="Answering Questions">💬</a> <a href="#research-AGLJCM" title="Research">🔬</a> <a href="https://github.com/EarthSpark/thundercloud/pulls?q=is%3Apr+reviewed-by%3AAGLJCM" title="Reviewed Pull Requests">👀</a> <a href="#tool-AGLJCM" title="Tools">🔧</a> <a href="#translation-AGLJCM" title="Translation">🌍</a> <a href="https://github.com/EarthSpark/thundercloud/commits?author=AGLJCM" title="Tests">⚠️</a> <a href="#tutorial-AGLJCM" title="Tutorials">✅</a> <a href="#userTesting-AGLJCM" title="User Testing">📓</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/jdahlin"><img src="https://avatars.githubusercontent.com/u/76610?v=4?s=100" width="100px;" alt="Johan Dahlin"/><br /><sub><b>Johan Dahlin</b></sub></a><br /><a href="https://github.com/EarthSpark/thundercloud/commits?author=jdahlin" title="Code">💻</a> <a href="https://github.com/EarthSpark/thundercloud/commits?author=jdahlin" title="Documentation">📖</a> <a href="#infra-jdahlin" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a> <a href="#security-jdahlin" title="Security">🛡️</a> <a href="#ideas-jdahlin" title="Ideas, Planning, & Feedback">🤔</a> <a href="#maintenance-jdahlin" title="Maintenance">🚧</a> <a href="#platform-jdahlin" title="Packaging/porting to new platform">📦</a> <a href="https://github.com/EarthSpark/thundercloud/pulls?q=is%3Apr+reviewed-by%3Ajdahlin" title="Reviewed Pull Requests">👀</a> <a href="#tool-jdahlin" title="Tools">🔧</a> <a href="https://github.com/EarthSpark/thundercloud/commits?author=jdahlin" title="Tests">⚠️</a> <a href="#design-jdahlin" title="Design">🎨</a> <a href="#translation-jdahlin" title="Translation">🌍</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/shawnchurchill"><img src="https://avatars.githubusercontent.com/u/178503568?v=4?s=100" width="100px;" alt="shawnchurchill"/><br /><sub><b>shawnchurchill</b></sub></a><br /><a href="https://github.com/EarthSpark/thundercloud/commits?author=shawnchurchill" title="Tests">⚠️</a> <a href="#infra-shawnchurchill" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/hollomancer"><img src="https://avatars.githubusercontent.com/u/9288648?v=4?s=100" width="100px;" alt="Conrad Hollomon"/><br /><sub><b>Conrad Hollomon</b></sub></a><br /><a href="https://github.com/EarthSpark/thundercloud/commits?author=hollomancer" title="Code">💻</a> <a href="https://github.com/EarthSpark/thundercloud/commits?author=hollomancer" title="Tests">⚠️</a> <a href="https://github.com/EarthSpark/thundercloud/commits?author=hollomancer" title="Documentation">📖</a> <a href="#infra-hollomancer" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/xovox"><img src="https://avatars.githubusercontent.com/u/20759483?v=4?s=100" width="100px;" alt="Duncan"/><br /><sub><b>Duncan</b></sub></a><br /><a href="#infra-xovox" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a> <a href="#tool-xovox" title="Tools">🔧</a> <a href="#maintenance-xovox" title="Maintenance">🚧</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://thelawrencemoore.com/"><img src="https://avatars.githubusercontent.com/u/2665198?v=4?s=100" width="100px;" alt="Lawrence Moore"/><br /><sub><b>Lawrence Moore</b></sub></a><br /><a href="https://github.com/EarthSpark/thundercloud/commits?author=MyLightIsOn" title="Code">💻</a> <a href="https://github.com/EarthSpark/thundercloud/commits?author=MyLightIsOn" title="Tests">⚠️</a> <a href="#design-MyLightIsOn" title="Design">🎨</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/seoheunl"><img src="https://avatars.githubusercontent.com/u/16997987?v=4?s=100" width="100px;" alt="Sally Lee"/><br /><sub><b>Sally Lee</b></sub></a><br /><a href="https://github.com/EarthSpark/thundercloud/commits?author=seoheunl" title="Code">💻</a> <a href="https://github.com/EarthSpark/thundercloud/commits?author=seoheunl" title="Tests">⚠️</a> <a href="https://github.com/EarthSpark/thundercloud/commits?author=seoheunl" title="Documentation">📖</a> <a href="#infra-seoheunl" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/concordion2k"><img src="https://avatars.githubusercontent.com/u/4155023?v=4?s=100" width="100px;" alt="Dan"/><br /><sub><b>Dan</b></sub></a><br /><a href="https://github.com/EarthSpark/thundercloud/commits?author=concordion2k" title="Code">💻</a> <a href="https://github.com/EarthSpark/thundercloud/commits?author=concordion2k" title="Tests">⚠️</a> <a href="#infra-concordion2k" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/jthacker"><img src="https://avatars.githubusercontent.com/u/452244?v=4?s=100" width="100px;" alt="Jon Thacker"/><br /><sub><b>Jon Thacker</b></sub></a><br /><a href="https://github.com/EarthSpark/thundercloud/commits?author=jthacker" title="Code">💻</a> <a href="https://github.com/EarthSpark/thundercloud/commits?author=jthacker" title="Tests">⚠️</a> <a href="https://github.com/EarthSpark/thundercloud/commits?author=jthacker" title="Documentation">📖</a> <a href="#infra-jthacker" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://arusahni.net/"><img src="https://avatars.githubusercontent.com/u/139487?v=4?s=100" width="100px;" alt="Aru Sahni"/><br /><sub><b>Aru Sahni</b></sub></a><br /><a href="https://github.com/EarthSpark/thundercloud/commits?author=arusahni" title="Code">💻</a> <a href="https://github.com/EarthSpark/thundercloud/commits?author=arusahni" title="Tests">⚠️</a> <a href="https://github.com/EarthSpark/thundercloud/commits?author=arusahni" title="Documentation">📖</a> <a href="#infra-arusahni" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a> <a href="#design-arusahni" title="Design">🎨</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/billyoung"><img src="https://avatars.githubusercontent.com/u/473429?v=4?s=100" width="100px;" alt="Bill Young"/><br /><sub><b>Bill Young</b></sub></a><br /><a href="#infra-billyoung" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/ben-postman"><img src="https://avatars.githubusercontent.com/u/51209752?v=4?s=100" width="100px;" alt="Ben Postman"/><br /><sub><b>Ben Postman</b></sub></a><br /><a href="#tool-ben-postman" title="Tools">🔧</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/sheshtawy"><img src="https://avatars.githubusercontent.com/u/5498393?v=4?s=100" width="100px;" alt="Hisham Elsheshtawy"/><br /><sub><b>Hisham Elsheshtawy</b></sub></a><br /><a href="https://github.com/EarthSpark/thundercloud/commits?author=sheshtawy" title="Code">💻</a> <a href="https://github.com/EarthSpark/thundercloud/commits?author=sheshtawy" title="Tests">⚠️</a> <a href="https://github.com/EarthSpark/thundercloud/commits?author=sheshtawy" title="Documentation">📖</a> <a href="#infra-sheshtawy" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://www.linkedin.com/in/martin-r-wagner/"><img src="https://avatars.githubusercontent.com/u/4905977?v=4?s=100" width="100px;" alt="Martin Wagner"/><br /><sub><b>Martin Wagner</b></sub></a><br /><a href="https://github.com/EarthSpark/thundercloud/commits?author=mw23" title="Code">💻</a> <a href="https://github.com/EarthSpark/thundercloud/commits?author=mw23" title="Tests">⚠️</a> <a href="#infra-mw23" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a> <a href="#design-mw23" title="Design">🎨</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/dberliner"><img src="https://avatars.githubusercontent.com/u/3488019?v=4?s=100" width="100px;" alt="Daniel Berliner"/><br /><sub><b>Daniel Berliner</b></sub></a><br /><a href="https://github.com/EarthSpark/thundercloud/commits?author=dberliner" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/sampscl"><img src="https://avatars.githubusercontent.com/u/358749?v=4?s=100" width="100px;" alt="Clay Sampson"/><br /><sub><b>Clay Sampson</b></sub></a><br /><a href="#infra-sampscl" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a> <a href="#maintenance-sampscl" title="Maintenance">🚧</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/LyncTechLLC"><img src="https://avatars.githubusercontent.com/u/19625522?v=4?s=100" width="100px;" alt="LyncTechLLC"/><br /><sub><b>LyncTechLLC</b></sub></a><br /><a href="https://github.com/EarthSpark/thundercloud/commits?author=LyncTechLLC" title="Code">💻</a> <a href="https://github.com/EarthSpark/thundercloud/issues?q=author%3ALyncTechLLC" title="Bug reports">🐛</a> <a href="https://github.com/EarthSpark/thundercloud/commits?author=LyncTechLLC" title="Documentation">📖</a> <a href="#design-LyncTechLLC" title="Design">🎨</a> <a href="#ideas-LyncTechLLC" title="Ideas, Planning, & Feedback">🤔</a> <a href="#maintenance-LyncTechLLC" title="Maintenance">🚧</a> <a href="#plugin-LyncTechLLC" title="Plugin/utility libraries">🔌</a> <a href="#security-LyncTechLLC" title="Security">🛡️</a> <a href="#tool-LyncTechLLC" title="Tools">🔧</a> <a href="https://github.com/EarthSpark/thundercloud/commits?author=LyncTechLLC" title="Tests">⚠️</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/jranson"><img src="https://avatars.githubusercontent.com/u/883928?v=4?s=100" width="100px;" alt="James Ranson"/><br /><sub><b>James Ranson</b></sub></a><br /><a href="https://github.com/EarthSpark/thundercloud/commits?author=jranson" title="Documentation">📖</a> <a href="#infra-jranson" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a> <a href="#security-jranson" title="Security">🛡️</a></td>
    </tr>
  </tbody>
  <tfoot>
    <tr>
      <td align="center" size="13px" colspan="7">
        <img src="https://raw.githubusercontent.com/all-contributors/all-contributors-cli/1b8533af435da9854653492b1327a23a4dbd0a10/assets/logo-small.svg">
          <a href="https://all-contributors.js.org/docs/en/bot/usage">Add your contributions</a>
        </img>
      </td>
    </tr>
  </tfoot>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind welcome!
