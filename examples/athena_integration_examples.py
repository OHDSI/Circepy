"""
Athena-Client Integration Examples

This script demonstrates how to use athena-client with Circe for building
phenotypes. Perfect for LLM/chatbot workflows.

Examples:
1. Simple search and convert
2. Cached workflow demonstration
3. Building a complete cohort with athena concepts
4. Batch import of multiple concept sets
"""

from circe.vocabulary import (
    search_and_create_concept_set,
    from_athena_concept_set,
    get_vocabulary_version,
    clear_cache
)
from circe.cohortdefinition import CohortExpression, PrimaryCriteria
from circe.cohortdefinition.criteria import DrugExposure, ConditionOccurrence, CorelatedCriteria
from circe.cohortdefinition.core import Window, WindowBound
import time


def example_1_simple_search():
    """Example 1: Simple search and convert to Circe ConceptSet"""
    print("=" * 60)
    print("Example 1: Simple Search and Convert")
    print("=" * 60)
    
    # Search for diabetes and create concept set
    diabetes = search_and_create_concept_set(
        search_term="type 2 diabetes mellitus",
        name="Type 2 Diabetes",
        concept_set_id=1,
        limit=5  # Limit to 5 concepts for demo
    )
    
    print(f"Created concept set: {diabetes.name}")
    print(f"  ID: {diabetes.id}")
    print(f"  Number of concepts: {len(diabetes.expression.items) if diabetes.expression else 0}")
    
    if diabetes.expression and diabetes.expression.items:
        print(f"  First concept: {diabetes.expression.items[0].concept.concept_name}")
    
    print()
    return diabetes


def example_2_caching_demo():
    """Example 2: Demonstrate caching performance"""
    print("=" * 60)
    print("Example 2: Caching Performance")
    print("=" * 60)
    
    # First call - fetches from API
    print("First call (from API)...")
    start = time.time()
    metformin1 = search_and_create_concept_set(
        search_term="metformin",
        name="Metformin",
        concept_set_id=2,
        limit=3
    )
    time1 = time.time() - start
    print(f"  Time: {time1:.2f}s")
    
    # Second call - loads from cache
    print("\nSecond call (from cache)...")
    start = time.time()
    metformin2 = search_and_create_concept_set(
        search_term="metformin",
        name="Metformin",
        concept_set_id=2,
        limit=3
    )
    time2 = time.time() - start
    print(f"  Time: {time2:.2f}s")
    print(f"  Speedup: {time1/time2:.1f}x faster")
    
    print()
    return metformin1


def example_3_complete_cohort():
    """Example 3: Build complete cohort using athena concepts"""
    print("=" * 60)
    print("Example 3: Complete Cohort Definition")
    print("=" * 60)
    
    # Create concept sets
    print("Creating concept sets...")
    diabetes = search_and_create_concept_set(
        search_term="type 2 diabetes",
        name="Type 2 Diabetes",
        concept_set_id=1,
        limit=3
    )
    
    metformin = search_and_create_concept_set(
        search_term="metformin",
        name="Metformin",
        concept_set_id=2,
        limit=3
    )
    
    # Build cohort: Patients with diabetes who started metformin
    print("\nBuilding cohort definition...")
    cohort = CohortExpression(
        title="Type 2 Diabetes Patients Starting Metformin",
        concept_sets=[diabetes, metformin],
        primary_criteria=PrimaryCriteria(
            criteria_list=[
                ConditionOccurrence(
                    codeset_id=1,  # Type 2 Diabetes
                    first=True
                )
            ]
        ),
        additional_criteria=None  # Could add metformin requirement here
    )
    
    print(f"Cohort created: {cohort.title}")
    print(f"  Concept sets: {len(cohort.concept_sets)}")
    print(f"  Primary criteria: {len(cohort.primary_criteria.criteria_list)}")
    
    # Generate SQL
    print("\nGenerating SQL...")
    sql = cohort.to_sql(dialect="postgresql")
    print(f"  SQL length: {len(sql)} characters")
    print(f"  First 200 chars: {sql[:200]}...")
    
    print()
    return cohort


def example_4_batch_import():
    """Example 4: Batch import multiple concept sets"""
    print("=" * 60)
    print("Example 4: Batch Import")
    print("=" * 60)
    
    # Define multiple concept sets to import
    concept_definitions = [
        ("hypertension", "Hypertension", 10),
        ("myocardial infarction", "MI", 11),
        ("stroke", "Stroke", 12),
    ]
    
    concept_sets = []
    for search_term, name, cs_id in concept_definitions:
        print(f"Importing: {name}...")
        cs = search_and_create_concept_set(
            search_term=search_term,
            name=name,
            concept_set_id=cs_id,
            limit=2  # Small limit for demo
        )
        concept_sets.append(cs)
    
    print(f"\nImported {len(concept_sets)} concept sets")
    for cs in concept_sets:
        item_count = len(cs.expression.items) if cs.expression else 0
        print(f"  - {cs.name}: {item_count} concepts")
    
    print()
    return concept_sets


def example_5_vocabulary_version():
    """Example 5: Check vocabulary version"""
    print("=" * 60)
    print("Example 5: Vocabulary Version")
    print("=" * 60)
    
    version = get_vocabulary_version()
    print(f"Current vocabulary version: {version}")
    print(f"Cache location: ~/.circe/concept_cache/{version}/")
    
    print()


def main():
    """Run all examples"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "Athena-Client Integration Examples" + " " * 13 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    try:
        # Run examples
        example_1_simple_search()
        example_2_caching_demo()
        example_3_complete_cohort()
        example_4_batch_import()
        example_5_vocabulary_version()
        
        print("=" * 60)
        print("✅ All examples completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        print("\nNote: These examples require internet connection to access")
        print("the OHDSI Athena API. If you're offline, cached results will")
        print("be used when available.")


if __name__ == "__main__":
    main()
