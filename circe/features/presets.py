"""
Pre-built covariate presets matching OHDSI FeatureExtraction's common settings.

Factory functions return configured ``FeatureSet`` objects ready for use
with ``FeatureExtractor.extract()``.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .models import (
    AncestorBinaryFeature,
    BulkDomainFeature,
    CompositeFeature,
    DemographicsFeature,
    FeatureSet,
    VisitCountFeature,
)


# ------------------------------------------------------------------
# Charlson Comorbidity Index — concept IDs from R FeatureExtraction
# ------------------------------------------------------------------

# Each entry: (name, weight, [ancestor_concept_ids])
# Source: OHDSI/FeatureExtraction inst/sql/sql_server/CharlsonIndex.sql
CHARLSON_COMPONENTS: List[Tuple[str, int, List[int]]] = [
    ("Myocardial infarction", 1, [4329847]),
    ("Congestive heart failure", 1, [316139]),
    ("Peripheral vascular disease", 1, [321052]),
    ("Cerebrovascular disease", 1, [381591, 434056]),
    ("Dementia", 1, [4182210]),
    ("Chronic pulmonary disease", 1, [4063381]),
    ("Rheumatologic disease", 1, [257628, 134442, 80800, 80809, 256197, 255348]),
    ("Peptic ulcer disease", 1, [4247120]),
    ("Mild liver disease", 1, [4064161, 4212540]),
    ("Diabetes (mild to moderate)", 1, [201820]),
    ("Diabetes with chronic complications", 2, [443767, 442793]),
    ("Hemiplegia or paraplegia", 2, [192606, 374022]),
    ("Renal disease", 2, [4030518]),
    ("Any malignancy", 2, [443392]),
    ("Moderate to severe liver disease", 3, [4245975, 4029488, 192680, 24966]),
    ("Metastatic solid tumor", 6, [432851]),
    ("AIDS", 6, [439727]),
]

# Standard domains for large-scale covariates
LARGE_SCALE_DOMAINS = [
    "ConditionOccurrence",
    "DrugExposure",
    "ProcedureOccurrence",
    "Measurement",
    "Observation",
    "ConditionEra",
    "DrugEra",
    "DeviceExposure",
]

# Standard time windows
WINDOW_SHORT = (-30, 0)
WINDOW_MEDIUM = (-180, 0)
WINDOW_LONG = (-365, 0)


# ------------------------------------------------------------------
# Public factory functions
# ------------------------------------------------------------------


def default_covariates(
    *,
    include_demographics: bool = True,
    include_conditions: bool = True,
    include_drugs: bool = True,
    include_procedures: bool = True,
    include_visits: bool = True,
    window: Tuple[int, int] = WINDOW_LONG,
) -> FeatureSet:
    """Return a standard set of default covariates.

    Equivalent to R's ``createDefaultCovariateSettings()``:

    - Demographics (age, gender)
    - Conditions (bulk, long-term)
    - Drugs (bulk, long-term)
    - Procedures (bulk, long-term)
    - Visit counts

    Parameters
    ----------
    include_demographics : bool
        Include age and gender features.
    include_conditions : bool
        Include bulk condition features.
    include_drugs : bool
        Include bulk drug features.
    include_procedures : bool
        Include bulk procedure features.
    include_visits : bool
        Include visit count feature.
    window : tuple[int, int]
        Default time window for domain features.

    Returns
    -------
    FeatureSet
        A configured feature set ready for extraction.
    """
    fs = FeatureSet(
        name="Default Covariates",
        description="Standard covariates: demographics + conditions + drugs + procedures + visits",
    )

    if include_demographics:
        fs.add(DemographicsFeature(
            name="Demographics",
            include_age=True,
            include_gender=True,
        ))

    if include_conditions:
        fs.add(BulkDomainFeature(
            name="Conditions (Long-Term)",
            domain="ConditionOccurrence",
            window=window,
        ))

    if include_drugs:
        fs.add(BulkDomainFeature(
            name="Drugs (Long-Term)",
            domain="DrugExposure",
            window=window,
        ))

    if include_procedures:
        fs.add(BulkDomainFeature(
            name="Procedures (Long-Term)",
            domain="ProcedureOccurrence",
            window=window,
        ))

    if include_visits:
        fs.add(VisitCountFeature(
            name="Visit Count (Long-Term)",
            window=window,
        ))

    return fs


def large_scale_covariates(
    *,
    domains: Optional[List[str]] = None,
    windows: Optional[List[Tuple[int, int]]] = None,
    include_demographics: bool = True,
    include_visits: bool = True,
) -> FeatureSet:
    """Return a large-scale covariate set for propensity score models.

    Equivalent to R's ``createCovariateSettings()`` with all domain flags enabled
    across multiple time windows.

    Parameters
    ----------
    domains : list[str] | None
        OMOP domain names. Defaults to all standard domains.
    windows : list[tuple[int, int]] | None
        Time windows to generate features for. Defaults to short/medium/long.
    include_demographics : bool
        Include demographic features (age, gender, race, ethnicity).
    include_visits : bool
        Include visit count features for each window.

    Returns
    -------
    FeatureSet
        A large-scale feature set with one bulk feature per domain per window.
    """
    if domains is None:
        domains = list(LARGE_SCALE_DOMAINS)
    if windows is None:
        windows = [WINDOW_SHORT, WINDOW_MEDIUM, WINDOW_LONG]

    fs = FeatureSet(
        name="Large-Scale Covariates",
        description=f"Bulk features for {len(domains)} domains × {len(windows)} windows",
    )

    if include_demographics:
        fs.add(DemographicsFeature(
            name="Demographics",
            include_age=True,
            include_gender=True,
            include_race=True,
            include_ethnicity=True,
            include_index_year=True,
            include_index_month=True,
        ))

    for window in windows:
        window_label = f"{abs(window[0])}d"

        for domain in domains:
            fs.add(BulkDomainFeature(
                name=f"{domain} ({window_label})",
                domain=domain,
                window=window,
            ))

        if include_visits:
            fs.add(VisitCountFeature(
                name=f"Visit Count ({window_label})",
                window=window,
            ))

    return fs


def charlson_index(
    *,
    window: Tuple[int, int] = (-99999, 0),
    domain: str = "ConditionEra",
) -> CompositeFeature:
    """Return a Charlson Comorbidity Index composite feature.

    Uses the standard 17-component Romano adaptation with ancestor concept
    IDs from OHDSI FeatureExtraction's ``CharlsonIndex.sql``. Each component
    uses ``AncestorBinaryFeature`` to match via ``concept_ancestor`` rollup.

    Parameters
    ----------
    window : tuple[int, int]
        Time window for matching conditions. Default ``(-99999, 0)`` matches
        any condition before or on the index date (matches R behavior).
    domain : str
        Domain to match against. Default ``"ConditionEra"`` matches the R
        implementation.

    Returns
    -------
    CompositeFeature
        A weighted composite feature with 17 Charlson components.
    """
    components = []
    for name, weight, ancestor_ids in CHARLSON_COMPONENTS:
        binary = AncestorBinaryFeature(
            name=f"Charlson: {name}",
            ancestor_concept_ids=ancestor_ids,
            domain=domain,
            window=window,
        )
        components.append((binary, float(weight)))

    return CompositeFeature(
        name="Charlson Comorbidity Index",
        components=components,
        description="Charlson index (Romano adaptation) — 17 components from R FeatureExtraction",
    )
