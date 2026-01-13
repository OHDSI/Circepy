"""
Athena-Client integration for Circe concept sets.

This module provides seamless integration between athena-client and Circe's
ConceptSet format, with vocabulary-versioned caching for performance and
reproducibility.

Key Features:
- Convert athena-client concept sets to Circe format
- Vocabulary version tracking for cache organization
- Automatic cache management when vocabulary updates
- LLM-friendly helper functions for chatbot workflows
"""

import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from athena_client import Athena
from ..vocabulary.concept import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem

logger = logging.getLogger(__name__)

# Default cache location
DEFAULT_CACHE_DIR = Path.home() / ".circe" / "concept_cache"

# Cache for vocabulary version (avoid repeated API calls)
_VOCABULARY_VERSION_CACHE: Optional[str] = None


def get_vocabulary_version(athena_client: Optional[Athena] = None) -> str:
    """
    Get current OMOP vocabulary version from athena-client.
    
    Args:
        athena_client: Optional Athena client instance. If None, creates new one.
        
    Returns:
        Vocabulary version string (e.g., "v5.0_20-MAY-23")
        
    Note:
        Result is cached in memory to avoid repeated API calls.
    """
    global _VOCABULARY_VERSION_CACHE
    
    if _VOCABULARY_VERSION_CACHE:
        return _VOCABULARY_VERSION_CACHE
    
    try:
        client = athena_client or Athena()
        
        # Query for a known concept to get vocabulary metadata
        # Using concept_id 0 (No matching concept) which always exists
        result = client.details(0)
        
        # Extract vocabulary version from result
        # The athena-client returns vocabulary version in the response
        if hasattr(result, 'vocabulary_version'):
            version = result.vocabulary_version
        else:
            # Fallback: use current date if version not available
            version = f"v5.0_{datetime.now().strftime('%d-%b-%y').upper()}"
            logger.warning(f"Could not detect vocabulary version, using: {version}")
        
        _VOCABULARY_VERSION_CACHE = version
        return version
        
    except Exception as e:
        # Fallback to date-based version if API fails
        version = f"v5.0_{datetime.now().strftime('%d-%b-%y').upper()}"
        logger.warning(f"Failed to get vocabulary version: {e}. Using: {version}")
        _VOCABULARY_VERSION_CACHE = version
        return version


def _get_cache_path(
    cache_key: str,
    cache_dir: Optional[Path] = None,
    vocabulary_version: Optional[str] = None
) -> Path:
    """
    Get the full cache file path for a given cache key.
    
    Args:
        cache_key: Cache key (typically search term + options)
        cache_dir: Base cache directory (default: ~/.circe/concept_cache)
        vocabulary_version: Vocabulary version (auto-detected if None)
        
    Returns:
        Full path to cache file
    """
    base_dir = cache_dir or DEFAULT_CACHE_DIR
    vocab_version = vocabulary_version or get_vocabulary_version()
    
    # Create vocabulary-versioned subdirectory
    version_dir = base_dir / vocab_version
    version_dir.mkdir(parents=True, exist_ok=True)
    
    # Sanitize cache key for filename
    safe_key = cache_key.replace(" ", "_").replace("/", "_")
    return version_dir / f"{safe_key}.json"


def load_cached_concept_set(
    cache_key: str,
    cache_dir: Optional[Path] = None,
    vocabulary_version: Optional[str] = None
) -> Optional[ConceptSet]:
    """
    Load concept set from vocabulary-versioned cache.
    
    Args:
        cache_key: Cache key to load
        cache_dir: Base cache directory (default: ~/.circe/concept_cache)
        vocabulary_version: Vocabulary version (auto-detected if None)
        
    Returns:
        ConceptSet if found in cache, None otherwise
    """
    cache_path = _get_cache_path(cache_key, cache_dir, vocabulary_version)
    
    if not cache_path.exists():
        logger.debug(f"Cache miss: {cache_path}")
        return None
    
    try:
        with open(cache_path, 'r') as f:
            data = json.load(f)
        
        # Validate vocabulary version matches
        cached_version = data.get('metadata', {}).get('vocabulary_version')
        current_version = vocabulary_version or get_vocabulary_version()
        
        if cached_version and cached_version != current_version:
            logger.warning(
                f"Cache vocabulary version mismatch: "
                f"cached={cached_version}, current={current_version}"
            )
            return None
        
        # Load ConceptSet from cached data
        concept_set = ConceptSet.model_validate(data['concept_set'])
        logger.info(f"Cache hit: {cache_path}")
        return concept_set
        
    except Exception as e:
        logger.error(f"Failed to load from cache: {e}")
        return None


