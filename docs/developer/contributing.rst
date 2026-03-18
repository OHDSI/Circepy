Contributing Guide
==================

See :doc:`../CONTRIBUTING` for complete contributing guidelines.

Development Setup
-----------------

.. code-block:: bash

   git clone https://github.com/OHDSI/Circepy.git
   cd Circepy
   uv sync --extra dev
   uv run pre-commit install

Running Tests
-------------

.. code-block:: bash

   uv run pytest

Code Quality
------------

.. code-block:: bash

   uv run ruff check .
   uv run ruff format .
   uv run pre-commit run --all-files

For more details, see the main CONTRIBUTING.md file.
