# sparkmeter

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

Thanks goes to these wonderful people ([emoji key](https://allcontributors.org/docs/en/emoji-key)):

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->
<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind welcome!
