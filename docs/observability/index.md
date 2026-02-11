# Observability

Observability is opt in and minimal today. The library ships helpers that can be wired into your
own tracing stack.

## What is implemented

- `init_observability(app)` adds an `X-Trace-Id` header to every response.
- `ObservabilitySettings.langsmith_tracing` can set the LangSmith environment variables.
- `redact_headers` and `redact_value` help remove sensitive values from traces.
- `traced_tool` and `traced_node` attach metadata to functions for external tracing frameworks.

No FastAPI, LangChain, or OpenAI instrumentation is configured automatically.

## Configuration

`ObservabilitySettings` reads environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `LANGSMITH_TRACING` | `false` | Enable LangSmith env wiring |
| `LANGSMITH_API_KEY` | empty | LangSmith API key |
| `LANGSMITH_PROJECT` | `default` | LangSmith project name |
| `OTEL_ENABLED` | `false` | Reserved for future OTEL support |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | empty | Reserved for future OTEL support |

## Example

```python
from h4ckath0n.obs import ObservabilitySettings, init_observability

settings = ObservabilitySettings(langsmith_tracing=True)
init_observability(app, settings)
```

## Roadmap

Advanced tracing and OpenTelemetry export are not wired yet. Track those changes in docs with a
clearly labeled Roadmap section if they are implemented.
