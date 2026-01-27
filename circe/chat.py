"""
Chat module for interacting with LLMs to generate cohort definitions.
"""
import sys
import os
import json
import re
from pathlib import Path
from typing import Optional, List, Dict, Any

from circe.prompt_builder import CohortPromptBuilder, ConceptSet

def chat_command(args):
    """
    Entry point for the chat command.
    """
    start_chat(
        model=args.model,
        prompt_type=args.prompt_type,
        output=args.output,
        concept_sets_file=args.concept_sets,
        input_file=args.input_file
    )
    return 0

def start_chat(
    model: Optional[str],
    prompt_type: str,
    output: Optional[str],
    concept_sets_file: Optional[str],
    input_file: Optional[str] = None
):
    """
    Start the interactive chat session.
    """
    # Check dependencies
    try:
        import litellm
        from dotenv import load_dotenv
    except ImportError:
        print("Error: 'litellm' and 'python-dotenv' are required for chat functionality.", file=sys.stderr)
        print("Please install them with: pip install litellm python-dotenv", file=sys.stderr)
        return 1

    # Load environment variables
    load_dotenv()
    
    # Determine model
    if not model:
        model = os.getenv("LLM_MODEL", "gpt-4o")
        # Handle optional temperature if needed, but litellm handles it or we pass it
        
    print(f"🚀 Starting Circe Chat")
    print(f"   Model: {model}")
    print(f"   Prompt: {prompt_type}")
    print("-" * 50)
    
    # Load concept sets if provided
    concept_sets_data = []
    if concept_sets_file:
        try:
            with open(concept_sets_file, 'r') as f:
                raw_data = json.load(f)
                # Expecting list of dicts with id, name
                for item in raw_data:
                    concept_sets_data.append(ConceptSet(
                        id=item.get('id'),
                        name=item.get('name'),
                        description=item.get('description')
                    ))
            print(f"   Loaded {len(concept_sets_data)} concept sets from {concept_sets_file}")
        except Exception as e:
            print(f"Error loading concept sets: {e}", file=sys.stderr)
            return 1
            
    # Initialize builder
    builder = CohortPromptBuilder()
    
    try:
        system_prompt = builder.load_system_prompt(prompt_type)
    except Exception as e:
        print(f"Error loading system prompt: {e}", file=sys.stderr)
        return 1

    # Add inference instruction if no concept sets provided
    if not concept_sets_data:
        system_prompt += "\n\nIMPORTANT: No concept sets were provided.\n" \
                         "You MUST infer appropriate concept sets from the clinical description.\n" \
                         "1. Define them using `circe.vocabulary.concept_set`.\n" \
                         "2. Add them to the builder using `.with_concept_sets(...)`.\n" \
                         "3. Use valid OMOP Concept IDs (or realistic placeholders if exact IDs are unknown)."
    
    messages = [{"role": "system", "content": system_prompt}]
    
    print("\nPlease describe the cohort you want to build (or type 'quit' to exit):")
    
    first_turn = True
    initial_input = None
    
    if input_file:
        try:
            initial_input = Path(input_file).read_text()
            print(f"   Loaded clinical description from {input_file}")
        except Exception as e:
            print(f"Error reading input file: {e}", file=sys.stderr)
            return 1

    while True:
        try:
            if first_turn and initial_input:
                user_input = initial_input
                print(f"\n> [Processing input from file...]")
            else:
                user_input = input("\n> ")
        except (EOFError, KeyboardInterrupt):
            print("\nExiting chat.")
            break
            
        if user_input.lower() in ('quit', 'exit'):
            break
            
        if not user_input.strip():
            continue
        
        # Turn off first_turn flag after we have a valid input
        if first_turn:
            first_turn = False
            
        # Construct user message
        if len(messages) == 1:
            # First user message - format nicely
            formatted_content = f"\n---\n## User Task\n**Clinical Description:**\n{user_input}\n"
            if concept_sets_data:
                formatted_content += builder.format_concept_sets(concept_sets_data)
            else:
                formatted_content += "\nNo pre-defined concept sets provided. Please infer them."
            
            messages.append({"role": "user", "content": formatted_content})
        else:
            messages.append({"role": "user", "content": user_input})

        # Call AI
        print("Thinking...")
        try:
            response = litellm.completion(model=model, messages=messages)
            content = response.choices[0].message.content
            print("\n" + content)
            
            messages.append({"role": "assistant", "content": content})
            
            # Extract and process code
            _process_response_content(content, output)

        except Exception as e:
            print(f"\nError during API call: {e}", file=sys.stderr)


def _process_response_content(content: str, output_base: Optional[str]):
    """
    Extract logic to find Python code, save it, and attempt to run it to generate JSON.
    """
    # Look for python code block
    code_match = re.search(r'```python\n(.*?)\n```', content, re.DOTALL)
    if not code_match:
        return

    code = code_match.group(1)
    
    # Determine output filenames
    if output_base:
        py_file = Path(output_base + ".py")
        json_file = Path(output_base + ".json")
    else:
        # Default name
        py_file = Path("cohort_definition.py")
        json_file = Path("cohort_definition.json")
        
    # Save Python code
    try:
        py_file.write_text(code)
        print(f"\n✅ Saved Python code to {py_file}")
    except Exception as e:
        print(f"Error saving Python file: {e}")
        return

    # Attempt to execute and save JSON
    # This involves running the code and capturing the 'cohort' variable or 'expression' variable
    print("   Attempting to generate JSON...")
    
    try:
        # Create a local scope
        local_scope = {}
        # We need to make sure the CWD is in path so imports work?
        # Assuming we are running from project root or installed package
        
        exec(code, {}, local_scope)
        
        # Look for a CohortExpression or CohortBuilder object
        # The prompt usually produces: 
        # cohort = CohortBuilder(...).build()
        # So we look for 'cohort'
        
        cohort_obj = local_scope.get('cohort')
        if not cohort_obj:
            # Try to find any variable that is a tuple (builder) or CohortExpression
            for k, v in local_scope.items():
                if hasattr(v, 'to_json'): # CohortExpression has to_json? Check API.
                    cohort_obj = v
                    break
        
        if cohort_obj:
            # If it's the builder (tuple in some cases?), checks if it has build()
            # But the prompt says `.build()` returns CohortExpression.
            
            # Check if it has 'to_json' or similar. 
            # circe.cohortdefinition.CohortExpression uses Pydantic? 
            # It inherits from Serializable?
            
            json_output = None
            if hasattr(cohort_obj, 'json'): # Pydantic v1/v2
                json_output = cohort_obj.model_dump_json(indent=2) if hasattr(cohort_obj, 'model_dump_json') else cohort_obj.json(indent=2)
            elif hasattr(cohort_obj, 'to_json'):
                json_output = cohort_obj.to_json()
            else:
                 # It might be a dict?
                 if isinstance(cohort_obj, dict):
                     json_output = json.dumps(cohort_obj, indent=2)

            if json_output:
                json_file.write_text(json_output)
                print(f"✅ Saved Cohort JSON to {json_file}")
            else:
                print("   Could not serialize 'cohort' object to JSON.")
        else:
            print("   Could not find 'cohort' variable in executed code.")
            
    except Exception as e:
        print(f"   Error executing generated code: {e}")
        print("   (Ensure the generated code is valid and all dependencies are installed)")
