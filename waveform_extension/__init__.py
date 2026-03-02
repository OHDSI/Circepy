from pathlib import Path
from circe.extensions import get_registry

from .criteria import WaveformOccurrence, WaveformRegistry, WaveformChannelMetadata, WaveformFeature
from .builders.waveform_occurrence import WaveformOccurrenceSqlBuilder
from .builders.waveform_registry import WaveformRegistrySqlBuilder
from .builders.waveform_channel_metadata import WaveformChannelMetadataSqlBuilder
from .builders.waveform_feature import WaveformFeatureSqlBuilder

def register():
    """Register the OHDSI Waveform Extension with circe_py."""
    registry = get_registry()
    
    # 1. Register Criteria Classes
    registry.register_criteria_class("WaveformOccurrence", WaveformOccurrence)
    registry.register_criteria_class("WaveformRegistry", WaveformRegistry)
    registry.register_criteria_class("WaveformChannelMetadata", WaveformChannelMetadata)
    registry.register_criteria_class("WaveformFeature", WaveformFeature)
    
    # 2. Register SQL Builders
    registry.register_sql_builder(WaveformOccurrence, WaveformOccurrenceSqlBuilder)
    registry.register_sql_builder(WaveformRegistry, WaveformRegistrySqlBuilder)
    registry.register_sql_builder(WaveformChannelMetadata, WaveformChannelMetadataSqlBuilder)
    registry.register_sql_builder(WaveformFeature, WaveformFeatureSqlBuilder)
    
    # 3. Register Markdown Templates
    template_path = Path(__file__).parent / "templates"
    registry.add_template_path(template_path)
    registry.register_markdown_template(WaveformOccurrence, "waveform_occurrence.j2")
    registry.register_markdown_template(WaveformRegistry, "waveform_registry.j2")
    registry.register_markdown_template(WaveformChannelMetadata, "waveform_channel_metadata.j2")
    registry.register_markdown_template(WaveformFeature, "waveform_feature.j2")
