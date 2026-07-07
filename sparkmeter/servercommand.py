# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Server and shell CLI commands."""

import os
import signal
import subprocess
import sys
import time

import click
from flask import current_app
from flask.cli import with_appcontext
from zope.component import getUtility

from sparkmeter.config.configdict import config
from sparkmeter.interface import IApplication

server = click.Group('server', help='Development server commands.')


@server.command()
@click.option('--host', '-h', default='0.0.0.0', help='The interface to bind to.')
@click.option('--port', '-p', default=5000, help='The port to bind to.')
@click.option('--debug/--no-debug', default=True, help='Enable or disable debug mode.')
@click.option('--reload/--no-reload', default=True, help='Enable or disable reloader.')
@click.option('--watch-assets/--no-watch-assets', default=False,
              help='Enable asset watching (CSS/JS compilation).')
@click.option('--demo-login/--no-demo-login', default=True,
              help='Enable or disable demo login (dev only).')
@with_appcontext
def dev(host, port, debug, reload, watch_assets, demo_login):
    """Run development server with optional asset watching."""
    click.echo('Starting Sparkmeter development server...')

    # The dev server serves session login and Flask-Security token endpoints,
    # so it needs the same secrets as production even though it runs under
    # MODE_MANAGE (which the production-only boot guard does not gate). Fail
    # fast here -- before spawning any asset-watcher subprocesses -- rather
    # than crash at request time when a secret is unset. The config is already
    # loaded at app construction, so it is available before bootstrap().
    from sparkmeter.app import REQUIRED_PRODUCTION_SECRETS, secret_configured
    for key, env_var in REQUIRED_PRODUCTION_SECRETS:
        if not secret_configured(config, key):
            raise SystemExit(
                '%s must be set to run the dev server; refusing to start '
                'without a configured %s.' % (env_var, key))

    pids = []

    def shutdown_handler():
        """Clean up child processes on shutdown."""
        for pid in pids:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass  # Process already dead

    def prepare_environment():
        """Prepare the development environment."""
        if not os.path.exists('static/javascripts'):
            os.makedirs('static/javascripts')
        if not os.path.exists('static/stylesheets'):
            os.makedirs('static/stylesheets')
        os.environ['SM_DEBUG'] = 'true'
        os.environ['SM_WATCH_ASSETS'] = 'true'

    def wait_for_assets(*files):
        """Wait for asset files to be generated."""
        click.echo('Waiting for assets to be compiled...')
        while True:
            if all([os.path.exists('static/' + f) for f in files]):
                break
            time.sleep(1)
        click.echo('Assets ready!')

    def start_watchers():
        """Start asset watchers for CSS and JS."""
        click.echo('Starting asset watchers...')
        p = subprocess.Popen(['make', '-j', '2', 'watchcss', 'watchjs'])
        pids.append(p.pid)
        wait_for_assets('javascripts/application.js',
                        'javascripts/vendor.js',
                        'stylesheets/application.css')

    try:
        if watch_assets:
            prepare_environment()
            start_watchers()

        # Bootstrap the application
        current_app.bootstrap()
        # The explicit flag is authoritative (default on), so --no-demo-login is
        # honored regardless of an ambient ENABLE_DEMO_LOGIN in config.
        config['ENABLE_DEMO_LOGIN'] = demo_login

        # Run the Flask development server
        current_app.run(host=host, port=port, debug=debug, use_reloader=reload)

    except KeyboardInterrupt:
        click.echo('\nShutting down...')
        shutdown_handler()


@click.command()
@click.option('-c', '--command', help='Python command to execute')
@click.argument('args', nargs=-1, type=click.UNPROCESSED)
@with_appcontext
def shell(command, args):
    """Run an interactive Sparkmeter shell with IPython support."""
    click.echo('Starting Sparkmeter shell...')

    # Setup databases
    app = getUtility(IApplication)
    app.setup_databases()

    def get_shell_context():
        """Get the shell context with useful imports."""
        from sparkmeter.controller import get_ground
        from sparkmeter.database.alchemy import sql
        from sparkmeter.models import BaseDomain

        ns = dict(
            app=getUtility(IApplication),
            ground=get_ground(),
            sql=sql,
        )
        # Add all domain models
        ns.update({m.__name__: m for m in BaseDomain.__subclasses__()})
        return ns

    def run_snippet(source, filename='<string>', mode='single'):
        """Execute a Python snippet in the shell context."""
        context = get_shell_context()
        if mode == 'exec':
            context['__name__'] = '__main__'
            context['__file__'] = filename
        code = compile(source, filename, mode)
        exec(code, globals(), context)

    def run_file(args):
        """Execute a Python file in the shell context."""
        sys.argv = list(args)
        if args[0] == "-":
            filename = '<stdin>'
            f = sys.stdin
        else:
            filename = args[0]
            f = open(filename)
        run_snippet(f.read(), filename, 'exec')

    def run_console():
        """Run an interactive IPython console."""
        try:
            from IPython.config.loader import Config
            from IPython.terminal.embed import InteractiveShellEmbed

            cfg = Config()
            cfg.TerminalInteractiveShell.confirm_exit = False
            ipython_shell = InteractiveShellEmbed(config=cfg)
            context = get_shell_context()

            banner = "Sparkmeter Interactive Shell\n"
            banner += "Available objects: " + ", ".join(sorted(context.keys()))

            ipython_shell(global_ns=globals(), local_ns=context, header=banner)
        except ImportError:
            # Fallback to standard Python shell if IPython not available
            import code
            context = get_shell_context()
            code.interact(banner="Sparkmeter Shell (IPython not available)", local=context)

    # Execute based on provided arguments
    if command is not None:
        run_snippet(command)
    elif args:
        run_file(args)
    else:
        run_console()
