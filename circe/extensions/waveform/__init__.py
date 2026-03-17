from pathlib import Path
from circe.extensions import template_path

# Importing criteria triggers @criteria_class decorators
from .criteria import WaveformOccurrence, WaveformRegistry, WaveformChannelMetadata, WaveformFeature

# Importing builders triggers @sql_builder and @markdown_template decorators
from .builders.waveform_occurrence import WaveformOccurrenceSqlBuilder
from .builders.waveform_registry import WaveformRegistrySqlBuilder
from .builders.waveform_channel_metadata import WaveformChannelMetadataSqlBuilder
from .builders.waveform_feature import WaveformFeatureSqlBuilder

# Register the templates directory so Jinja2 can locate extension templates
template_path(Path(__file__).parent / "templates")