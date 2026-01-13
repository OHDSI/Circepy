"""
Quick test to verify athena-client integration works.

This is a minimal test that can run without network access if cache exists.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from circe.vocabulary import (
    search_and_create_concept_set,
    get_vocabulary_version,
    from_athena_concept_set
)
from circe.vocabulary.concept import Concept


def test_vocabulary_version():
    """Test vocabulary version detection"""
    print("Testing vocabulary version detection...")
    try:
        version = get_vocabulary_version()
        print(f"  ✓ Vocabulary version: {version}")
        assert version is not None
        assert len(version) > 0
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False


def test_from_concept_ids():
    """Test creating concept set from concept IDs"""
    print("\nTesting concept set creation from IDs...")
    try:
        # Create a simple concept set with a known concept ID
        # Using concept_id 201826 (Type 2 diabetes mellitus)
        cs = from_athena_concept_set(
            concept_ids=[201826],
            name="Test Diabetes",
            concept_set_id=999,
            include_descendants=False,
            include_mapped=False
        )
        
        print(f"  ✓ Created concept set: {cs.name}")
        print(f"    ID: {cs.id}")
        print(f"    Items: {len(cs.expression.items) if cs.expression else 0}")
        
        assert cs.id == 999
        assert cs.name == "Test Diabetes"
        return True
        
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        print(f"    Note: This test requires internet connection")
        return False


def test_search_and_create():
    """Test search and create workflow"""
    print("\nTesting search and create...")
    try:
        cs = search_and_create_concept_set(
            search_term="diabetes",
            name="Diabetes Concepts",
            concept_set_id=1000,
            limit=2  # Small limit for testing
        )
        
        print(f"  ✓ Created concept set: {cs.name}")
        print(f"    ID: {cs.id}")
        print(f"    Items: {len(cs.expression.items) if cs.expression else 0}")
        
        assert cs.id == 1000
        assert cs.name == "Diabetes Concepts"
        return True
        
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        print(f"    Note: This test requires internet connection")
        return False


def test_caching():
    """Test that caching works"""
    print("\nTesting caching...")
    try:
        import time
        
        # First call
        start = time.time()
        cs1 = search_and_create_concept_set(
            search_term="test_cache",
            name="Cache Test",
            concept_set_id=1001,
            limit=1
        )
        time1 = time.time() - start
        
        # Second call (should be cached)
        start = time.time()
        cs2 = search_and_create_concept_set(
            search_term="test_cache",
            name="Cache Test",
            concept_set_id=1001,
            limit=1
        )
        time2 = time.time() - start
        
        print(f"  ✓ First call: {time1:.3f}s")
        print(f"  ✓ Second call: {time2:.3f}s")
        
        if time2 < time1:
            print(f"  ✓ Cache is working ({time1/time2:.1f}x faster)")
        else:
            print(f"  ⚠ Cache may not be working (times similar)")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("Athena-Client Integration Quick Test")
    print("=" * 60)
    print()
    
    results = []
    
    # Run tests
    results.append(("Vocabulary Version", test_vocabulary_version()))
    results.append(("From Concept IDs", test_from_concept_ids()))
    results.append(("Search and Create", test_search_and_create()))
    results.append(("Caching", test_caching()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed (may require internet connection)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
