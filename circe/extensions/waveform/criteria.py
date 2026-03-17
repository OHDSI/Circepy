from typing import Optional, List
from pydantic import Field, AliasChoices

from circe.cohortdefinition.criteria import Criteria, CriteriaGroup
from circe.cohortdefinition.core import NumericRange, DateRange, TextFilter
from circe.extensions import register_domain
from circe.vocabulary.concept import Concept
from circe.cohort_builder.query_builder import BaseQuery


@register_domain(
    name="waveform_occurrence",
    domain="WaveformOccurrence",
    query_class=BaseQuery,
    requires_concept=False,
)
class WaveformOccurrence(Criteria):
    """
    Criteria for Waveform Occurrence.
    
    Represents the clinical and temporal context for a waveform recording session.
    Maps to the waveform_occurrence table in the OHDSI Waveform Extension.
    
    Reference: https://ohdsi.github.io/WaveformWG/waveform-tables.html
    """
    # Core concept - type of waveform recording
    waveform_occurrence_concept_id: Optional[List[Concept]] = Field(
        default=None,
        validation_alias=AliasChoices("WaveformOccurrenceConceptId", "waveformOccurrenceConceptId"),
        serialization_alias="WaveformOccurrenceConceptId"
    )
    
    # Temporal bounds
    occurrence_start_datetime: Optional[DateRange] = Field(
        default=None,
        validation_alias=AliasChoices("OccurrenceStartDatetime", "occurrenceStartDatetime"),
        serialization_alias="OccurrenceStartDatetime"
    )
    occurrence_end_datetime: Optional[DateRange] = Field(
        default=None,
        validation_alias=AliasChoices("OccurrenceEndDatetime", "occurrenceEndDatetime"),
        serialization_alias="OccurrenceEndDatetime"
    )
    
    # Visit context
    visit_occurrence_id: Optional[NumericRange] = Field(
        default=None,
        validation_alias=AliasChoices("VisitOccurrenceId", "visitOccurrenceId"),
        serialization_alias="VisitOccurrenceId"
    )
    visit_detail_id: Optional[NumericRange] = Field(
        default=None,
        validation_alias=AliasChoices("VisitDetailId", "visitDetailId"),
        serialization_alias="VisitDetailId"
    )
    
    # File metadata
    num_of_files: Optional[NumericRange] = Field(
        default=None,
        validation_alias=AliasChoices("NumOfFiles", "numOfFiles"),
        serialization_alias="NumOfFiles"
    )
    
    # Source identifiers
    waveform_occurrence_source_value: Optional[TextFilter] = Field(
        default=None,
        validation_alias=AliasChoices("WaveformOccurrenceSourceValue", "waveformOccurrenceSourceValue"),
        serialization_alias="WaveformOccurrenceSourceValue"
    )
    
    # Sequence/chain filtering
    preceding_waveform_occurrence_id: Optional[NumericRange] = Field(
        default=None,
        validation_alias=AliasChoices("PrecedingWaveformOccurrenceId", "precedingWaveformOccurrenceId"),
        serialization_alias="PrecedingWaveformOccurrenceId"
    )

