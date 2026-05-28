from sqlglot import exp as sge

from ..builders.utils import BuilderUtils
from ..criteria import DrugExposure
from .base import SqlGlotCriteriaBuilder
from .primitives import (
    alias_expr,
    build_date_range_clause,
    build_in_clause,
    build_numeric_range_clause,
    build_text_filter_clause,
    coalesce,
    codeset_in,
    column_ref,
    date_add,
    row_number_expr,
    year_of,
)


class DrugExposureGlotBuilder(SqlGlotCriteriaBuilder[DrugExposure]):
    def build_select(self, criteria: DrugExposure) -> sge.Select:
        inner = sge.Select()
        cols = [
            column_ref("de", "person_id"),
            column_ref("de", "drug_exposure_id"),
            column_ref("de", "drug_concept_id"),
            column_ref("de", "visit_occurrence_id"),
            column_ref("de", "days_supply"),
            column_ref("de", "quantity"),
            column_ref("de", "refills"),
        ]

        if criteria.drug_type is not None and len(criteria.drug_type) > 0:
            cols.append(column_ref("de", "drug_type_concept_id"))
        if criteria.drug_type_cs is not None:
            cols.append(column_ref("de", "drug_type_concept_id"))
        if criteria.stop_reason is not None:
            cols.append(column_ref("de", "stop_reason"))
        if criteria.route_concept is not None and len(criteria.route_concept) > 0:
            cols.append(column_ref("de", "route_concept_id"))
        if criteria.route_concept_cs is not None:
            cols.append(column_ref("de", "route_concept_id"))
        if criteria.provider_specialty is not None and len(criteria.provider_specialty) > 0:
            cols.append(column_ref("de", "provider_id"))
        if criteria.provider_specialty_cs is not None:
            cols.append(column_ref("de", "provider_id"))
        if criteria.dose_unit is not None and len(criteria.dose_unit) > 0:
            cols.append(column_ref("de", "dose_unit_concept_id"))
        if criteria.dose_unit_cs is not None:
            cols.append(column_ref("de", "dose_unit_concept_id"))
        if criteria.lot_number is not None:
            cols.append(column_ref("de", "lot_number"))

        if criteria.date_adjustment is not None:
            start_col = (
                column_ref("de", "drug_exposure_start_date")
                if criteria.date_adjustment.start_with == "start_date"
                else column_ref("de", "drug_exposure_end_date")
            )
            end_col = (
                column_ref("de", "drug_exposure_start_date")
                if criteria.date_adjustment.end_with == "start_date"
                else column_ref("de", "drug_exposure_end_date")
            )
            start_date_expr = date_add("day", criteria.date_adjustment.start_offset, start_col)
            end_date_expr = date_add("day", criteria.date_adjustment.end_offset, end_col)
        else:
            start_date_expr = column_ref("de", "drug_exposure_start_date")
            end_date_expr = coalesce(
                column_ref("de", "drug_exposure_end_date"),
                date_add(
                    "day", column_ref("de", "days_supply"), column_ref("de", "drug_exposure_start_date")
                ),
                date_add("day", 1, column_ref("de", "drug_exposure_start_date")),
            )

        cols.append(alias_expr(start_date_expr, "start_date"))
        cols.append(alias_expr(end_date_expr, "end_date"))

        inner = inner.select(*cols).from_(sge.Table(this="DRUG_EXPOSURE", alias="de"))

        if criteria.codeset_id is not None:
            cs_table = sge.Table(this="#Codesets", alias="cs")
            cs_on = sge.And(
                this=sge.EQ(
                    this=column_ref("de", "drug_concept_id"), expression=column_ref("cs", "concept_id")
                ),
                expression=sge.EQ(
                    this=column_ref("cs", "codeset_id"), expression=sge.Literal.number(criteria.codeset_id)
                ),
            )
            inner = inner.join(cs_table, on=cs_on, kind="INNER JOIN", append=True)
        if criteria.drug_source_concept is not None:
            cns_table = sge.Table(this="#Codesets", alias="cns")
            cns_on = sge.And(
                this=sge.EQ(
                    this=column_ref("de", "drug_source_concept_id"),
                    expression=column_ref("cns", "concept_id"),
                ),
                expression=sge.EQ(
                    this=column_ref("cns", "codeset_id"),
                    expression=sge.Literal.number(criteria.drug_source_concept),
                ),
            )
            inner = inner.join(cns_table, on=cns_on, kind="INNER JOIN", append=True)

        if criteria.first:
            inner = inner.select(
                alias_expr(
                    row_number_expr(
                        [column_ref("de", "person_id")],
                        [column_ref("de", "drug_exposure_start_date"), column_ref("de", "drug_exposure_id")],
                    ),
                    "ordinal",
                )
            )

        outer_cols = [
            alias_expr(column_ref("C", "person_id"), "person_id"),
            alias_expr(column_ref("C", "drug_exposure_id"), "event_id"),
            column_ref("C", "start_date"),
            column_ref("C", "end_date"),
            column_ref("C", "visit_occurrence_id"),
            alias_expr(column_ref("C", "start_date"), "sort_date"),
        ]

        outer = sge.Select().select(*outer_cols).from_(inner.subquery().as_("C"))

        if (
            criteria.age is not None
            or (criteria.gender is not None and len(criteria.gender) > 0)
            or criteria.gender_cs is not None
        ):
            outer = outer.join(
                sge.Table(this="PERSON", alias="P"),
                on=sge.EQ(this=column_ref("C", "person_id"), expression=column_ref("P", "person_id")),
                kind="JOIN",
                append=True,
            )

        if (
            criteria.visit_type is not None and len(criteria.visit_type) > 0
        ) or criteria.visit_type_cs is not None:
            outer = outer.join(
                sge.Table(this="VISIT_OCCURRENCE", alias="V"),
                on=sge.And(
                    this=sge.EQ(
                        this=column_ref("C", "visit_occurrence_id"),
                        expression=column_ref("V", "visit_occurrence_id"),
                    ),
                    expression=sge.EQ(
                        this=column_ref("C", "person_id"), expression=column_ref("V", "person_id")
                    ),
                ),
                kind="JOIN",
                append=True,
            )

        if (
            criteria.provider_specialty is not None and len(criteria.provider_specialty) > 0
        ) or criteria.provider_specialty_cs is not None:
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

        if criteria.drug_type is not None and len(criteria.drug_type) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.drug_type)
            if concept_ids:
                wheres.append(
                    build_in_clause(
                        column_ref("C", "drug_type_concept_id"),
                        concept_ids,
                        exclude=criteria.drug_type_exclude,
                    )
                )

        if criteria.drug_type_cs is not None:
            clause = codeset_in(
                column_ref("C", "drug_type_concept_id"),
                criteria.drug_type_cs.codeset_id,
                exclude=criteria.drug_type_cs.is_exclusion,
            )
            if clause is not None:
                wheres.append(clause)

        if criteria.stop_reason is not None:
            clause = build_text_filter_clause(column_ref("C", "stop_reason"), criteria.stop_reason)
            if clause is not None:
                wheres.append(clause)

        if criteria.route_concept is not None and len(criteria.route_concept) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.route_concept)
            if concept_ids:
                wheres.append(build_in_clause(column_ref("C", "route_concept_id"), concept_ids))

        if criteria.route_concept_cs is not None:
            clause = codeset_in(
                column_ref("C", "route_concept_id"),
                criteria.route_concept_cs.codeset_id,
                exclude=criteria.route_concept_cs.is_exclusion,
            )
            if clause is not None:
                wheres.append(clause)

        if criteria.dose_unit is not None and len(criteria.dose_unit) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.dose_unit)
            if concept_ids:
                wheres.append(build_in_clause(column_ref("C", "dose_unit_concept_id"), concept_ids))

        if criteria.dose_unit_cs is not None:
            clause = codeset_in(
                column_ref("C", "dose_unit_concept_id"),
                criteria.dose_unit_cs.codeset_id,
                exclude=criteria.dose_unit_cs.is_exclusion,
            )
            if clause is not None:
                wheres.append(clause)

        if criteria.lot_number is not None:
            clause = build_text_filter_clause(column_ref("C", "lot_number"), criteria.lot_number)
            if clause is not None:
                wheres.append(clause)

        if criteria.refills is not None:
            clause = build_numeric_range_clause(column_ref("C", "refills"), criteria.refills)
            if clause is not None:
                wheres.append(clause)

        if criteria.quantity is not None:
            clause = build_numeric_range_clause(column_ref("C", "quantity"), criteria.quantity)
            if clause is not None:
                wheres.append(clause)

        if criteria.days_supply is not None:
            clause = build_numeric_range_clause(column_ref("C", "days_supply"), criteria.days_supply)
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

        if criteria.gender_cs is not None:
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

        if criteria.provider_specialty_cs is not None:
            clause = codeset_in(
                column_ref("PR", "specialty_concept_id"),
                criteria.provider_specialty_cs.codeset_id,
                exclude=criteria.provider_specialty_cs.is_exclusion,
            )
            if clause is not None:
                wheres.append(clause)

        if criteria.visit_type is not None and len(criteria.visit_type) > 0:
            concept_ids = BuilderUtils.get_concept_ids_from_concepts(criteria.visit_type)
            if concept_ids:
                wheres.append(build_in_clause(column_ref("V", "visit_concept_id"), concept_ids))

        if criteria.visit_type_cs is not None:
            clause = codeset_in(
                column_ref("V", "visit_concept_id"),
                criteria.visit_type_cs.codeset_id,
                exclude=criteria.visit_type_cs.is_exclusion,
            )
            if clause is not None:
                wheres.append(clause)

        for w in wheres:
            if w is not None:
                outer = outer.where(w)

        return outer
