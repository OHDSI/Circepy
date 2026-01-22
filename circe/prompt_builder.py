"""
Prompt builder for generating cohort definitions using LLMs.

This module provides utilities to construct complete prompts for different AI models
by combining system prompts with clinical descriptions and concept sets.
"""

from pathlib import Path
from typing import List, Dict, Literal, Optional
from dataclasses import dataclass


ModelType = Literal["reasoning", "standard", "fast"]


@dataclass
class ConceptSet:
    """Represents a concept set with ID and name."""
    id: int
    name: str
    description: Optional[str] = None
    
    def __str__(self) -> str:
        """Format concept set for prompt."""
        if self.description:
            return f"- ID {self.id}: {self.name} ({self.description})"
        return f"- ID {self.id}: {self.name}"


class CohortPromptBuilder:
    """Builds complete prompts for cohort generation using different AI models."""
    
    PROMPT_FILES = {
        "reasoning": "prompts/reasoning_models_prompt.md",
        "standard": "prompts/standard_models_prompt.md",
        "fast": "prompts/fast_models_prompt.md"
    }
    
    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize the prompt builder.
        
        Args:
            project_root: Path to project root. If None, uses current file's parent.
        """
        if project_root is None:
            project_root = Path(__file__).parent.parent
        self.project_root = Path(project_root)
    
    def load_system_prompt(self, model_type: ModelType) -> str:
        """
        Load the system prompt for a given model type.
        
        Args:
            model_type: Type of model (reasoning/standard/fast)
            
        Returns:
            System prompt content
            
        Raises:
            FileNotFoundError: If prompt file doesn't exist
            ValueError: If model_type is invalid
        """
        if model_type not in self.PROMPT_FILES:
            raise ValueError(f"Invalid model_type: {model_type}. Must be 'reasoning', 'standard', or 'fast'")
        
        prompt_path = self.project_root / self.PROMPT_FILES[model_type]
        
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        
        with open(prompt_path, 'r') as f:
            return f.read()
    
    def format_concept_sets(self, concept_sets: List[ConceptSet]) -> str:
        """
        Format concept sets for inclusion in prompt.
        
        Args:
            concept_sets: List of concept sets
            
        Returns:
            Formatted concept sets string
        """
        if not concept_sets:
            return "No concept sets provided."
        
        lines = ["**Pre-defined Concept Sets:**"]
        for cs in concept_sets:
            lines.append(str(cs))
        
        return "\n".join(lines)
    
    def build_prompt(
        self,
        clinical_description: str,
        concept_sets: List[ConceptSet],
        model_type: ModelType = "standard",
        additional_notes: Optional[str] = None
    ) -> str:
        """
        Build complete prompt combining system prompt with user task.
        
        Args:
            clinical_description: Clinical description of the cohort
            concept_sets: List of available concept sets with IDs
            model_type: Type of model to target (reasoning/standard/fast)
            additional_notes: Optional additional instructions or constraints
            
        Returns:
            Complete prompt ready to send to the model
            
        Example:
            >>> builder = CohortPromptBuilder()
            >>> concept_sets = [
            ...     ConceptSet(1, "Type 2 Diabetes", "Standard OMOP codes"),
            ...     ConceptSet(2, "Metformin", "All metformin formulations"),
            ...     ConceptSet(3, "Insulin", "All insulin products")
            ... ]
            >>> prompt = builder.build_prompt(
            ...     clinical_description="Adults aged 18-65 with new T2DM diagnosis",
            ...     concept_sets=concept_sets,
            ...     model_type="standard"
            ... )
        """
        # Load system prompt
        system_prompt = self.load_system_prompt(model_type)
        
        # Format concept sets
        formatted_concepts = self.format_concept_sets(concept_sets)
        
        # Build user task section
        user_task = [
            "\n---\n",
            "## User Task\n",
            "**Clinical Description:**",
            clinical_description,
            "",
            formatted_concepts
        ]
        
        if additional_notes:
            user_task.extend([
                "",
                "**Additional Notes:**",
                additional_notes
            ])
        
        # Combine system prompt + user task
        complete_prompt = system_prompt + "\n".join(user_task)
        
        return complete_prompt
    
    def save_prompt(
        self,
        prompt: str,
        output_path: Path,
        model_type: Optional[ModelType] = None
    ) -> None:
        """
        Save a generated prompt to a file.
        
        Args:
            prompt: The complete prompt to save
            output_path: Where to save the prompt
            model_type: Optional model type to include in filename
        """
        output_path = Path(output_path)
        
        # Add model type suffix if provided
        if model_type:
            stem = output_path.stem
            suffix = output_path.suffix
            output_path = output_path.parent / f"{stem}_{model_type}{suffix}"
        
        with open(output_path, 'w') as f:
            f.write(prompt)
        
        print(f"✅ Saved prompt to: {output_path}")


def create_prompt(
    clinical_description: str,
    concept_sets: List[Dict[str, any]],
    model_type: ModelType = "standard",
    **kwargs
) -> str:
    """
    Convenience function to create a prompt.
    
    Args:
        clinical_description: Clinical description
        concept_sets: List of dicts with 'id', 'name', and optional 'description'
        model_type: Model type to target
        **kwargs: Additional arguments for build_prompt()
        
    Returns:
        Complete prompt string
        
    Example:
        >>> prompt = create_prompt(
        ...     "Adults with diabetes",
        ...     [{"id": 1, "name": "Type 2 Diabetes"}],
        ...     model_type="fast"
        ... )
    """
    builder = CohortPromptBuilder()
    
    # Convert dicts to ConceptSet objects
    cs_objects = [
        ConceptSet(
            id=cs['id'],
            name=cs['name'],
            description=cs.get('description')
        )
        for cs in concept_sets
    ]
    
    return builder.build_prompt(
        clinical_description=clinical_description,
        concept_sets=cs_objects,
        model_type=model_type,
        **kwargs
    )


# CLI interface
if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) < 4:
        print("Usage: python prompt_builder.py <model_type> <clinical_description> <concept_sets_json>")
        print("\nExample:")
        print('  python prompt_builder.py standard \\')
        print('    "Adults aged 18-65 with new T2DM diagnosis" \\')
        print('    \'[{"id": 1, "name": "Type 2 Diabetes"}, {"id": 2, "name": "Metformin"}]\'')
        sys.exit(1)
    
    model_type = sys.argv[1]
    clinical_desc = sys.argv[2]
    concept_sets_json = sys.argv[3]
    
    # Parse concept sets
    concept_sets_data = json.loads(concept_sets_json)
    
    # Build prompt
    prompt = create_prompt(
        clinical_description=clinical_desc,
        concept_sets=concept_sets_data,
        model_type=model_type
    )
    
    # Output
    print(prompt)