@register_domain(
    name="waveform_registry",
    domain="WaveformRegistry",
    query_class=BaseQuery,
    requires_concept=False,
)
class WaveformRegistry(Criteria):
    """
    Criteria for Waveform Registry.
    
    Registers individual waveform files with their storage locations, formats, and temporal boundaries.
    Maps to the waveform_registry table in the OHDSI Waveform Extension.
    
    Reference: https://ohdsi.github.io/WaveformWG/waveform-tables.html
    """
    # Link to parent occurrence
    waveform_occurrence_id: Optional[NumericRange] = Field(
        default=None,
        validation_alias=AliasChoices("WaveformOccurrenceId", "waveformOccurrenceId"),
        serialization_alias="WaveformOccurrenceId"
    )
    
    # File temporal bounds
    file_start_datetime: Optional[DateRange] = Field(
        default=None,
        validation_alias=AliasChoices("FileStartDatetime", "fileStartDatetime"),
        serialization_alias="FileStartDatetime"
    )
    file_end_datetime: Optional[DateRange] = Field(
        default=None,
        validation_alias=AliasChoices("FileEndDatetime", "fileEndDatetime"),
        serialization_alias="FileEndDatetime"
    )
    
    # File format
    file_extension_concept_id: Optional[List[Concept]] = Field(
        default=None,
        validation_alias=AliasChoices("FileExtensionConceptId", "fileExtensionConceptId"),
        serialization_alias="FileExtensionConceptId"
    )
    file_extension_source_value: Optional[TextFilter] = Field(
        default=None,
        validation_alias=AliasChoices("FileExtensionSourceValue", "fileExtensionSourceValue"),
        serialization_alias="FileExtensionSourceValue"
    )
    
    # Visit context (denormalized for easier querying)
    visit_occurrence_id: Optional[NumericRange] = Field(
        default=None,
        validation_alias=AliasChoices("VisitOccurrenceId", "visitOccurrenceId"),
        serialization_alias="VisitOccurrenceId"
    )
    visit_detail_id: Optional[NumericRange] = Field(
        default=None,
        validation_alias=AliasChoices("VisitDetailId", "visitDetailId"),
        serialization_alias="VisitDetailId"
    )


@register_domain(
    name="waveform_channel_metadata",
    domain="WaveformChannelMetadata",
    query_class=BaseQuery,
    requires_concept=False,
)
class WaveformChannelMetadata(Criteria):
    """
    Criteria for Waveform Channel Metadata.
    
    Describes per-signal-channel metadata including sampling rates, gains, calibration factors,
    and signal quality indicators.
    Maps to the waveform_channel_metadata table in the OHDSI Waveform Extension.
    
    Reference: https://ohdsi.github.io/WaveformWG/waveform-tables.html
    """
    # Link to registry file
    waveform_registry_id: Optional[NumericRange] = Field(
        default=None,
        validation_alias=AliasChoices("WaveformRegistryId", "waveformRegistryId"),
        serialization_alias="WaveformRegistryId"
    )
    
    # Channel identification
    channel_concept_id: Optional[List[Concept]] = Field(
        default=None,
        validation_alias=AliasChoices("ChannelConceptId", "channelConceptId"),
        serialization_alias="ChannelConceptId"
    )
    waveform_channel_source_value: Optional[TextFilter] = Field(
        default=None,
        validation_alias=AliasChoices("WaveformChannelSourceValue", "waveformChannelSourceValue"),
        serialization_alias="WaveformChannelSourceValue"
    )
    
    # Metadata type (e.g., sampling rate, gain, offset)
    metadata_concept_id: Optional[List[Concept]] = Field(
        default=None,
        validation_alias=AliasChoices("MetadataConceptId", "metadataConceptId"),
        serialization_alias="MetadataConceptId"
    )
    metadata_source_value: Optional[TextFilter] = Field(
        default=None,
        validation_alias=AliasChoices("MetadataSourceValue", "metadataSourceValue"),
        serialization_alias="MetadataSourceValue"
    )
    
    # Metadata values (at least one must be populated)
    value_as_number: Optional[NumericRange] = Field(
        default=None,
        validation_alias=AliasChoices("ValueAsNumber", "valueAsNumber"),
        serialization_alias="ValueAsNumber"
    )
    value_as_concept_id: Optional[List[Concept]] = Field(
        default=None,
        validation_alias=AliasChoices("ValueAsConceptId", "valueAsConceptId"),
        serialization_alias="ValueAsConceptId"
    )
    
    # Units for numeric values
    unit_concept_id: Optional[List[Concept]] = Field(
        default=None,
        validation_alias=AliasChoices("UnitConceptId", "unitConceptId"),
        serialization_alias="UnitConceptId"
    )
    
    # Device/procedure linkage
    device_exposure_id: Optional[NumericRange] = Field(
        default=None,
        validation_alias=AliasChoices("DeviceExposureId", "deviceExposureId"),
        serialization_alias="DeviceExposureId"
    )
    procedure_occurrence_id: Optional[NumericRange] = Field(
        default=None,
        validation_alias=AliasChoices("ProcedureOccurrenceId", "procedureOccurrenceId"),
        serialization_alias="ProcedureOccurrenceId"
    )


