from circe.extensions import get_registry

# Importing criteria triggers @register_criteria decorators (registers criteria + templates)
from .criteria import WaveformOccurrence, WaveformRegistry, WaveformChannelMetadata, WaveformFeature

# Importing builders triggers @register_sql_builder decorators
from .builders.waveform_occurrence import WaveformOccurrenceSqlBuilder
from .builders.waveform_registry import WaveformRegistrySqlBuilder
from .builders.waveform_channel_metadata import WaveformChannelMetadataSqlBuilder
from .builders.waveform_feature import WaveformFeatureSqlBuilder

def register():
    """Register the OHDSI Waveform Extension with circe_py.
    
    All criteria classes, SQL builders, and markdown templates are auto-registered
    via decorators when imported. This function only registers the named extension.
    """
    registry = get_registry()
    registry.register_named_extension("waveform", version="0.1.0")
