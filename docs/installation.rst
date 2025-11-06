Installation
============

Requirements
------------

* Python 3.8 or higher
* pip (Python package installer)

Basic Installation
------------------

Install CIRCE Python from PyPI using pip:

.. code-block:: bash

   pip install ohdsi-circe

This will install the package and all required dependencies.

Development Installation
------------------------

If you want to contribute to CIRCE Python or run the tests, install with development dependencies:

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/OHDSI/circe-be-python.git
   cd circe-be-python

   # Install in development mode with dev dependencies
   pip install -e ".[dev]"

This installs the package in editable mode with additional development tools:

* pytest - Testing framework
* pytest-cov - Coverage reporting
* black - Code formatter
* isort - Import sorter
* flake8 - Linter
* mypy - Type checker

Optional Dependencies
---------------------

Documentation
~~~~~~~~~~~~~

To build the documentation locally:

.. code-block:: bash

   pip install ohdsi-circe[docs]

This installs:

* sphinx - Documentation generator
* sphinx-rtd-theme - ReadTheDocs theme

Verifying Installation
----------------------

After installation, verify that CIRCE Python is working correctly:

.. code-block:: bash

   # Check CLI is available
   circe --help

   # Test Python import
   python -c "from circe import CohortExpression; print('✓ Installation successful')"

   # Check version
   python -c "from circe import __version__; print(f'Version: {__version__}')"

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

   # Upgrade to latest version
   pip install --upgrade ohdsi-circe

   # Verify installation
   pip show ohdsi-circe

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
   pip install ohdsi-circe

Python Version Issues
~~~~~~~~~~~~~~~~~~~~~

CIRCE Python requires Python 3.8 or higher. Check your Python version:

.. code-block:: bash

   python --version

If you have multiple Python versions installed, you may need to use ``python3`` or ``python3.8``:

.. code-block:: bash

   python3 -m pip install ohdsi-circe

Upgrading
---------

To upgrade to the latest version:

.. code-block:: bash

   pip install --upgrade ohdsi-circe

To upgrade to a specific version:

.. code-block:: bash

   pip install ohdsi-circe==1.0.0

Uninstalling
------------

To uninstall CIRCE Python:

.. code-block:: bash

   pip uninstall ohdsi-circe

Next Steps
----------

* :doc:`quickstart` - Get started with CIRCE Python
* :doc:`cli` - Learn about the command-line interface
* :doc:`user_guide/cohort_definitions` - Create your first cohort definition

