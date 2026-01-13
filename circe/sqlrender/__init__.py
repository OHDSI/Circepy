# -*- coding: utf-8 -*-
"""SQL rendering utilities for CIRCE.

Provides functions to render SQL templates with @variable placeholders and
translate rendered SQL between dialects using ``sqlglot``.
"""

from .render import render_sql, translate_sql

__all__ = ["render_sql", "translate_sql"]
