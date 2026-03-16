"""
Aggregation utilities for feature results (e.g. Table 1).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING, Union

import pandas as pd

if TYPE_CHECKING:
    from .extractor import FeatureResult
    from .models import FeatureSet


def table_one(
    results: "FeatureResult",
    feature_set: "FeatureSet",
    *,
    output_format: str = "pandas",
) -> Union[pd.DataFrame, Any]:
    """Compute a 'Table 1' summary (means, percentages) from feature results.

    Binary features: count (%)
    Continuous features: mean (SD), median [IQR]

    Parameters
    ----------
    results : FeatureResult
        The output from ``FeatureExtractor.extract()``.
    feature_set : FeatureSet
        The feature definitions used for extraction (metadata).
    output_format : str
        'pandas' (default) or 'polars'.

    Returns
    -------
    pd.DataFrame
        A summary table with rows for each feature.
    """
    if results.scalar is None:
        return pd.DataFrame()

    # Get raw data
    df = results.scalar.execute()
    
    # Map hashes back to feature names and types
    hash_to_meta = {
        f.feature_hash: {"name": f.name, "type": f.feature_type}
        for f in feature_set
    }

    # Aggregate
    summary = []
    
    # We need total N for percentages
    # Assuming all subjects in the cohort are represented or can be inferred
    total_subjects = df["subject_id"].nunique()

    for f_hash, group in df.groupby("feature_hash"):
        meta = hash_to_meta.get(f_hash, {"name": f_hash, "type": "unknown"})
        name = meta["name"]
        f_type = meta["type"]

        values = group["feature_value"]
        
        row = {"Feature": name, "Type": str(f_type)}

        if f_type == "binary":
            count = (values == 1.0).sum()
            pct = (count / total_subjects) * 100
            row["Summary"] = f"{count} ({pct:.1f}%)"
            row["Count"] = count
            row["Mean/Pct"] = pct
        else:
            mean = values.mean()
            sd = values.std()
            median = values.median()
            q1 = values.quantile(0.25)
            q3 = values.quantile(0.75)
            
            row["Summary"] = f"{mean:.2f} ({sd:.2f}) / {median:.2f} [{q1:.2f}-{q3:.2f}]"
            row["Mean/Pct"] = mean
            row["SD"] = sd
            row["Median"] = median
            row["IQR"] = f"{q1:.2f}-{q3:.2f}"

        summary.append(row)

    res_df = pd.DataFrame(summary)
    
    if output_format == "polars":
        import polars as pl
        return pl.from_pandas(res_df)
    
    return res_df


def get_standard_table_one_set() -> "FeatureSet":
    """Return a standard FeatureSet for baseline characterization.
    
    Includes demographics (age, gender) and bulk domain features for
    conditions, drugs, and procedures in a 365-day lookback window.
    Delegates to ``presets.default_covariates()``.
    """
    from .presets import default_covariates
    
    return default_covariates()
