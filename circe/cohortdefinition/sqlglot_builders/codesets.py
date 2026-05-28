"""Concept set expression query builder matching T-SQL ConceptSetExpressionQueryBuilder.

Layer 1: Per concept set: select distinct concept_id with optional LEFT JOIN exclusion.

  SELECT DISTINCT I.concept_id FROM (
    @includeQuery
  ) I [LEFT JOIN ( @excludeQuery ) E ON I.concept_id = E.concept_id WHERE E.concept_id IS NULL]

Layer 2: Across concept sets: wrap with codeset_id and UNION ALL.

  SELECT {cs.id} as codeset_id, c.concept_id FROM ( @expression ) C
  UNION ALL ...
"""

from sqlglot import exp as sge

from ...vocabulary.concept import ConceptSet, ConceptSetExpression

VOCAB = "@vocabulary_database_schema"

INCLUDE_TEMPLATE = "select distinct I.concept_id FROM ( @includeQuery ) I"
EXCLUDE_TEMPLATE = "LEFT JOIN ( @excludeQuery ) E ON I.concept_id = E.concept_id\nWHERE E.concept_id is null"


def build_codeset_query(concept_sets: list[ConceptSet]) -> sge.Union | None:
    if not concept_sets:
        return None

    union_parts: list[sge.Select] = []
    for cs in concept_sets:
        if hasattr(cs, "id") and hasattr(cs, "expression") and cs.expression is not None:
            inner = _build_expression_select(cs.expression)
            if inner is not None:
                wrapped = (
                    sge.Select()
                    .select(
                        sge.Literal.number(cs.id).as_("codeset_id"),
                        sge.column("c.concept_id"),
                    )
                    .from_(inner.subquery().as_("C"))
                )
                union_parts.append(wrapped)

    if not union_parts:
        return None

    result = union_parts[0]
    for part in union_parts[1:]:
        result = sge.Union(this=result, expression=part, distinct=False)
    return result


def _build_expression_select(expression: ConceptSetExpression) -> sge.Select | None:
    """Matches ConceptSetExpressionQueryBuilder.build_expression_query()."""
    items = expression.items if expression and expression.items else []
    if not items:
        return None

    include_concepts: list[int] = []
    include_descendant_ids: list[int] = []
    include_mapped_ids: list[int] = []
    include_mapped_descendant_ids: list[int] = []

    exclude_concepts: list[int] = []
    exclude_descendant_ids: list[int] = []
    exclude_mapped_ids: list[int] = []
    exclude_mapped_descendant_ids: list[int] = []

    for item in items:
        cid = item.concept.concept_id if item.concept else None
        if cid is None:
            continue
        if item.is_excluded:
            exclude_concepts.append(cid)
            if item.include_descendants:
                exclude_descendant_ids.append(cid)
            if item.include_mapped:
                exclude_mapped_ids.append(cid)
                if item.include_descendants:
                    exclude_mapped_descendant_ids.append(cid)
        else:
            include_concepts.append(cid)
            if item.include_descendants:
                include_descendant_ids.append(cid)
            if item.include_mapped:
                include_mapped_ids.append(cid)
                if item.include_descendants:
                    include_mapped_descendant_ids.append(cid)

    have_include = any(
        [
            include_concepts,
            include_descendant_ids,
            include_mapped_ids,
            include_mapped_descendant_ids,
        ]
    )
    have_exclude = any(
        [
            exclude_concepts,
            exclude_descendant_ids,
            exclude_mapped_ids,
            exclude_mapped_descendant_ids,
        ]
    )

    include_query = _build_concept_set_query(
        include_concepts,
        include_descendant_ids,
        include_mapped_ids,
        include_mapped_descendant_ids,
    )
    if include_query is None or not have_include:
        include_query = (
            sge.Select()
            .select(sge.column("concept_id"))
            .from_(sge.Table(this="CONCEPT", db=VOCAB))
            .where(sge.false())
        )

    outer = (
        sge.Select().distinct().select(sge.column("I.concept_id")).from_(include_query.subquery().as_("I"))
    )

    if have_exclude:
        exclude_query = _build_concept_set_query(
            exclude_concepts,
            exclude_descendant_ids,
            exclude_mapped_ids,
            exclude_mapped_descendant_ids,
        )
        if exclude_query is not None:
            j = sge.Join(
                this=exclude_query.subquery().as_("E"),
                on=sge.column("I.concept_id").eq(sge.column("E.concept_id")),
                kind="LEFT",
            )
            outer.args.setdefault("joins", []).append(j)
            outer = outer.where(sge.Is(this=sge.column("E.concept_id"), expression=sge.null()))

    return outer


