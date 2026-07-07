# sparkmeter

<small>Also known as ThunderCloud (when deployed to the cloud) or GroundBolt (when deployed to the base station on the ground)</small>
___

A web application used by utility companies to manage their micro-grids remotely.

## Contributing

We accept merge requests! Read the instructions in our [contribution guidelines](/CONTRIBUTING.md) for more details.

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

For Docker deployments, prefix commands with `docker compose exec`:
```bash
docker compose exec ground uv run flask user create
```

## Development

This document is to help you get the development environment up and running. You can choose between two options, hit either of the links below for more details:

1. [Docker](#docker)
2. [Local](#local)


### Docker


For a fully Dockerized development environment:

```bash
$ docker compose up
```

Pass `-d` to detach. Run with `--watch` to enable Compose's develop watcher, which rebuilds the `ground` and `cloud` images on file changes (note: full image rebuild, not Flask hot-reload — slow for iterative work, useful for verifying built behavior).

#### 1. Build docker services

`docker compose up` builds any missing images automatically, so this step is optional. Run it when you want to force a clean rebuild (e.g. after Dockerfile or dependency changes):

```bash
$ docker compose build --no-cache
```

#### 2. Run the built docker services

The default Compose profile brings up the ground-side stack:

```bash
$ docker compose up -d
```

After it settles, `docker compose ps` shows:

```
ground             # the GroundBolt webapp
postgres-ground    # its database
metering-provider  # the service the ground app calls for meter operations
symds-ground       # SymmetricDS node syncing the ground database
```

The ground webapp talks to the metering provider over an OpenAPI HTTP+SSE contract, configured via `METERING_PROVIDER_URL` (default `http://localhost:8000`). The Compose file references the provider image by tag. That image must be present locally; build or pull it under that tag before bringing up the ground stack.

The cloud-side stack lives behind the `cloud` Compose profile. To also bring up the cloud webapp and the cloud-side SymmetricDS node:

```bash
$ docker compose --profile cloud up -d
```

That adds:

```
cloud           # the ThunderCloud webapp
postgres-cloud  # its database
symds-cloud     # SymmetricDS node syncing the cloud database
```

`symds-ground` and `symds-cloud` together provide bidirectional sync between the ground and cloud databases. With only the ground profile active, `symds-ground` runs but has nothing to sync against until `--profile cloud` brings up `symds-cloud`.

#### 3. Voilà! Your development environment is ready!

- The GroundBolt webapp (`ground` container) is at [localhost:8765](http://localhost:8765).
- With `--profile cloud`, the ThunderCloud webapp (`cloud` container) is at [localhost:5010](http://localhost:5010).

#### Useful commands

##### Run unit tests

```bash
$ docker compose --profile test run --rm test
```

##### Run a subset of unit tests

Override the `test` service's command with a pytest invocation. Any pytest arguments can be passed:

```bash
$ docker compose --profile test run --rm test uv run pytest <path/to/test>[::ClassName][::method_name]
```

For example, running the tests for the AddCustomer endpoint in the API:

```bash
docker compose --profile test run --rm test uv run pytest sparkmeter/api/tests/test_customerviews0.py::CustomerAddTest
```

##### Create a new database migration

Database schema migrations are managed via Alembic.  To get started, you must first create a migration file.

```bash
docker compose exec ground uv run flask database new-revision "<short description of the migration>"
```

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
