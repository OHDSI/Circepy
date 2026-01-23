from circe.cohortdefinition.cohort import CohortExpression
from circe.cohortdefinition.core import CollapseSettings, CollapseType, DateOffsetStrategy, NumericRange, ObservationFilter, Period, ResultLimit, Window, WindowBound
from circe.cohortdefinition.criteria import ConditionOccurrence, CorelatedCriteria, CriteriaGroup, InclusionRule, Measurement, Observation, Occurrence, PrimaryCriteria
from circe.vocabulary.concept import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem

cohort = CohortExpression(
    concept_sets=[
        ConceptSet(
            id=7,
            name='Platelet measurement',
            expression=ConceptSetExpression(
                items=[
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=4267147,
                            concept_name='Platelet count',
                            concept_code='61928009',
                            concept_class_id='Procedure',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Measurement',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=3031586,
                            concept_name='Platelets [#/volume] in Blood by Estimate',
                            concept_code='49497-1',
                            concept_class_id='Lab Test',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Measurement',
                            vocabulary_id='LOINC'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=3050583,
                            concept_name='Platelets panel - Blood by Automated count',
                            concept_code='53800-9',
                            concept_class_id='Lab Test',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Measurement',
                            vocabulary_id='LOINC'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=3007461,
                            concept_name='Platelets [#/volume] in Blood',
                            concept_code='26515-7',
                            concept_class_id='Lab Test',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Measurement',
                            vocabulary_id='LOINC'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=37393863,
                            concept_name='Platelet count',
                            concept_code='1022651000000100',
                            concept_class_id='Observable Entity',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Measurement',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    )
                ]
            )
        ),
        ConceptSet(
            id=9,
            name='Congenital or genetic causes for thrombocytopenia',
            expression=ConceptSetExpression(
                items=[
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=37397537,
                            concept_name='Beta thalassemia X-linked thrombocytopenia syndrome',
                            concept_code='718196002',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=4121131,
                            concept_name='Inherited platelet disorder',
                            concept_code='234469001',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=4006469,
                            concept_name='Reticular dysgenesis',
                            concept_code='111584000',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=42537688,
                            concept_name='Congenital thrombocytopenia',
                            concept_code='737221003',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=437242,
                            concept_name='Congenital thrombocytopenic purpura',
                            concept_code='267535004',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    )
                ]
            )
        ),
        ConceptSet(
            id=10,
            name='Thrombocytosis',
            expression=ConceptSetExpression(
                items=[
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=4280071,
                            concept_name='Thrombocytosis',
                            concept_code='6631009',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=36715584,
                            concept_name='Refractory anemia with ringed sideroblasts associated with marked thrombocytosis',
                            concept_code='721302006',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=45766614,
                            concept_name='Refractory anemia with ring sideroblasts associated with marked thrombocytosis',
                            concept_code='703817002',
                            concept_class_id='Morph Abnormality',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Observation',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    )
                ]
            )
        ),
        ConceptSet(
            id=24,
            name='Pancytopenia & bone marrow disorder',
            expression=ConceptSetExpression(
                items=[
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=432881,
                            concept_name='Pancytopenia',
                            concept_code='127034005',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=4131124,
                            concept_name='Bone marrow disorder',
                            concept_code='127035006',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    )
                ]
            )
        ),
        ConceptSet(
            id=25,
            name='Neutropenia, Agranulocytosis or Unspecified Leukopenia',
            expression=ConceptSetExpression(
                items=[
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=36715585,
                            concept_name='Refractory neutropenia',
                            concept_code='721303001',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=320073,
                            concept_name='Neutropenia',
                            concept_code='165517008',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=42872951,
                            concept_name='Refractory neutropenia',
                            concept_code='450946009',
                            concept_class_id='Morph Abnormality',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Observation',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=435224,
                            concept_name='Leukopenia',
                            concept_code='84828003',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        )
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=440689,
                            concept_name='Agranulocytosis',
                            concept_code='17182001',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=45766061,
                            concept_name='Periodontitis associated with chronic familial neutropenia',
                            concept_code='703148008',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=4119158,
                            concept_name='Neutropenic disorder',
                            concept_code='303011007',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    )
                ]
            )
        ),
        ConceptSet(
            id=26,
            name='Neutrophil Absolute Count',
            expression=ConceptSetExpression(
                items=[
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=37393856,
                            concept_name='Neutrophil count',
                            concept_code='1022551000000104',
                            concept_class_id='Observable Entity',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Measurement',
                            vocabulary_id='SNOMED'
                        )
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=4148615,
                            concept_name='Neutrophil count',
                            concept_code='30630007',
                            concept_class_id='Procedure',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Measurement',
                            vocabulary_id='SNOMED'
                        )
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=3017732,
                            concept_name='Neutrophils [#/volume] in Blood',
                            concept_code='26499-4',
                            concept_class_id='Lab Test',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Measurement',
                            vocabulary_id='LOINC'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=3013650,
                            concept_name='Neutrophils [#/volume] in Blood by Automated count',
                            concept_code='751-8',
                            concept_class_id='Lab Test',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Measurement',
                            vocabulary_id='LOINC'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=3017501,
                            concept_name='Neutrophils [#/volume] in Blood by Manual count',
                            concept_code='753-4',
                            concept_class_id='Lab Test',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Measurement',
                            vocabulary_id='LOINC'
                        ),
                        include_descendants=True
                    )
                ]
            )
        ),
        ConceptSet(
            id=27,
            name='Anemia or Reticulocytopenia',
            expression=ConceptSetExpression(
                items=[
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=2617149,
                            concept_name='Erythropoetic stimulating agent (esa) administered to treat anemia due to anti-cancer radiotherapy',
                            concept_code='EB',
                            concept_class_id='HCPCS Modifier',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Observation',
                            vocabulary_id='HCPCS'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=36716029,
                            concept_name='Hyperuricemia, anemia, renal failure syndrome',
                            concept_code='721840000',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=2617148,
                            concept_name='Erythropoetic stimulating agent (esa) administered to treat anemia due to anti-cancer chemotherapy',
                            concept_code='EA',
                            concept_class_id='HCPCS Modifier',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Observation',
                            vocabulary_id='HCPCS'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=4029669,
                            concept_name='Refractory anemia with sideroblasts',
                            concept_code='128846006',
                            concept_class_id='Morph Abnormality',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Observation',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=4120449,
                            concept_name="von Jaksch's anemia",
                            concept_code='234345001',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=35624756,
                            concept_name='Anemia due to and following chemotherapy',
                            concept_code='767657005',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=4028718,
                            concept_name='Refractory anemia with excess blasts',
                            concept_code='128847002',
                            concept_class_id='Morph Abnormality',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Observation',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=37017165,
                            concept_name='GATA binding protein 1 related thrombocytopenia with dyserythropoiesis',
                            concept_code='713388002',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=4144746,
                            concept_name='Hereditary hemoglobinopathy',
                            concept_code='427306008',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=2617150,
                            concept_name='Erythropoetic stimulating agent (esa) administered to treat anemia not due to anti-cancer radiotherapy or anti-cancer chemotherapy',
                            concept_code='EC',
                            concept_class_id='HCPCS Modifier',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Observation',
                            vocabulary_id='HCPCS'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=44831063,
                            concept_name='Anemia associated with other specified nutritional deficiency',
                            concept_code='281.8',
                            concept_class_id='4-dig billing code',
                            standard_concept='N',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='ICD9CM'
                        )
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=4105643,
                            concept_name='Myasthenic syndrome due to pernicious anemia',
                            concept_code='193213003',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=37398911,
                            concept_name='Anemia in chronic kidney disease stage 4',
                            concept_code='691401000119104',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=438869,
                            concept_name='Perinatal jaundice due to hereditary hemolytic anemia',
                            concept_code='56921004',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=4183718,
                            concept_name='Pericarditis associated with severe chronic anemia',
                            concept_code='43742007',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=37395652,
                            concept_name='Anemia in chronic kidney disease stage 5',
                            concept_code='691411000119101',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=4125630,
                            concept_name='Chronic non-spherocytic hemolytic anemia',
                            concept_code='234402007',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=4217370,
                            concept_name='Aase syndrome',
                            concept_code='71988008',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=4267432,
                            concept_name='Erythropenia',
                            concept_code='62574001',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=36680584,
                            concept_name='Autosomal dominant aplasia and myelodysplasia',
                            concept_code='778006008',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=37018722,
                            concept_name='Anemia caused by zidovudine',
                            concept_code='713496008',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=4295183,
                            concept_name='Mixed hemoglobin disorder',
                            concept_code='38589006',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=4028717,
                            concept_name='Refractory anemia',
                            concept_code='128845005',
                            concept_class_id='Morph Abnormality',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Observation',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=44783626,
                            concept_name='Pulmonary arterial hypertension associated with chronic hemolytic anemia',
                            concept_code='697908003',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=4159748,
                            concept_name='Hand-foot syndrome in sickle cell anemia',
                            concept_code='371104006',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=4051681,
                            concept_name='Reticulocytopenia',
                            concept_code='124961001',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=37017132,
                            concept_name='Anemia co-occurrent with human immunodeficiency virus infection',
                            concept_code='713349004',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=4029670,
                            concept_name='Refractory anemia with excess blasts in transformation',
                            concept_code='128848007',
                            concept_class_id='Morph Abnormality',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Observation',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=4006467,
                            concept_name='Anemia due to infection',
                            concept_code='111570005',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=40478891,
                            concept_name='Erythropoietin resistance in anemia of chronic kidney disease',
                            concept_code='444271000',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=36715584,
                            concept_name='Refractory anemia with ringed sideroblasts associated with marked thrombocytosis',
                            concept_code='721302006',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    )
                ]
            )
        ),
        ConceptSet(
            id=28,
            name='Hemoglobin measurement',
            expression=ConceptSetExpression(
                items=[
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=3000963,
                            concept_name='Hemoglobin [Mass/volume] in Blood',
                            concept_code='718-7',
                            concept_class_id='Lab Test',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Measurement',
                            vocabulary_id='LOINC'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=3027484,
                            concept_name='Hemoglobin [Mass/volume] in Blood by calculation',
                            concept_code='20509-6',
                            concept_class_id='Lab Test',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Measurement',
                            vocabulary_id='LOINC'
                        ),
                        include_descendants=True
                    )
                ]
            )
        ),
        ConceptSet(
            id=30,
            name='Immune Thrombocytopenia',
            expression=ConceptSetExpression(
                items=[
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=4103532,
                            concept_name='Immune thrombocytopenia',
                            concept_code='2897005',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    ),
                    ConceptSetItem(
                        concept=Concept(
                            concept_id=4119134,
                            concept_name='Thrombocytopenic purpura',
                            concept_code='302873008',
                            concept_class_id='Clinical Finding',
                            standard_concept='S',
                            invalid_reason='V',
                            domain_id='Condition',
                            vocabulary_id='SNOMED'
                        ),
                        include_descendants=True
                    )
                ]
            )
        )
    ],
    qualified_limit=ResultLimit(type='First'),
    end_strategy=DateOffsetStrategy(offset=0, date_field='EndDate'),
    primary_criteria=PrimaryCriteria(
        criteria_list=[ConditionOccurrence(codeset_id=30, first=False)],
        observation_window=ObservationFilter(prior_days=0, post_days=0),
        primary_limit=ResultLimit(type='All')
    ),
    expression_limit=ResultLimit(type='All'),
    collapse_settings=CollapseSettings(era_pad=0, collapse_type=CollapseType.ERA),
    inclusion_rules=[
        InclusionRule(
            expression=CriteriaGroup(
                criteria_list=[
                    CorelatedCriteria(
                        criteria=ConditionOccurrence(codeset_id=9, first=False),
                        start_window=Window(
                            start=WindowBound(coeff=-1),
                            end=WindowBound(coeff=1, days=7),
                            use_event_end=False,
                            use_index_end=False
                        ),
                        ignore_observation_period=True,
                        occurrence=Occurrence(type=0, count=0)
                    )
                ],
                groups=[],
                demographic_criteria_list=[],
                type='ALL'
            ),
            name='No congenital or genetic thrombocytopenia'
        ),
        InclusionRule(
            expression=CriteriaGroup(
                criteria_list=[
                    CorelatedCriteria(
                        criteria=Measurement(
                            value_as_number=NumericRange(op='bt', value=101, extent=450),
                            unit=[
                                Concept(
                                    concept_id=8848,
                                    concept_name='thousand per microliter',
                                    concept_code='10*3/uL',
                                    domain_id='Unit',
                                    vocabulary_id='UCUM'
                                ),
                                Concept(
                                    concept_id=8961,
                                    concept_name='thousand per cubic millimeter',
                                    concept_code='10*3/mm3',
                                    domain_id='Unit',
                                    vocabulary_id='UCUM'
                                ),
                                Concept(
                                    concept_id=9444,
                                    concept_name='billion per liter',
                                    concept_code='10*9/L',
                                    domain_id='Unit',
                                    vocabulary_id='UCUM'
                                ),
                                Concept(
                                    concept_id=8816,
                                    concept_name='million per milliliter',
                                    concept_code='10*6/mL',
                                    domain_id='Unit',
                                    vocabulary_id='UCUM'
                                ),
                                Concept(
                                    concept_id=44777588,
                                    concept_name='billion cells per liter',
                                    concept_code='10*9.{cellls}/L',
                                    domain_id='Unit',
                                    vocabulary_id='UCUM'
                                )
                            ],
                            codeset_id=7,
                            first=False
                        ),
                        start_window=Window(
                            start=WindowBound(coeff=-1, days=0),
                            end=WindowBound(coeff=1, days=0),
                            use_event_end=False,
                            use_index_end=False
                        ),
                        ignore_observation_period=True,
                        occurrence=Occurrence(type=0, count=0)
                    )
                ],
                groups=[],
                demographic_criteria_list=[],
                type='ALL'
            ),
            name='No Platelet count > 100 on index date'
        ),
        InclusionRule(
            expression=CriteriaGroup(
                criteria_list=[
                    CorelatedCriteria(
                        criteria=ConditionOccurrence(codeset_id=10, first=False),
                        start_window=Window(
                            start=WindowBound(coeff=-1, days=0),
                            end=WindowBound(coeff=1, days=0),
                            use_event_end=False,
                            use_index_end=False
                        ),
                        ignore_observation_period=True,
                        occurrence=Occurrence(type=0, count=0)
                    )
                ],
                groups=[],
                demographic_criteria_list=[],
                type='ALL'
            ),
            name='No thrombocytosis on index date'
        ),
        InclusionRule(
            expression=CriteriaGroup(
                criteria_list=[
                    CorelatedCriteria(
                        criteria=ConditionOccurrence(codeset_id=24, first=False),
                        start_window=Window(
                            start=WindowBound(coeff=-1, days=7),
                            end=WindowBound(coeff=1, days=7),
                            use_event_end=False,
                            use_index_end=False
                        ),
                        ignore_observation_period=True,
                        occurrence=Occurrence(type=0, count=0)
                    )
                ],
                groups=[],
                demographic_criteria_list=[],
                type='ALL'
            ),
            name='No Pancytopenia or bone marrow disorder diagnosis within 7 days'
        ),
        InclusionRule(
            expression=CriteriaGroup(
                criteria_list=[
                    CorelatedCriteria(
                        criteria=ConditionOccurrence(codeset_id=25, first=False),
                        start_window=Window(
                            start=WindowBound(coeff=-1, days=7),
                            end=WindowBound(coeff=1, days=7),
                            use_event_end=False,
                            use_index_end=False
                        ),
                        ignore_observation_period=True,
                        occurrence=Occurrence(type=0, count=0)
                    )
                ],
                groups=[],
                demographic_criteria_list=[],
                type='ALL'
            ),
            name='No Neutropenia, Agranulocytosis diagnosis within 7 days'
        ),
        InclusionRule(
            expression=CriteriaGroup(
                criteria_list=[
                    CorelatedCriteria(
                        criteria=Measurement(
                            value_as_number=NumericRange(op='bt', value=0.01, extent=1.499),
                            unit=[
                                Concept(
                                    concept_id=9444,
                                    concept_name='billion per liter',
                                    concept_code='10*9/L',
                                    domain_id='Unit',
                                    vocabulary_id='UCUM'
                                ),
                                Concept(
                                    concept_id=8848,
                                    concept_name='thousand per microliter',
                                    concept_code='10*3/uL',
                                    domain_id='Unit',
                                    vocabulary_id='UCUM'
                                ),
                                Concept(
                                    concept_id=8816,
                                    concept_name='million per milliliter',
                                    concept_code='10*6/mL',
                                    domain_id='Unit',
                                    vocabulary_id='UCUM'
                                ),
                                Concept(
                                    concept_id=8961,
                                    concept_name='thousand per cubic millimeter',
                                    concept_code='10*3/mm3',
                                    domain_id='Unit',
                                    vocabulary_id='UCUM'
                                ),
                                Concept(
                                    concept_id=44777588,
                                    concept_name='billion cells per liter',
                                    concept_code='10*9.{cellls}/L',
                                    domain_id='Unit',
                                    vocabulary_id='UCUM'
                                )
                            ],
                            range_low=NumericRange(op='bt', value=1.5, extent=4),
                            codeset_id=26,
                            first=False
                        ),
                        start_window=Window(
                            start=WindowBound(coeff=-1, days=7),
                            end=WindowBound(coeff=-1, days=7),
                            use_event_end=False,
                            use_index_end=False
                        ),
                        ignore_observation_period=True,
                        occurrence=Occurrence(type=0, count=0)
                    ),
                    CorelatedCriteria(
                        criteria=Measurement(
                            value_as_number=NumericRange(op='bt', value=10, extent=1500),
                            unit=[
                                Concept(
                                    concept_id=8784,
                                    concept_name='cells per microliter',
                                    concept_code='{cells}/uL',
                                    domain_id='Unit',
                                    vocabulary_id='UCUM'
                                ),
                                Concept(
                                    concept_id=8647,
                                    concept_name='per microliter',
                                    concept_code='/uL',
                                    domain_id='Unit',
                                    vocabulary_id='UCUM'
                                )
                            ],
                            codeset_id=26,
                            first=False
                        ),
                        start_window=Window(
                            start=WindowBound(coeff=-1, days=7),
                            end=WindowBound(coeff=1, days=7),
                            use_event_end=False,
                            use_index_end=False
                        ),
                        ignore_observation_period=True,
                        occurrence=Occurrence(type=0, count=0)
                    )
                ],
                groups=[],
                demographic_criteria_list=[],
                type='ALL'
            ),
            name='No low neutrophil count within 7 days'
        ),
        InclusionRule(
            expression=CriteriaGroup(
                criteria_list=[
                    CorelatedCriteria(
                        criteria=ConditionOccurrence(codeset_id=27, first=False),
                        start_window=Window(
                            start=WindowBound(coeff=-1, days=7),
                            end=WindowBound(coeff=1, days=7),
                            use_event_end=False,
                            use_index_end=False
                        ),
                        ignore_observation_period=True,
                        occurrence=Occurrence(type=0, count=0)
                    ),
                    CorelatedCriteria(
                        criteria=Observation(codeset_id=27, first=False),
                        start_window=Window(
                            start=WindowBound(coeff=-1, days=7),
                            end=WindowBound(coeff=1, days=7),
                            use_event_end=False,
                            use_index_end=False
                        ),
                        ignore_observation_period=True,
                        occurrence=Occurrence(type=0, count=0)
                    )
                ],
                groups=[],
                demographic_criteria_list=[],
                type='ALL'
            ),
            name='No Anemia diagnosis within 7 days'
        ),
        InclusionRule(
            expression=CriteriaGroup(
                criteria_list=[
                    CorelatedCriteria(
                        criteria=Measurement(
                            value_as_number=NumericRange(op='bt', value=4, extent=11),
                            unit=[
                                Concept(
                                    concept_id=4121395,
                                    concept_name='g/dL',
                                    concept_code='258795003',
                                    domain_id='Unit',
                                    vocabulary_id='SNOMED'
                                ),
                                Concept(
                                    concept_id=8713,
                                    concept_name='gram per deciliter',
                                    concept_code='g/dL',
                                    domain_id='Unit',
                                    vocabulary_id='UCUM'
                                ),
                                Concept(
                                    concept_id=8950,
                                    concept_name='gram per deciliter calculated',
                                    concept_code='g/dL{calc}',
                                    domain_id='Unit',
                                    vocabulary_id='UCUM'
                                )
                            ],
                            codeset_id=28,
                            first=False
                        ),
                        start_window=Window(
                            start=WindowBound(coeff=-1, days=7),
                            end=WindowBound(coeff=1, days=7),
                            use_event_end=False,
                            use_index_end=False
                        ),
                        ignore_observation_period=True,
                        occurrence=Occurrence(type=0, count=0)
                    )
                ],
                groups=[],
                demographic_criteria_list=[],
                type='ALL'
            ),
            name='No low Hemoglobin measurement in blood within 7 days'
        )
    ],
    censor_window=Period(),
    censoring_criteria=[
        Measurement(
            value_as_number=NumericRange(op='bt', value=150, extent=450),
            unit=[
                Concept(
                    concept_id=8848,
                    concept_name='thousand per microliter',
                    concept_code='10*3/uL',
                    domain_id='Unit',
                    vocabulary_id='UCUM'
                ),
                Concept(
                    concept_id=8961,
                    concept_name='thousand per cubic millimeter',
                    concept_code='10*3/mm3',
                    domain_id='Unit',
                    vocabulary_id='UCUM'
                ),
                Concept(
                    concept_id=9444,
                    concept_name='billion per liter',
                    concept_code='10*9/L',
                    domain_id='Unit',
                    vocabulary_id='UCUM'
                ),
                Concept(
                    concept_id=8816,
                    concept_name='million per milliliter',
                    concept_code='10*6/mL',
                    domain_id='Unit',
                    vocabulary_id='UCUM'
                ),
                Concept(
                    concept_id=44777588,
                    concept_name='billion cells per liter',
                    concept_code='10*9.{cellls}/L',
                    domain_id='Unit',
                    vocabulary_id='UCUM'
                )
            ],
            codeset_id=7,
            first=False
        ),
        ConditionOccurrence(codeset_id=10, first=False)
    ]
)