def save_concept_set_to_cache(
    concept_set: ConceptSet,
    cache_key: str,
    cache_dir: Optional[Path] = None,
    vocabulary_version: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Save concept set to vocabulary-versioned cache.
    
    Args:
        concept_set: ConceptSet to cache
        cache_key: Cache key
        cache_dir: Base cache directory (default: ~/.circe/concept_cache)
        vocabulary_version: Vocabulary version (auto-detected if None)
        metadata: Additional metadata to store with cache
    """
    cache_path = _get_cache_path(cache_key, cache_dir, vocabulary_version)
    
    try:
        # Prepare cache data with metadata
        cache_data = {
            'metadata': {
                'vocabulary_version': vocabulary_version or get_vocabulary_version(),
                'cached_at': datetime.now().isoformat(),
                'cache_key': cache_key,
                **(metadata or {})
            },
            'concept_set': concept_set.model_dump(by_alias=True)
        }
        
        # Write to cache
        with open(cache_path, 'w') as f:
            json.dump(cache_data, f, indent=2)
        
        logger.info(f"Saved to cache: {cache_path}")
        
    except Exception as e:
        logger.error(f"Failed to save to cache: {e}")


def from_athena_concept_set(
    concept_ids: List[int],
    name: str,
    concept_set_id: int,
    include_descendants: bool = True,
    include_mapped: bool = False,
    cache_dir: Optional[Path] = None,
    vocabulary_version: Optional[str] = None,
    athena_client: Optional[Athena] = None
) -> ConceptSet:
    """
    Convert athena-client concept IDs to Circe ConceptSet.
    
    Args:
        concept_ids: List of OMOP concept IDs
        name: Name for the concept set
        concept_set_id: ID for the concept set (used in cohort definitions)
        include_descendants: Include descendant concepts
        include_mapped: Include mapped concepts
        cache_dir: Base cache directory
        vocabulary_version: Vocabulary version (auto-detected if None)
        athena_client: Optional Athena client instance
        
    Returns:
        ConceptSet in Circe format
    """
    client = athena_client or Athena()
    
    # Build cache key
    cache_key = f"ids_{'_'.join(map(str, sorted(concept_ids)))}_{include_descendants}_{include_mapped}"
    
    # Try to load from cache
    cached = load_cached_concept_set(cache_key, cache_dir, vocabulary_version)
    if cached:
        # Update name and ID to match request
        cached.name = name
        cached.id = concept_set_id
        return cached
    
    # Fetch concept details from athena-client
    items = []
    for concept_id in concept_ids:
        try:
            details = client.details(concept_id)
            
            # Convert to Circe Concept format
            concept = Concept(
                concept_id=details.concept_id,
                concept_name=details.concept_name,
                concept_code=details.concept_code,
                concept_class_id=details.concept_class_id,
                standard_concept=details.standard_concept,
                invalid_reason=details.invalid_reason,
                domain_id=details.domain_id,
                vocabulary_id=details.vocabulary_id
            )
            
            # Create ConceptSetItem
            item = ConceptSetItem(
                concept=concept,
                is_excluded=False,
                include_descendants=include_descendants,
                include_mapped=include_mapped
            )
            items.append(item)
            
        except Exception as e:
            logger.error(f"Failed to fetch concept {concept_id}: {e}")
            continue
    
    # Build ConceptSetExpression
    expression = ConceptSetExpression(items=items)
    
    # Create ConceptSet
    concept_set = ConceptSet(
        id=concept_set_id,
        name=name,
        expression=expression
    )
    
    # Save to cache
    save_concept_set_to_cache(
        concept_set,
        cache_key,
        cache_dir,
        vocabulary_version,
        metadata={
            'concept_ids': concept_ids,
            'include_descendants': include_descendants,
            'include_mapped': include_mapped
        }
    )
    
    return concept_set


def search_and_create_concept_set(
    search_term: str,
    name: str,
    concept_set_id: int,
    limit: int = 10,
    include_descendants: bool = True,
    include_mapped: bool = False,
    cache_dir: Optional[Path] = None,
    vocabulary_version: Optional[str] = None,
    athena_client: Optional[Athena] = None
) -> ConceptSet:
    """
    Search athena and create Circe ConceptSet in one step.
    
    This is the primary function for LLM/chatbot workflows.
    
    Args:
        search_term: Search query for athena
        name: Name for the concept set
        concept_set_id: ID for the concept set
        limit: Maximum number of search results to include
        include_descendants: Include descendant concepts
        include_mapped: Include mapped concepts
        cache_dir: Base cache directory
        vocabulary_version: Vocabulary version (auto-detected if None)
        athena_client: Optional Athena client instance
        
    Returns:
        ConceptSet in Circe format
        
    Example:
        >>> diabetes = search_and_create_concept_set(
        ...     search_term="type 2 diabetes mellitus",
        ...     name="Type 2 Diabetes",
        ...     concept_set_id=1
        ... )
    """
    client = athena_client or Athena()
    
    # Build cache key
    cache_key = f"{search_term}_{limit}_{include_descendants}_{include_mapped}"
    
    # Try to load from cache
    cached = load_cached_concept_set(cache_key, cache_dir, vocabulary_version)
    if cached:
        # Update name and ID to match request
        cached.name = name
        cached.id = concept_set_id
        return cached
    
    # Search athena
    try:
        search_results = client.search(search_term, limit=limit)
        concept_ids = [result.concept_id for result in search_results]
        
        if not concept_ids:
            logger.warning(f"No concepts found for search term: {search_term}")
            # Return empty concept set
            return ConceptSet(
                id=concept_set_id,
                name=name,
                expression=ConceptSetExpression(items=[])
            )
        
        # Use from_athena_concept_set to build the concept set
        concept_set = from_athena_concept_set(
            concept_ids=concept_ids,
            name=name,
            concept_set_id=concept_set_id,
            include_descendants=include_descendants,
            include_mapped=include_mapped,
            cache_dir=cache_dir,
            vocabulary_version=vocabulary_version,
            athena_client=client
        )
        
        # Save with search-specific cache key
        save_concept_set_to_cache(
            concept_set,
            cache_key,
            cache_dir,
            vocabulary_version,
            metadata={
                'search_term': search_term,
                'limit': limit,
                'concept_count': len(concept_ids)
            }
        )
        
        return concept_set
        
    except Exception as e:
        logger.error(f"Failed to search and create concept set: {e}")
        raise


def clear_cache(
    cache_dir: Optional[Path] = None,
    vocabulary_version: Optional[str] = None
) -> int:
    """
    Clear cached concept sets.
    
    Args:
        cache_dir: Base cache directory (default: ~/.circe/concept_cache)
        vocabulary_version: Specific vocabulary version to clear (all if None)
        
    Returns:
        Number of files deleted
    """
    base_dir = cache_dir or DEFAULT_CACHE_DIR
    
    if vocabulary_version:
        # Clear specific version
        version_dir = base_dir / vocabulary_version
        if not version_dir.exists():
            return 0
        
        count = sum(1 for _ in version_dir.glob("*.json"))
        for file in version_dir.glob("*.json"):
            file.unlink()
        
        logger.info(f"Cleared {count} cached files for version {vocabulary_version}")
        return count
    else:
        # Clear all versions
        count = 0
        for version_dir in base_dir.iterdir():
            if version_dir.is_dir():
                for file in version_dir.glob("*.json"):
                    file.unlink()
                    count += 1
        
        logger.info(f"Cleared {count} total cached files")
        return count
