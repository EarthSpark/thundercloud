# Stage 1: Build JS/CSS assets
FROM node:20-alpine AS assets
WORKDIR /app
COPY scripts/config/package.json scripts/config/package.json
RUN cd scripts/config && npm install
COPY scripts/config/webpack.config.js scripts/config/webpack.config.js
COPY assets assets
COPY sparkmeter sparkmeter

# Build application.js (webpack)
RUN mkdir -p static/javascripts && \
    ./scripts/config/node_modules/.bin/webpack \
      --optimize-minimize \
      --config scripts/config/webpack.config.js \
      --output-path static/javascripts

# Build vendor.js (uglifyjs)
RUN ./scripts/config/node_modules/.bin/uglifyjs \
      --compress warnings=false --mangle \
      --output static/javascripts/vendor.js \
      assets/javascripts/vendor/jquery-1.10.2.js \
      assets/javascripts/vendor/bootstrap/affix.js \
      assets/javascripts/vendor/bootstrap/alert.js \
      assets/javascripts/vendor/bootstrap/button.js \
      assets/javascripts/vendor/bootstrap/carousel.js \
      assets/javascripts/vendor/bootstrap/collapse.js \
      assets/javascripts/vendor/bootstrap/dropdown.js \
      assets/javascripts/vendor/bootstrap/tab.js \
      assets/javascripts/vendor/bootstrap/transition.js \
      assets/javascripts/vendor/bootstrap/modal.js \
      assets/javascripts/vendor/bootstrap/scrollspy.js \
      assets/javascripts/vendor/bootstrap/tooltip.js \
      assets/javascripts/vendor/bootstrap/popover.js \
      assets/javascripts/vendor/jquery_gritter.js \
      assets/javascripts/vendor/jquery.datetimepicker.js \
      assets/javascripts/vendor/select2.js \
      assets/javascripts/vendor/d3.js \
      assets/javascripts/vendor/vega.js \
      assets/javascripts/vendor/justgage/raphael.2.1.0.min.js \
      assets/javascripts/vendor/justgage/justgage.1.0.1.js \
      assets/javascripts/vendor/jquery.easy-pie-chart.js \
      assets/javascripts/vendor/datatables/jquery.dataTables.js \
      assets/javascripts/vendor/datatables/dataTables.bootstrap.js \
      assets/javascripts/vendor/datatables/dataTables.buttons.js \
      assets/javascripts/vendor/datatables/buttons.flash.js \
      assets/javascripts/vendor/datatables/buttons.html5.js \
      assets/javascripts/vendor/datatables/dataTables.fixedHeader.js \
      assets/javascripts/vendor/ibutton/jquery.easing.1.3.js \
      assets/javascripts/vendor/ibutton/jquery.metadata.js \
      assets/javascripts/vendor/ibutton/jquery.ibutton.js \
      assets/javascripts/vendor/jquery.numeric.js \
      assets/javascripts/vendor/angular-1.4.9.js \
      assets/javascripts/vendor/angular-resource-1.4.9.js \
      assets/javascripts/vendor/ui-bootstrap-custom-tpls-1.1.1.js \
      assets/javascripts/vendor/ng-textcomplete-0.6.0.js \
      assets/javascripts/vendor/tlite.js

# Build application.css (sass)
RUN mkdir -p static/stylesheets && \
    ./scripts/config/node_modules/.bin/sass \
      --quiet --style compressed \
      --load-path assets/stylesheets/ \
      --load-path scripts/config/node_modules/compass-mixins/lib/ \
      assets/stylesheets/application.scss static/stylesheets/application.css

# Stage 2: Install Python dependencies
FROM astral/uv:python3.13-alpine AS builder

RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    libffi-dev \
    postgresql-dev \
    linux-headers \
    git

WORKDIR /app

COPY pyproject.toml pyproject.toml
COPY uv.lock uv.lock
COPY README.md README.md
# `.git` is needed for hatch-vcs to derive the version from tags.
# `sparkmeter/` is needed because the project install runs the build
# backend (hatchling + hatch-vcs), which reads source. Both are
# discarded after this stage; production only inherits `.venv` and
# `sparkmeter/` (the latter with `_version.py` written by hatch-vcs).
COPY .git .git
COPY sparkmeter sparkmeter

# Supply the version explicitly when the build context has no usable .git —
# e.g. a git worktree, whose .git is a file pointing outside the context, so
# hatch-vcs/setuptools-scm cannot derive the version. Empty (the default)
# leaves hatch-vcs to read .git as usual. sparkmeter is the only source build
# in this step, so the global (non-dist-scoped) variable is unambiguous here.
ARG SETUPTOOLS_SCM_PRETEND_VERSION=""
RUN SETUPTOOLS_SCM_PRETEND_VERSION="$SETUPTOOLS_SCM_PRETEND_VERSION" \
    uv sync --locked --no-dev