@register_domain(
    name="waveform_feature",
    domain="WaveformFeature",
    query_class=BaseQuery,
    requires_concept=False,
)
class WaveformFeature(Criteria):
    """
    Criteria for Waveform Feature.
    
    Stores measurements and features derived from waveform signals.
    Supports both traditional signal processing features and AI-derived embeddings.
    Maps to the waveform_feature table in the OHDSI Waveform Extension.
    
    Reference: https://ohdsi.github.io/WaveformWG/waveform-tables.html
    """
    # Parent links
    waveform_occurrence_id: Optional[NumericRange] = Field(
        default=None,
        validation_alias=AliasChoices("WaveformOccurrenceId", "waveformOccurrenceId"),
        serialization_alias="WaveformOccurrenceId"
    )
    waveform_registry_id: Optional[NumericRange] = Field(
        default=None,
        validation_alias=AliasChoices("WaveformRegistryId", "waveformRegistryId"),
        serialization_alias="WaveformRegistryId"
    )
    waveform_channel_metadata_id: Optional[NumericRange] = Field(
        default=None,
        validation_alias=AliasChoices("WaveformChannelMetadataId", "waveformChannelMetadataId"),
        serialization_alias="WaveformChannelMetadataId"
    )
    
    # Feature type (e.g., heart rate, SpO2, QRS detection)
    feature_concept_id: Optional[List[Concept]] = Field(
        default=None,
        validation_alias=AliasChoices("FeatureConceptId", "featureConceptId"),
        serialization_alias="FeatureConceptId"
    )
    
    # Algorithm used to derive feature
    algorithm_concept_id: Optional[List[Concept]] = Field(
        default=None,
        validation_alias=AliasChoices("AlgorithmConceptId", "algorithmConceptId"),
        serialization_alias="AlgorithmConceptId"
    )
    algorithm_source_value: Optional[TextFilter] = Field(
        default=None,
        validation_alias=AliasChoices("AlgorithmSourceValue", "algorithmSourceValue"),
        serialization_alias="AlgorithmSourceValue"
    )
    
    # Temporal window for feature
    feature_start_timestamp: Optional[DateRange] = Field(
        default=None,
        validation_alias=AliasChoices("FeatureStartTimestamp", "featureStartTimestamp"),
        serialization_alias="FeatureStartTimestamp"
    )
    feature_end_timestamp: Optional[DateRange] = Field(
        default=None,
        validation_alias=AliasChoices("FeatureEndTimestamp", "featureEndTimestamp"),
        serialization_alias="FeatureEndTimestamp"
    )
    
    # Feature values (at least one must be populated)
    value_as_number: Optional[NumericRange] = Field(
        default=None,
        validation_alias=AliasChoices("ValueAsNumber", "valueAsNumber"),
        serialization_alias="ValueAsNumber"
    )
    value_as_concept_id: Optional[List[Concept]] = Field(
        default=None,
        validation_alias=AliasChoices("ValueAsConceptId", "valueAsConceptId"),
        serialization_alias="ValueAsConceptId"
    )
    
    # Units for numeric values
    unit_concept_id: Optional[List[Concept]] = Field(
        default=None,
        validation_alias=AliasChoices("UnitConceptId", "unitConceptId"),
        serialization_alias="UnitConceptId"
    )
    
    # Links to standard OMOP tables
    measurement_id: Optional[NumericRange] = Field(
        default=None,
        validation_alias=AliasChoices("MeasurementId", "measurementId"),
        serialization_alias="MeasurementId"
    )
    observation_id: Optional[NumericRange] = Field(
        default=None,
        validation_alias=AliasChoices("ObservationId", "observationId"),
        serialization_alias="ObservationId"
    )

# Rebuild models to resolve forward references
