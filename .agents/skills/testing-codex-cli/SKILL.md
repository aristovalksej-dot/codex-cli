---
name: testing-codex-cli
description: Test the Codex CLI agent end-to-end. Use when verifying CLI functionality, tool calling, API integration, or REPL behavior.
---

# Testing Codex CLI

## Prerequisites

1. Install the CLI in dev mode:
   ```bash
   cd /home/ubuntu/repos/codex-cli
   pip install -e .
   ```
2. Set the API key:
   ```bash
   export CODEX_API_KEY="$CODEX_SALE_API_KEY"
   ```

## Devin Secrets Needed

- `CODEX_SALE_API_KEY` — API key for codex.sale (user-scoped)

## Quick Smoke Tests

### 1. CLI entry points
```bash
codex --version        # Expect: codex-cli X.Y.Z
codex --help           # Expect: usage with --model, --api-key, --auto-approve, --setup
```

### 2. Config validation
```python
python3 -c "
from codex_cli.config import Config
c = Config.load()
print('API key loaded:', bool(c.api_key))
print('Model:', c.model)
print('Errors:', c.validate())
"
# Expect: API key loaded: True, Model: gpt-5.3-codex, Errors: []
```

### 3. Tool registry
```python
python3 -c "
from codex_cli.tools import create_registry
r = create_registry()
print(f'Tools: {len(r.list_tools())}')  # Expect: 19
print(f'Schemas: {len(r.to_openai_tools())}')  # Expect: 19
"
```

### 4. One-shot mode (no tools)
```bash
codex "Say hello in Russian"
# Expect: Rich panel with Russian greeting, exit code 0
```

### 5. One-shot mode with tool calling
```bash
codex --auto-approve "List files in /tmp using list_directory tool"
# Expect: Tool call panel → Result panel → Summary panel
```

### 6. Shell command tool
```bash
codex --auto-approve "Run 'echo TEST_OK' using run_command"
# Expect: run_command tool call, output TEST_OK
```

### 7. Error handling
```bash
CODEX_API_KEY= CODEX_SALE_API_KEY= codex "hello"
# Expect: Error about missing API key, exit code 1
```

## Individual Tool Testing

Tools can be tested directly via Python without API calls:

```python
import asyncio
from codex_cli.tools.file_ops import ReadFileTool
from codex_cli.tools.web import FetchWebpageTool

async def test():
    # File read
    r = await ReadFileTool().execute(path='/etc/hostname')
    print(r)
    # Web fetch
    w = await FetchWebpageTool().execute(url='https://example.com')
    print(w[:200])

asyncio.run(test())
```

## Notes

- The API at codex.sale supports OpenAI-style tool/function calling (`supports_parallel_tool_calls: true`)
- `gpt-5.4-mini` may not appear in the models list from the API but is in AVAILABLE_MODELS — test with other models if this one fails
- Web tools use httpx + BeautifulSoup (no JS rendering)
- `search_web` scrapes DuckDuckGo HTML — may break if DDG changes markup
- Use `--auto-approve` flag to skip confirmation prompts during testing
- Interactive REPL testing requires a real terminal (not easily scriptable); prefer one-shot mode for automated tests
