"""builders sub-package for the waveform extension.

Importing this package registers both the SQL builders (via @sql_builder /
@markdown_template decorators) and the ibis execution builders (via @register)
for all four waveform criteria types.
"""

# SQL / markdown builders — decorators fire on import
from . import waveform_occurrence  # noqa: F401
from . import waveform_registry  # noqa: F401
from . import waveform_channel_metadata  # noqa: F401
from . import waveform_feature  # noqa: F401

# Ibis execution builders — @register decorators fire on import
from . import ibis_waveform_occurrence  # noqa: F401
from . import ibis_waveform_registry  # noqa: F401
from . import ibis_waveform_channel_metadata  # noqa: F401
from . import ibis_waveform_feature  # noqa: F401
