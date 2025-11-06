Contributing Guide
==================

See :doc:`../../CONTRIBUTING` for complete contributing guidelines.

Development Setup
-----------------

.. code-block:: bash

   git clone https://github.com/OHDSI/circe-be-python.git
   cd circe-be-python
   pip install -e ".[dev]"

Running Tests
-------------

.. code-block:: bash

   pytest

Code Quality
------------

.. code-block:: bash

   black circe/
   isort circe/
   flake8 circe/
   mypy circe/

For more details, see the main CONTRIBUTING.md file.

