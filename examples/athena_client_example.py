"""
Example: Using athena-client to search for concepts and generate concept sets.

This demonstrates the athena-client API before we build the Circe integration.
"""

from athena_client import Athena

# Initialize Athena client
athena = Athena()

# Example 1: Search for diabetes concepts
print("=== Searching for diabetes concepts ===")
diabetes_results = athena.search("type 2 diabetes mellitus", limit=5)
for result in diabetes_results:
    print(f"ID: {result.concept_id}, Name: {result.concept_name}, "
          f"Domain: {result.domain_id}, Vocabulary: {result.vocabulary_id}")

# Example 2: Get concept details
print("\n=== Getting concept details ===")
concept_id = 201826  # Type 2 diabetes mellitus
details = athena.details(concept_id)
print(f"Concept: {details.concept_name}")
print(f"Standard: {details.standard_concept}")
print(f"Domain: {details.domain_id}")

# Example 3: Generate concept set (this is what we need to convert to Circe format)
print("\n=== Generating concept set ===")
concept_set = athena.generate_concept_set(
    concept_ids=[201826],  # Type 2 diabetes
    include_descendants=True,
    include_mapped=False
)

print(f"Generated concept set with {len(concept_set)} concepts")
print(f"Type: {type(concept_set)}")
print(f"First few concepts: {concept_set[:3] if concept_set else 'None'}")

# The concept_set is a list of concept IDs
# We need to convert this to Circe's ConceptSet format
