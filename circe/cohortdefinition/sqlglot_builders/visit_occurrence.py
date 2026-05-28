from sqlglot import exp as sge

from ..builders.utils import BuilderUtils
from ..criteria import VisitOccurrence
from .base import SqlGlotCriteriaBuilder
from .primitives import (
    alias_expr,
    build_date_range_clause,
    build_in_clause,
    build_numeric_range_clause,
    codeset_in,
    column_ref,
    date_add,
    datediff,
    row_number_expr,
    year_of,
)


class VisitOccurrenceGlotBuilder(SqlGlotCriteriaBuilder[VisitOccurrence]):
    def build_select(self, criteria: VisitOccurrence) -> sge.Select:
        inner = sge.Select()
        cols = [
            column_ref("vo", "person_id"),
            column_ref("vo", "visit_occurrence_id"),
            column_ref("vo", "visit_concept_id"),
        ]

        if (
            criteria.visit_type is not None and len(criteria.visit_type) > 0
        ) or criteria.visit_type_cs is not None:
            cols.append(column_ref("vo", "visit_type_concept_id"))
        if (
            criteria.provider_specialty is not None and len(criteria.provider_specialty) > 0
        ) or criteria.provider_specialty_cs is not None:
            cols.append(column_ref("vo", "provider_id"))
        if (
            criteria.place_of_service is not None and len(criteria.place_of_service) > 0
        ) or criteria.place_of_service_cs is not None:
            cols.append(column_ref("vo", "care_site_id"))

        if criteria.date_adjustment is not None:
            start_col = (
                column_ref("vo", "visit_start_date")
                if criteria.date_adjustment.start_with == "START_DATE"
                else column_ref("vo", "visit_end_date")
            )
            end_col = (
                column_ref("vo", "visit_start_date")
                if criteria.date_adjustment.end_with == "START_DATE"
                else column_ref("vo", "visit_end_date")
            )
            start_date_expr = date_add("day", criteria.date_adjustment.start_offset, start_col)
            end_date_expr = date_add("day", criteria.date_adjustment.end_offset, end_col)
        else:
            start_date_expr = column_ref("vo", "visit_start_date")
            end_date_expr = column_ref("vo", "visit_end_date")

        cols.append(alias_expr(start_date_expr, "start_date"))
        cols.append(alias_expr(end_date_expr, "end_date"))

        inner = inner.select(*cols).from_(sge.Table(this="VISIT_OCCURRENCE", alias="vo"))

        if criteria.codeset_id is not None:
            cs_table = sge.Table(this="#Codesets", alias="cs")
            cs_on = sge.And(
                this=sge.EQ(
                    this=column_ref("vo", "visit_concept_id"), expression=column_ref("cs", "concept_id")
                ),
                expression=sge.EQ(
                    this=column_ref("cs", "codeset_id"), expression=sge.Literal.number(criteria.codeset_id)
                ),
            )
            inner = inner.join(cs_table, on=cs_on, kind="INNER JOIN", append=True)
        if criteria.visit_source_concept is not None:
            cns_table = sge.Table(this="#Codesets", alias="cns")
            cns_on = sge.And(
                this=sge.EQ(
                    this=column_ref("vo", "visit_source_concept_id"),
                    expression=column_ref("cns", "concept_id"),
                ),
                expression=sge.EQ(
                    this=column_ref("cns", "codeset_id"),
                    expression=sge.Literal.number(criteria.visit_source_concept),
                ),
            )
            inner = inner.join(cns_table, on=cns_on, kind="INNER JOIN", append=True)

        if criteria.first:
            inner = inner.select(
                alias_expr(
                    row_number_expr(
                        [column_ref("vo", "person_id")],
                        [column_ref("vo", "visit_start_date"), column_ref("vo", "visit_occurrence_id")],
                    ),
                    "ordinal",
                )
            )

        outer_cols = [
            alias_expr(column_ref("C", "person_id"), "person_id"),
            alias_expr(column_ref("C", "visit_occurrence_id"), "event_id"),
            column_ref("C", "start_date"),
            column_ref("C", "end_date"),
            column_ref("C", "visit_occurrence_id"),
            alias_expr(column_ref("C", "start_date"), "sort_date"),
        ]

        outer = sge.Select().select(*outer_cols).from_(inner.subquery().as_("C"))

        if (
            criteria.age is not None
            or (criteria.gender is not None and len(criteria.gender) > 0)
            or (criteria.gender_cs is not None and criteria.gender_cs.codeset_id)
        ):
            outer = outer.join(
                sge.Table(this="PERSON", alias="P"),
                on=sge.EQ(this=column_ref("C", "person_id"), expression=column_ref("P", "person_id")),
                kind="JOIN",
                append=True,
            )

        if (
            (criteria.place_of_service is not None and len(criteria.place_of_service) > 0)
            or (criteria.place_of_service_cs is not None and criteria.place_of_service_cs.codeset_id)
            or criteria.place_of_service_location is not None
        ):
            outer = outer.join(
                sge.Table(this="CARE_SITE", alias="CS"),
                on=sge.EQ(this=column_ref("C", "care_site_id"), expression=column_ref("CS", "care_site_id")),
                kind="JOIN",
                append=True,
            )

        if (criteria.provider_specialty is not None and len(criteria.provider_specialty) > 0) or (
            criteria.provider_specialty_cs is not None and criteria.provider_specialty_cs.codeset_id
        ):
            outer = outer.join(
                sge.Table(this="PROVIDER", alias="PR"),
                on=sge.EQ(this=column_ref("C", "provider_id"), expression=column_ref("PR", "provider_id")),
                kind="LEFT JOIN",
                append=True,
            )

        wheres = []

        if criteria.occurrence_start_date is not None:
            clause = build_date_range_clause(column_ref("C", "start_date"), criteria.occurrence_start_date)
            if clause is not None:
                wheres.append(clause)

        if criteria.occurrence_end_date is not None:
            clause = build_date_range_clause(column_ref("C", "end_date"), criteria.occurrence_end_date)
            if clause is not None:
                wheres.append(clause)

        if criteria.visit_type is not None and len(criteria.visit_type) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.visit_type)
            if concept_ids:
                exclude = criteria.visit_type_exclude if hasattr(criteria, "visit_type_exclude") else False
                wheres.append(
                    build_in_clause(column_ref("C", "visit_type_concept_id"), concept_ids, exclude=exclude)
                )

        if criteria.visit_type_cs is not None and criteria.visit_type_cs.codeset_id:
            clause = codeset_in(
                column_ref("C", "visit_type_concept_id"),
                criteria.visit_type_cs.codeset_id,
                exclude=criteria.visit_type_cs.is_exclusion,
            )
            if clause is not None:
                wheres.append(clause)

        if criteria.visit_length is not None:
            len_expr = datediff("day", column_ref("C", "start_date"), column_ref("C", "end_date"))
            clause = build_numeric_range_clause(len_expr, criteria.visit_length)
            if clause is not None:
                wheres.append(clause)

        if criteria.age is not None:
            age_expr = sge.Sub(
                this=year_of(column_ref("C", "start_date")),
                expression=column_ref("P", "year_of_birth"),
            )
            clause = build_numeric_range_clause(age_expr, criteria.age)
            if clause is not None:
                wheres.append(clause)

        if criteria.gender is not None and len(criteria.gender) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.gender)
            if concept_ids:
                wheres.append(build_in_clause(column_ref("P", "gender_concept_id"), concept_ids))

        if criteria.gender_cs is not None and criteria.gender_cs.codeset_id:
            clause = codeset_in(
                column_ref("P", "gender_concept_id"),
                criteria.gender_cs.codeset_id,
                exclude=criteria.gender_cs.is_exclusion,
            )
            if clause is not None:
                wheres.append(clause)

        if criteria.provider_specialty is not None and len(criteria.provider_specialty) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.provider_specialty)
            if concept_ids:
                wheres.append(build_in_clause(column_ref("PR", "specialty_concept_id"), concept_ids))

        if criteria.provider_specialty_cs is not None and criteria.provider_specialty_cs.codeset_id:
            clause = codeset_in(
                column_ref("PR", "specialty_concept_id"),
                criteria.provider_specialty_cs.codeset_id,
                exclude=criteria.provider_specialty_cs.is_exclusion,
            )
            if clause is not None:
                wheres.append(clause)

        if criteria.place_of_service is not None and len(criteria.place_of_service) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.place_of_service)
            if concept_ids:
                wheres.append(build_in_clause(column_ref("CS", "place_of_service_concept_id"), concept_ids))

        if criteria.place_of_service_cs is not None and criteria.place_of_service_cs.codeset_id:
            clause = codeset_in(
                column_ref("CS", "place_of_service_concept_id"),
                criteria.place_of_service_cs.codeset_id,
                exclude=criteria.place_of_service_cs.is_exclusion,
            )
            if clause is not None:
                wheres.append(clause)

        for w in wheres:
            if w is not None:
                outer = outer.where(w)

        return outer
