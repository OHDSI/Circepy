"""
Warning severity levels for validation checks.

This module defines the severity levels for warnings generated during
cohort expression validation.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from enum import Enum


class WarningSeverity(Enum):
    """Severity levels for validation warnings.
    
    Java equivalent: org.ohdsi.circe.check.WarningSeverity
    """
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

