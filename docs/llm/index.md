# LLM wrapper

h4ckath0n provides a small wrapper around the OpenAI Python SDK for simple chat calls.

## Usage

```python
from h4ckath0n.llm import llm

client = llm()
response = client.chat(user="Summarize this in one sentence: ...")
print(response.text)
```

## Configuration

The wrapper reads API keys from either environment variable:

- `OPENAI_API_KEY`
- `H4CKATH0N_OPENAI_API_KEY`

You can also pass `api_key` directly to `llm()` or `LLMClient`.

## Defaults

- Model: `gpt-4o-mini`
- Timeout: 30 seconds
- Max retries: 2

## Response model

`chat()` returns a `ChatResponse` with:

- `text`
- `model`
- `usage_prompt_tokens`
- `usage_completion_tokens`

## Not implemented

- Streaming responses
- Tool calling helpers
- Built in prompt redaction
