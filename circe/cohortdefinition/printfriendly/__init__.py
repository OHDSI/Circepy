"""
Print-Friendly Module

This module contains classes for generating human-readable output from cohort definitions.
It mirrors the Java CIRCE-BE printfriendly package structure.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from .markdown_render import MarkdownRender

__all__ = [
    "MarkdownRender"
]
