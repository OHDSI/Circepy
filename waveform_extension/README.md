# OHDSI Waveform Extension for circe_py

This extension implements the full [OHDSI Waveform Extension specification](https://ohdsi.github.io/WaveformWG/waveform-tables.html) for cohort definition and SQL generation in circe_py.

## Tables Implemented

The extension provides criteria classes and SQL builders for all 4 waveform tables:

1. **waveform_occurrence** - Clinical and temporal context for recording sessions
2. **waveform_registry** - File metadata (format, storage, temporal bounds)
3. **waveform_channel_metadata** - Signal parameters (sampling rates, gains, calibration)
4. **waveform_feature** - Derived measurements (heart rate, SpO2, arrhythmias, AI features)

## Installation

The waveform extension is included with circe_py in the `waveform_extension/` directory. To use it:

```python
import waveform_extension
waveform_extension.register()
```

## Usage Examples

### Example 1: ICU Monitoring Sessions with Multiple Files

```python
from waveform_extension.criteria import WaveformOccurrence
from circe.cohortdefinition.core import NumericRange, DateRange

criteria = WaveformOccurrence(
    waveform_occurrence_concept_id=[create_concept(2000000001, "ICU Continuous Monitoring")],
    occurrence_start_datetime=DateRange(value="2025-01-01", op="gte"),
    num_of_files=NumericRange(value=10, op="gte")
)
```

**Generated SQL**: Queries `waveform_occurrence` table for ICU monitoring sessions with ≥10 files starting after 2025-01-01.

### Example 2: High-Quality ECG Channels

```python
from waveform_extension.criteria import WaveformChannelMetadata

criteria = WaveformChannelMetadata(
    channel_concept_id=[create_concept(2000000020, "ECG Lead II")],
    metadata_concept_id=[create_concept(2000000030, "Sampling Rate")],
    value_as_number=NumericRange(value=500, op="gte"),  # ≥500 Hz
    unit_concept_id=[create_concept(8504, "Hz")]
)
```

**Use Case**: Ensure high-quality signals for QRS detection.

### Example 3: Derived Heart Rate (Most Clinically Valuable)

```python
from waveform_extension.criteria import WaveformFeature

criteria = WaveformFeature(
    feature_concept_id=[create_concept(3027018, "Heart Rate")],
    algorithm_concept_id=[create_concept(2000000040, "Pan-Tompkins QRS Detection")],
    value_as_number=NumericRange(value=60, op="gte", extent=100),  # 60-100 bpm
    unit_concept_id=[create_concept(8541, "beats/min")]
)
```

**Use Case**: Identify patients with normal cardiac rhythm derived from waveform data.

### Example 4: EDF File Format Filter

```python
from waveform_extension.criteria import WaveformRegistry

criteria = WaveformRegistry(
    file_extension_concept_id=[create_concept(2000000010, "EDF")]
)
```

**Use Case**: Filter cohorts to only include patients with EDF waveform files.

## Architecture

The extension demonstrates the full circe_py extension capabilities:

- **Criteria Classes** (`criteria.py`): 4 Pydantic models matching OHDSI spec
- **SQL Builders** (`builders/*.py`): 4 builders generating OHDSI-compliant SQL
- **Markdown Templates** (`templates/*.j2`): 4 Jinja2 templates for human-readable output
- **Registration** (`__init__.py`): Single function to register all components

## Running the Examples

```bash
cd /path/to/circe_py
export PYTHONPATH=.
python3 waveform_extension/example_usage.py
```

This will verify all 4 tables are correctly implemented with proper SQL generation and markdown rendering.

## Clinical Use Cases

### Waveform Occurrence
- ICU telemetry sessions
- Operating room monitoring
- Ambulatory ECG studies
- Sleep studies

### Waveform Registry
- Filter by file format (EDF, WFDB, etc.)
- Temporal file-level queries
- Storage location audits

### Waveform Channel Metadata
- Signal quality assurance
- Sampling rate requirements
- Device/procedure linkage
- Calibration verification

### Waveform Feature
- Continuous vital signs (HR, RR, SpO2, BP)
- Arrhythmia detection
- AI-derived embeddings
- Physiological event detection

## Reference

Full specification: https://ohdsi.github.io/WaveformWG/waveform-tables.html