def _build_concept_set_query(
    concepts: list[int],
    descendant_concepts: list[int],
    mapped_concepts: list[int],
    mapped_descendant_concepts: list[int],
) -> sge.Union | sge.Select | None:
    """Matches ConceptSetExpressionQueryBuilder.build_concept_set_query()."""
    parts: list[sge.Select | sge.Union] = []

    sub = _build_concept_set_sub_query(concepts, descendant_concepts)
    if sub is not None:
        parts.append(sub)

    if mapped_concepts or mapped_descendant_concepts:
        mapped = _build_concept_set_mapped_query(mapped_concepts, mapped_descendant_concepts)
        if mapped is not None:
            parts.append(mapped)

    if not parts:
        return None

    result = parts[0]
    for part in parts[1:]:
        result = sge.Union(this=result, expression=part, distinct=True)
    return result


def _build_concept_set_sub_query(
    concepts: list[int],
    descendant_concepts: list[int],
) -> sge.Union | sge.Select | None:
    """Matches ConceptSetExpressionQueryBuilder.build_concept_set_sub_query()."""
    parts: list[sge.Select] = []

    if concepts:
        parts.append(_standard_concept_select(concepts))

    if descendant_concepts:
        parts.append(_descendant_concept_select(descendant_concepts))

    if not parts:
        return None

    result: sge.Union | sge.Select = parts[0]
    for part in parts[1:]:
        result = sge.Union(this=result, expression=part, distinct=True)
    return result


def _build_concept_set_mapped_query(
    mapped_concepts: list[int],
    mapped_descendant_concepts: list[int],
) -> sge.Select | None:
    """Matches ConceptSetExpressionQueryBuilder.build_concept_set_mapped_query().

    select distinct cr.concept_id_1 as concept_id
    FROM ( @conceptsetQuery ) C
    join @vocabulary_database_schema.concept_relationship cr on C.concept_id = cr.concept_id_2
      and cr.relationship_id = 'Maps to'
      and cr.invalid_reason IS NULL
    """
    inner = _build_concept_set_sub_query(mapped_concepts, mapped_descendant_concepts)
    if inner is None:
        return None

    cr_table = sge.Table(this="concept_relationship", db=VOCAB, alias="cr")

    sel = (
        sge.Select()
        .distinct()
        .select(sge.column("cr.concept_id_1").as_("concept_id"))
        .from_(inner.subquery().as_("C"))
    )

    j = sge.Join(
        this=cr_table,
        on=sge.and_(
            sge.column("C.concept_id").eq(sge.column("cr.concept_id_2")),
            sge.column("cr.relationship_id").eq(sge.Literal.string("Maps to")),
            sge.Is(
                this=sge.column("cr.invalid_reason"),
                expression=sge.null(),
            ),
        ),
        kind="INNER",
    )
    sel.args.setdefault("joins", []).append(j)
    return sel


def _standard_concept_select(concept_ids: list[int]) -> sge.Select:
    """select concept_id from VOCAB.CONCEPT where (clause)"""
    return (
        sge.Select()
        .select(sge.column("concept_id"))
        .from_(sge.Table(this="CONCEPT", db=VOCAB))
        .where(_split_in_clause(sge.column("concept_id"), concept_ids))
    )


def _descendant_concept_select(concept_ids: list[int]) -> sge.Select:
    """select c.concept_id from VOCAB.CONCEPT c
    join VOCAB.CONCEPT_ANCESTOR ca on c.concept_id = ca.descendant_concept_id
    WHERE c.invalid_reason is null and (ca.ancestor_concept_id in (...))"""
    concept_table = sge.Table(this="CONCEPT", db=VOCAB)
    ancestor_table = sge.Table(this="CONCEPT_ANCESTOR", db=VOCAB)

    sel = sge.Select().select(sge.column("c.concept_id")).from_(concept_table.as_("c"))

    j = sge.Join(
        this=ancestor_table.as_("ca"),
        on=sge.column("c.concept_id").eq(sge.column("ca.descendant_concept_id")),
        kind="INNER",
    )
    sel.args.setdefault("joins", []).append(j)
    sel = sel.where(sge.Is(this=sge.column("c.invalid_reason"), expression=sge.null()))
    sel = sel.where(_split_in_clause(sge.column("ca.ancestor_concept_id"), concept_ids))
    return sel


def _split_in_clause(column: sge.Column, values: list[int]) -> sge.In | sge.Or:
    """Matches BuilderUtils.split_in_clause — wraps large lists in OR'd IN groups."""
    sorted_vals = sorted(set(values))
    if len(sorted_vals) == 0:
        return sge.false()
    if len(sorted_vals) <= 1000:
        return sge.In(
            this=column,
            expressions=[sge.Literal.number(v) for v in sorted_vals],
        )
    chunks = [sorted_vals[i : i + 1000] for i in range(0, len(sorted_vals), 1000)]
    in_exprs = [
        sge.In(
            this=column.copy(),
            expressions=[sge.Literal.number(v) for v in chunk],
        )
        for chunk in chunks
    ]
    result: sge.In | sge.Or = in_exprs[0]
    for e in in_exprs[1:]:
        result = sge.Or(this=result, expression=e)
    return result
