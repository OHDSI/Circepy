# System Prompts for Cohort Builder

This directory contains multiple variants of the OHDSI Cohort Builder system prompt, each tailored to different AI model capabilities.

## Prompt Variants

### 1. Reasoning Models (`reasoning_models_prompt.md`)
**For**: OpenAI o1/o3-mini, Claude 3.5 Sonnet (with extended thinking), Gemini 2.0 Flash Thinking

**Characteristics**:
- **Concise and direct** - reasoning models don't need verbose instructions
- **Minimal examples** - these models can infer patterns
- **Focus on constraints** - emphasizes what NOT to do (no hallucinations)
- **Trust the model** - assumes strong logical reasoning capabilities

**When to use**: For models with built-in reasoning/thinking capabilities that can handle complex logical tasks with minimal guidance.

---

### 2. Standard Models (`standard_models_prompt.md`)
**For**: GPT-4o, Claude 3.5 Sonnet (standard), Gemini 2.0 Flash

**Characteristics**:
- **Balanced detail** - provides context and examples
- **Strategic instructions** - guides the analytical process
- **Guardrails and warnings** - explicit "do not invent methods" rules
- **Example patterns** - includes template responses

**When to use**: For high-capability general-purpose models that benefit from structured guidance and examples.

---

### 3. Fast Models (`fast_models_prompt.md`)
**For**: GPT-4o-mini, Claude 3.5 Haiku, Gemini 1.5 Flash

**Characteristics**:
- **Step-by-step instructions** - explicit numbered steps
- **Multiple examples** - shows 5+ common patterns
- **Heavy emphasis on rules** - repeats critical constraints
- **Simple language** - avoids complex terminology
- **Visual formatting** - uses ✅/❌ for clarity

**When to use**: For smaller/faster models that need clear, direct instructions with lots of examples.

---

## Auto-Generation

All prompts are **auto-generated** from the codebase via `scripts/generate_skill.py`. The SKILL.MD content section is identical across all variants - only the surrounding instructions differ.

### To Update All Prompts:

```bash
python3 scripts/generate_skill.py
```

This will:
1. Generate fresh `SKILL.md` from the codebase
2. Update all three prompt variants with the new API reference
3. Preserve the model-specific instruction text

### Pre-Commit Hook

A git pre-commit hook automatically runs the generator when builder files change, ensuring prompts stay in sync with the API.

---

## Choosing the Right Prompt

| Model                          | Recommended Prompt     | Why                                      |
|--------------------------------|------------------------|------------------------------------------|
| OpenAI o1, o3-mini             | Reasoning Models       | Native reasoning capabilities            |
| Claude 3.5 Sonnet (thinking)   | Reasoning Models       | Extended thinking mode                   |
| Gemini 2.0 Flash Thinking      | Reasoning Models       | Built-in thinking                        |
| GPT-4o                         | Standard Models        | High capability, benefits from examples  |
| Claude 3.5 Sonnet              | Standard Models        | High capability, structured guidance     |
| Gemini 2.0 Flash               | Standard Models        | Balanced performance                     |
| GPT-4o-mini                    | Fast Models            | Needs step-by-step guidance              |
| Claude 3.5 Haiku               | Fast Models            | Faster model, more examples helpful      |
| Gemini 1.5 Flash               | Fast Models            | Lighter model, clear instructions needed |

---

## Maintenance

- **DO NOT** manually edit the `[BEGIN SKILL.MD CONTENT]` ... `[END SKILL.MD CONTENT]` sections
- **DO** edit the surrounding instruction text to improve model-specific guidance
- **DO** run `python3 scripts/generate_skill.py` after editing builder classes
- **DO** test prompts with their target models to validate effectiveness

---

## Files

```
prompts/
├── README.md                      # This file
├── reasoning_models_prompt.md     # Concise prompt for reasoning models
├── standard_models_prompt.md      # Balanced prompt for GPT-4o/Claude/Gemini
└── fast_models_prompt.md          # Detailed prompt for smaller models
```

All prompts guarantee zero hallucinations because they're generated directly from the actual API implementation.
