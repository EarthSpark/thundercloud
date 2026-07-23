Sparkmeter Style Guide
======================

Naming Conventions:
-------------------

Name order
~~~~~~~~~~

Everything should be named with the model (object) first, verb last.

::

    Functions:

     - tariff_add()
     - tariff_edit()

    Files:

     - tariff-list.html
     - tariff-edit.html

underscore vs hyphen
~~~~~~~~~~~~~~~~~~~~

Where possible use - instead of \_ (saves on keystrokes)

::

    tariff-list.html instead of tariff_list.html

Python Style:
-------------

Style is enforced by `Ruff <https://docs.astral.sh/ruff/>`_, configured in
``pyproject.toml``. ``ruff format`` handles formatting (line length 110) and
``ruff check`` runs the lint rules -- pyflakes (``F``) and import sorting
(``I``). Both are checked in CI and applied by the pre-commit hooks. Docstrings
are additionally checked against PEP257 by ``pydocstyle`` (ignoring ``D211`` and
``D403``); that check is advisory and does not block.

Hanging indents
~~~~~~~~~~~~~~~

    Do what thou wilt shall be the whole of the law.
