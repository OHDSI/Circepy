
import unittest
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path
import shutil
import tempfile
import json
from datetime import datetime

from circe.vocabulary.athena_integration import (
    get_vocabulary_version,
    _get_cache_path,
    load_cached_concept_set,
    save_concept_set_to_cache,
    from_athena_concept_set,
    search_and_create_concept_set,
    clear_cache,
    DEFAULT_CACHE_DIR
)
from circe.vocabulary.concept import ConceptSet, ConceptSetExpression, ConceptSetItem, Concept


class TestAthenaIntegration(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for testing cache
        self.test_dir = tempfile.mkdtemp()
        self.cache_dir = Path(self.test_dir)
        
        # Reset the global vocabulary version cache before each test
        import circe.vocabulary.athena_integration as module
        module._VOCABULARY_VERSION_CACHE = None

    def tearDown(self):
        # Remove the directory after the test
        shutil.rmtree(self.test_dir)

    @patch('circe.vocabulary.athena_integration.Athena')
    def test_get_vocabulary_version_success(self, mock_athena_cls):
        # Setup mock
        mock_client = MagicMock()
        result_mock = MagicMock()
        result_mock.vocabulary_version = "v5.0_TEST"
        mock_client.details.return_value = result_mock
        mock_athena_cls.return_value = mock_client
        
        # Test
        version = get_vocabulary_version(mock_client)
        
        # Assert
        self.assertEqual(version, "v5.0_TEST")
        mock_client.details.assert_called_with(0)

    @patch('circe.vocabulary.athena_integration.Athena')
    def test_get_vocabulary_version_fallback_missing_attr(self, mock_athena_cls):
        # Setup mock to return result without version
        mock_client = MagicMock()
        result_mock = MagicMock()
        del result_mock.vocabulary_version 
        # Make sure it raises AttributeError if accessed, or just doesn't have it
        # In the code it uses hasattr check
        mock_client.details.return_value = result_mock
        mock_athena_cls.return_value = mock_client
        
        # Test
        version = get_vocabulary_version(mock_client)
        
        # Assert
        self.assertTrue(version.startswith("v5.0_"))
        self.assertIn(datetime.now().strftime('%d-%b-%y').upper(), version)

    @patch('circe.vocabulary.athena_integration.Athena')
    def test_get_vocabulary_version_exception(self, mock_athena_cls):
        # Setup mock to raise exception
        mock_client = MagicMock()
        mock_client.details.side_effect = Exception("API Error")
        mock_athena_cls.return_value = mock_client
        
        # Test
        version = get_vocabulary_version(mock_client)
        
        # Assert
        self.assertTrue(version.startswith("v5.0_"))

    def test_get_cache_path(self):
        path = _get_cache_path("key/with/slashes", self.cache_dir, "v1")
        expected = self.cache_dir / "v1" / "key_with_slashes.json"
        self.assertEqual(path, expected)

    def test_save_and_load_concept_set(self):
        # Create a dummy concept set
        cs = ConceptSet(
            id=1,
            name="Test Set",
            expression=ConceptSetExpression(items=[])
        )
        
        # Save
        save_concept_set_to_cache(cs, "test_key", self.cache_dir, "v1")
        
        # Verify file exists
        expected_path = self.cache_dir / "v1" / "test_key.json"
        self.assertTrue(expected_path.exists())
        
        # Load
        loaded_cs = load_cached_concept_set("test_key", self.cache_dir, "v1")
        self.assertIsNotNone(loaded_cs)
        self.assertEqual(loaded_cs.name, "Test Set")

    def test_load_cache_miss(self):
        result = load_cached_concept_set("non_existent", self.cache_dir, "v1")
        self.assertIsNone(result)

    def test_load_version_mismatch(self):
        # Create a cache file manually with old version
        version_dir = self.cache_dir / "v1"
        version_dir.mkdir(parents=True)
        file_path = version_dir / "test.json"
        
        data = {
            'metadata': {'vocabulary_version': 'v1'},
            'concept_set': ConceptSet(id=1, name="set", expression=ConceptSetExpression(items=[])).model_dump(by_alias=True)
        }
        with open(file_path, 'w') as f:
            json.dump(data, f)
            
        # Try to load with different version expectation
        result = load_cached_concept_set("test", self.cache_dir, "v2")
        # Note: _get_cache_path uses the passed version to find the file
        # If we pass v2, it looks in v2 dir. The file is in v1 dir.
        # So it's a simple cache miss unless the function logic is to check file metadata against current expectation
        
        # The function `load_cached_concept_set` constructs path using `vocabulary_version`.
        # If we pass "v2", it looks in ".../v2/test.json". It won't find it.
        # To test the mismatch logic *inside* the function, we must force it to read a file 
        # where metadata says X but we expect Y, AND expected Y is what determined the path.
        # Wait, if version determines path, then path implicitly guarantees version?
        # UNLESS `vocabulary_version` passed to `load_cached_concept_set` is None, 
        # and it autodects generic version, but we found a file that claims to be another version?
        # Actually, looking at code: 
        # 1. path = _get_cache_path(..., version)
        # 2. open(path)
        # 3. check cached_version != current_version
        # This implies we successfully opened the file. 
        # So we must verify against the version *passed in* or *detected*.
        
        # Let's try to simulate a case where we found the file but version is wrong.
        # This can happen if I put a file in "v2" folder but metadata inside says "v1".
        
        wrong_dir = self.cache_dir / "v2"
        wrong_dir.mkdir(parents=True, exist_ok=True)
        file_path = wrong_dir / "test_mismatch.json"
        with open(file_path, 'w') as f:
            json.dump(data, f) # metadata says v1
            
        result = load_cached_concept_set("test_mismatch", self.cache_dir, "v2")
        self.assertIsNone(result)

    @patch('circe.vocabulary.athena_integration.Athena')
    def test_from_athena_concept_set_api(self, mock_athena_cls):
        mock_client = MagicMock()
        mock_athena_cls.return_value = mock_client
        
        # Mock details response
        details = MagicMock()
        details.concept_id = 123
        details.concept_name = "Test Concept"
        details.concept_code = "C1"
        details.concept_class_id = "Class"
        details.standard_concept = "S"
        details.invalid_reason = None
        details.domain_id = "Condition"
        details.vocabulary_id = "SNOMED"
        
        mock_client.details.return_value = details
        
        # Test
        cs = from_athena_concept_set(
            concept_ids=[123],
            name="Test Set",
            concept_set_id=1,
            cache_dir=self.cache_dir,
            vocabulary_version="v1",
            athena_client=mock_client
        )
        
        self.assertEqual(cs.name, "Test Set")
        self.assertEqual(len(cs.expression.items), 1)
        self.assertEqual(cs.expression.items[0].concept.concept_id, 123)
        
        # Verify it was cached
        cached = load_cached_concept_set("ids_123_True_False", self.cache_dir, "v1")
        self.assertIsNotNone(cached)

    @patch('circe.vocabulary.athena_integration.Athena')
    def test_from_athena_concept_set_exception(self, mock_athena_cls):
        mock_client = MagicMock()
        
        # details raises exception
        mock_client.details.side_effect = Exception("Concept not found")
        
        cs = from_athena_concept_set(
            concept_ids=[999],
            name="Empty Set",
            concept_set_id=1,
            cache_dir=self.cache_dir,
            athena_client=mock_client
        )
        
        self.assertEqual(len(cs.expression.items), 0)

    @patch('circe.vocabulary.athena_integration.Athena')
    def test_search_and_create_concept_set(self, mock_athena_cls):
        mock_client = MagicMock()
        
        # Search returns results
        search_result = MagicMock()
        search_result.concept_id = 100
        mock_client.search.return_value = [search_result]
        
        # Details called for the result
        details = MagicMock()
        details.concept_id = 100
        details.concept_name = "Result Concept"
        # ... populate other required fields to avoid validation errors
        details.concept_code = "C1"
        details.concept_class_id = "Class" 
        details.standard_concept = "S"
        details.invalid_reason = None
        details.domain_id = "Domain"
        details.vocabulary_id = "Vocab"
        
        mock_client.details.return_value = details
        
        cs = search_and_create_concept_set(
            search_term="test query",
            name="Set",
            concept_set_id=1,
            cache_dir=self.cache_dir,
            vocabulary_version="v1",
            athena_client=mock_client
        )
        
        self.assertEqual(len(cs.expression.items), 1)
        mock_client.search.assert_called_with("test query", limit=10)

    @patch('circe.vocabulary.athena_integration.Athena')
    def test_search_and_create_empty(self, mock_athena_cls):
        mock_client = MagicMock()
        mock_client.search.return_value = []
        
        cs = search_and_create_concept_set(
            search_term="nothing",
            name="Empty",
            concept_set_id=1,
            athena_client=mock_client
        )
        
        self.assertEqual(len(cs.expression.items), 0)

    def test_clear_cache(self):
        # Create some files
        save_concept_set_to_cache(
            ConceptSet(id=1, name="A", expression=ConceptSetExpression(items=[])),
            "key1", self.cache_dir, "v1"
        )
        save_concept_set_to_cache(
            ConceptSet(id=2, name="B", expression=ConceptSetExpression(items=[])),
            "key2", self.cache_dir, "v2"
        )
        
        # Clear specific version
        count = clear_cache(self.cache_dir, "v1")
        self.assertEqual(count, 1)
        self.assertTrue((self.cache_dir / "v2" / "key2.json").exists())
        self.assertFalse((self.cache_dir / "v1" / "key1.json").exists())
        
        # Clear all
        count = clear_cache(self.cache_dir)
        self.assertEqual(count, 1) # Only v2 left
        self.assertFalse((self.cache_dir / "v2" / "key2.json").exists())

if __name__ == '__main__':
    unittest.main()