RUN apk del .build-deps

# Stage 3: Final runtime image (production)
FROM astral/uv:python3.13-alpine AS production

# Install runtime dependencies for PostgreSQL, git so that `uv` can
# resolve git-sourced dependencies at runtime, and curl for the compose
# healthcheck (which probes /health from inside the container).
RUN apk add --no-cache postgresql-libs postgresql-client git curl

# Create spark user
RUN addgroup -g 1000 spark && \
    adduser -D -u 1000 -G spark spark

# Directories the webapp writes to at runtime (logs, pid files). Two fixed
# inodes -- the only ownership change the image makes.
RUN chown spark /var/log /var/run

# Everything below is created owned by spark, rather than written as root and
# chowned afterward: switch to the spark user before WORKDIR (so /app itself is
# created spark-owned) and tag every COPY with --chown=spark:spark. This is why
# the test stage needs no recursive chown over the app tree.
USER spark
WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --chown=spark:spark --from=builder /app/.venv .venv

# Copy `sparkmeter/` from the builder stage so it includes the
# hatch-vcs-generated `_version.py`, rather than from the host (which
# may not have it on a fresh checkout).
COPY --chown=spark:spark --from=builder /app/sparkmeter sparkmeter
COPY --chown=spark:spark --from=assets /app/static/javascripts static/javascripts
COPY --chown=spark:spark --from=assets /app/static/stylesheets static/stylesheets
COPY --chown=spark:spark static/fonts static/fonts
COPY --chown=spark:spark static/images static/images
COPY --chown=spark:spark static/logo static/logo
COPY --chown=spark:spark static/swf static/swf
COPY --chown=spark:spark .flaskenv .flaskenv
COPY --chown=spark:spark messages.pot messages.pot
COPY --chown=spark:spark pyproject.toml pyproject.toml
COPY --chown=spark:spark uv.lock uv.lock
COPY --chown=spark:spark run/webapp run/webapp

# 5000 = public listener (mapped to host port 80 in production).
# 5001 = internal listener (admin endpoints; not network-exposed
#        in production, reachable via `docker compose exec`).
EXPOSE 5000 5001

# `uv run` defaults to syncing the venv against the lockfile, which
# triggers re-evaluating the project install. With `dynamic = ["version"]`
# that calls hatch-vcs, which fails without `.git/` (intentionally
# absent in the runtime image). The venv was already built correctly
# in the builder stage; tell `uv run` not to re-sync.
ENV UV_NO_SYNC=1

#RUN export VERSION=$(cat /wheelhouse/SPARKMETER_VERSION.txt)

ENV PATH=/app/bin:/app/scripts:$PATH

CMD ["/app/run/webapp"]

# Stage 4: Test image (extends production with dev dependencies)
FROM production AS test

# Build toolchain for any dev deps with C extensions. Root only for the apk
# install; back to spark immediately so everything written below is spark-owned.
USER root
RUN apk add --no-cache gcc musl-dev libffi-dev postgresql-dev linux-headers git
USER spark

COPY --chown=spark:spark setup.cfg setup.cfg

# The top level conftest.py, which registers the suite's own command line
# options. It has to be at the top of the tree, next to setup.cfg: pytest only
# calls pytest_addoption for initial conftests, and with no path argument the
# rootdir is the only directory searched for one.
COPY --chown=spark:spark conftest.py conftest.py

# Test fixtures: the committed snapshot baseline that the snapshot tests
# (verify()) compare generated output against. Without it the tests find
# the expected files absent and write them fresh every run instead of
# comparing — so the suite never actually validates. Test-only, so it
# lives in the test stage rather than production. Owned by spark like the
# rest of the tree: the harness writes a fresh baseline as the (non-root)
# test user whenever one is missing — a new test, a new variant, or a
# regeneration run.
COPY --chown=spark:spark test-data test-data

# The project itself is already installed in the venv inherited from
# the production stage (which inherited from builder). This sync just
# adds the `dev` dependency group on top — `--no-install-project`
# skips re-evaluating the project install, which would otherwise need
# `.git/` (not present here). Runs as spark into the spark-owned venv.
RUN uv sync --locked --group dev --no-install-project

# Disable bytecode caching: spark never needs to write .pyc into sparkmeter/,
# and it keeps the image tree clean. Every file is already spark-owned (USER
# spark + --chown on all COPYs) and coverage data is written into the
# spark-owned workdir, so the image needs no chown of the app tree.
ENV PYTHONDONTWRITEBYTECODE=1

CMD ["uv", "run", "pytest"]
