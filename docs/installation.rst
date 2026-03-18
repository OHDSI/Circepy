Installation
============

Requirements
------------
* Python 3.9 or higher
* uv (recommended for the reproducible, lockfile-backed workflow)
* pip (supported as a fallback installer)

Source Installation
-------------------

Since the package is still in active development, the recommended path is to install from source with ``uv``:

.. code-block:: bash

   git clone https://github.com/OHDSI/Circepy.git
   cd Circepy
   uv sync --extra dev
   uv run pre-commit install

This creates a project-local environment with the locked development toolchain.

pip Fallback
------------

If you are not using ``uv``, use a virtual environment and install with ``pip``:

.. code-block:: bash

   python -m venv .venv
   source .venv/bin/activate

   pip install -e ".[dev]"

Development tools include:

* pytest - Testing framework
* pytest-cov - Coverage reporting
* Ruff - Linting and formatting
* pre-commit - Git hook runner

PyPI Installation
-----------------

The current alpha package is available on PyPI as:

.. code-block:: bash

   pip install ohdsi-circe-python-alpha

The long-term package name is expected to become:

.. code-block:: bash

   pip install ohdsi-circepy

Optional Dependencies
---------------------

Documentation
~~~~~~~~~~~~~

To build the documentation locally:

.. code-block:: bash

   uv sync --extra docs

Or, with ``pip``:

.. code-block:: bash

   pip install -e ".[docs]"

This installs:

* sphinx - Documentation generator
* sphinx-rtd-theme - ReadTheDocs theme

Verifying Installation
----------------------

After installation, verify that CIRCE Python is working correctly:

.. code-block:: bash

   # Check CLI is available
   uv run circe --help

   # Test Python import
   uv run python -c "from circe import CohortExpression; print('✓ Installation successful')"

   # Check version
   uv run python -c "from circe import __version__; print(f'Version: {__version__}')"

Expected output:

.. code-block:: text

   ✓ Installation successful
   Version: 1.0.0

Troubleshooting
---------------

Import Errors
~~~~~~~~~~~~~

If you encounter import errors after installation:

.. code-block:: bash

   cd Circepy
   uv sync --extra dev

Permission Errors
~~~~~~~~~~~~~~~~~

If you get permission errors during installation, use a virtual environment:

.. code-block:: bash

   # Create virtual environment
   python -m venv circe_env

   # Activate (Linux/Mac)
   source circe_env/bin/activate

   # Activate (Windows)
   circe_env\Scripts\activate

   # Install
   pip install -e ".[dev]"

Python Version Issues
~~~~~~~~~~~~~~~~~~~~~

CIRCE Python requires Python 3.9 or higher. Check your Python version:

.. code-block:: bash

   python --version

If you have multiple Python versions installed, you may need to use ``python3`` or ``python3.9``:

.. code-block:: bash

   python3 -m pip install -e ".[dev]"

Upgrading
---------

To refresh the ``uv`` environment after pulling new changes:

.. code-block:: bash

   git pull origin main
   uv sync --extra dev

If you installed with ``pip``, reinstall after pulling:

.. code-block:: bash

   pip install -e ".[dev]"

Uninstalling
------------

To uninstall CIRCE Python:

.. code-block:: bash

   pip uninstall ohdsi-circe-python-alpha

Next Steps
----------

* :doc:`quickstart` - Get started with CIRCE Python
* :doc:`cli` - Learn about the command-line interface
* :doc:`user_guide/cohort_definitions` - Create your first cohort definition
