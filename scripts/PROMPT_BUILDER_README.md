# Prompt Builder for Cohort Generation

Generate complete prompts for LLM-based cohort definition generation.

## Quick Start

```python
from scripts.prompt_builder import create_prompt

# Define your concept sets
concept_sets = [
    {"id": 1, "name": "Type 2 Diabetes", "description": "Standard T2DM codes"},
    {"id": 2, "name": "Metformin"},
    {"id": 3, "name": "Insulin"}
]

# Create a prompt
prompt = create_prompt(
    clinical_description="Adults aged 18-65 with new T2DM, prior Metformin, no Insulin",
    concept_sets=concept_sets,
    model_type="standard"  # or "reasoning" or "fast"
)

# Use the prompt with your LLM
print(prompt)
```

## API Reference

### `create_prompt()`

Convenience function to create a complete prompt.

**Parameters:**
- `clinical_description` (str): Clinical description of the cohort
- `concept_sets` (List[Dict]): List of concept sets with `id`, `name`, and optional `description`
- `model_type` (str): `"reasoning"`, `"standard"`, or `"fast"`
- `additional_notes` (str, optional): Extra instructions or constraints

**Returns:** Complete prompt string ready for LLM

### `CohortPromptBuilder`

Class-based interface with more control.

```python
from scripts.prompt_builder import CohortPromptBuilder, ConceptSet

builder = CohortPromptBuilder()

# Using ConceptSet objects
concept_sets = [
    ConceptSet(1, "Type 2 Diabetes", "Standard OMOP codes for T2DM"),
    ConceptSet(2, "Metformin", "All metformin formulations")
]

prompt = builder.build_prompt(
    clinical_description="Your clinical description here",
    concept_sets=concept_sets,
    model_type="standard",
    additional_notes="Optional extra guidance"
)

# Save to file
builder.save_prompt(prompt, "my_cohort_prompt.txt", model_type="standard")
```

## Model Types

### `reasoning` - For Reasoning Models
- **Models**: OpenAI o1/o3-mini, Claude 3.5 Sonnet (thinking), Gemini 2.0 Flash Thinking
- **Characteristics**: Concise, minimal examples, trusts model reasoning
- **Prompt size**: ~1,200 tokens

### `standard` - For Standard Models  
- **Models**: GPT-4o, Claude 3.5 Sonnet, Gemini 2.0 Flash
- **Characteristics**: Balanced detail, strategic guidance, 4 examples
- **Prompt size**: ~1,600 tokens

### `fast` - For Fast/Smaller Models
- **Models**: GPT-4o-mini, Claude 3.5 Haiku, Gemini 1.5 Flash
- **Characteristics**: Step-by-step instructions, 7 examples, heavy emphasis on rules
- **Prompt size**: ~2,200 tokens

## Examples

### Simple Cohort

```python
prompt = create_prompt(
    clinical_description="Patients aged 18+ with diabetes",
    concept_sets=[{"id": 1, "name": "Diabetes Mellitus"}],
    model_type="fast"
)
```

### Complex Cohort with Multiple Criteria

```python
concept_sets = [
    {"id": 1, "name": "Acute MI", "description": "AMI diagnosis codes"},
    {"id": 2, "name": "Aspirin", "description": "Antiplatelet therapy"},
    {"id": 3, "name": "Statin", "description": "Lipid-lowering therapy"},
    {"id": 4, "name": "CKD", "description": "Chronic kidney disease"}
]

clinical_desc = """
Patients aged 18+ with first acute myocardial infarction who:
- Are prescribed aspirin within 7 days
- Are prescribed a statin within 30 days  
- Have no history of chronic kidney disease
"""

prompt = create_prompt(
    clinical_description=clinical_desc,
    concept_sets=concept_sets,
    model_type="standard",
    additional_notes="Focus on guideline-concordant post-MI care"
)
```

## CLI Usage

```bash
# Basic usage
python scripts/prompt_builder.py standard \
  "Adults with diabetes" \
  '[{"id": 1, "name": "Diabetes"}]'

# Complex cohort
python scripts/prompt_builder.py fast \
  "Patients with AMI requiring aspirin" \
  '[{"id": 1, "name": "Acute MI"}, {"id": 2, "name": "Aspirin"}]'
```

## Output Format

The generated prompt includes:

1. **System Prompt**: Model-specific instructions from `prompts/{model_type}_models_prompt.md`
2. **API Reference**: Auto-generated SKILL.md with all available methods
3. **Critical Warnings**: Common API pitfalls to avoid
4. **Examples**: 1-7 validated examples depending on model type
5. **User Task**: Your clinical description + concept sets

## Token Counts

| Model Type | Typical Size | Max Recommended |
|-----------|--------------|-----------------|
| Reasoning | ~1,200 tokens | 10,000 tokens |
| Standard  | ~1,600 tokens | 8,000 tokens |
| Fast      | ~2,200 tokens | 5,000 tokens |

Your prompts are well within safe limits for all models!

## Integration with LLM APIs

### OpenAI

```python
import openai

prompt = create_prompt(...)

response = openai.ChatCompletion.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": prompt},
        {"role": "user", "content": "Please generate the cohort definition"}
    ]
)
```

### Anthropic Claude

```python
import anthropic

prompt = create_prompt(..., model_type="standard")

client = anthropic.Anthropic()
message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=4096,
    messages=[{"role": "user", "content": prompt}]
)
```

### Google Gemini

```python
import google.generativeai as genai

prompt = create_prompt(..., model_type="fast")

model = genai.GenerativeModel('gemini-2.0-flash')
response = model.generate_content(prompt)
```

## Updating Prompts

All prompts are auto-generated from the codebase:

```bash
# Regenerate all prompts and SKILL.md
python scripts/generate_skill.py
```

This ensures prompts always reflect the current API!
