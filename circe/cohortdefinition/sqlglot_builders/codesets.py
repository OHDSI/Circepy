from sqlglot import exp as sge

from ...vocabulary.concept import ConceptSet, ConceptSetExpression, ConceptSetItem


def build_codeset_query(concept_sets: list[ConceptSet]) -> sge.Union | None:
    if not concept_sets:
        return None

    union_parts: list[sge.Select] = []
    for cs in concept_sets:
        if hasattr(cs, "id") and hasattr(cs, "expression"):
            sub = _build_concept_set_select(cs.id, cs.expression)
            if sub is not None:
                union_parts.append(sub)

    if not union_parts:
        return None

    result = union_parts[0]
    for part in union_parts[1:]:
        result = sge.Union(this=result, expression=part, distinct=False)
    return result


def _build_concept_set_select(
    codeset_id: int,
    expression: ConceptSetExpression,
) -> sge.Select | None:
    items = expression.items if expression and expression.items else []
    if not items:
        return None

    union_parts: list[sge.Select] = []
    for item in items:
        sel = _build_item_select(codeset_id, item)
        if sel is not None:
            union_parts.append(sel)

    if not union_parts:
        union_parts.append(
            sge.Select()
            .select(
                sge.Literal.number(codeset_id).as_("codeset_id"),
                sge.Literal.number(0).as_("concept_id"),
            )
            .where(sge.false())
        )

    result = union_parts[0]
    for part in union_parts[1:]:
        result = sge.Union(this=result, expression=part, distinct=False)
    return result


def _build_item_select(codeset_id: int, item: ConceptSetItem) -> sge.Select | None:
    if item.concept is None or item.concept.concept_id is None:
        return None

    concept_id = item.concept.concept_id

    base_select = sge.Select().select(
        sge.Literal.number(codeset_id).as_("codeset_id"),
        sge.column("c.concept_id"),
    )

    if item.include_descendants:
        base_select = (
            base_select.from_(sge.Table(this="concept_ancestor", alias="ca"))
            .join(
                sge.Table(this="concept", alias="c"),
                on=sge.EQ(
                    this=sge.column("ca.descendant_concept_id"),
                    expression=sge.column("c.concept_id"),
                ),
                kind="INNER JOIN",
            )
            .where(
                sge.EQ(
                    this=sge.column("ca.ancestor_concept_id"),
                    expression=sge.Literal.number(concept_id),
                )
            )
        )
    elif item.include_mapped:
        base_select = (
            base_select.from_(sge.Table(this="concept_relationship", alias="cr"))
            .join(
                sge.Table(this="concept", alias="c"),
                on=sge.EQ(
                    this=sge.column("cr.concept_id_2"),
                    expression=sge.column("c.concept_id"),
                ),
                kind="INNER JOIN",
            )
            .where(
                sge.EQ(
                    this=sge.column("cr.concept_id_1"),
                    expression=sge.Literal.number(concept_id),
                )
            )
            .where(
                sge.EQ(
                    this=sge.column("c.standard_concept"),
                    expression=sge.Literal.string("S"),
                )
            )
        )
    else:
        base_select = base_select.from_(sge.Table(this="concept", alias="c")).where(
            sge.EQ(
                this=sge.column("c.concept_id"),
                expression=sge.Literal.number(concept_id),
            )
        )

    return base_select
