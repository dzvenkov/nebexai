# AI Performance Engineering 2026 — Execution Plan

This execution plan outlines the steps and architecture required to build the repository summarization API service for the Nebius Academy admission assignment.

## Proposed Changes

### 1. Project Setup
- **Framework**: Use **FastAPI** for its modern asynchronous capabilities, auto-generated OpenAPI documentation, and high performance.
- **Dependency Management**: Standard `requirements.txt`.
  - `fastapi`, `uvicorn` (server), `httpx` (for async repository fetching), `openai` (for LLM interactions with standard APIs).

### 2. GitHub Repository Fetching & Processing
- **Fetching**: Use the GitHub REST API (`GET /repos/{owner}/{repo}/git/trees/{sha}?recursive=1`) to get the file tree without downloading binary blobs.
- **Filtering Criteria**:
  - Exclude common ignore directories: `.git`, `node_modules`, `venv`, `__pycache__`, `dist`, `build`, etc.
  - Exclude binary files and large assets: `.png`, `.jpg`, `.pdf`, `.mp4`, `.zip`, etc.
  - Exclude lock files: `package-lock.json`, `poetry.lock`, etc.
- **Context Window Management**:
  - Send the hierarchical directory tree representation.
  - Send the raw content of critical files: `README.md`, `pyproject.toml`, `package.json`, and main entry points (e.g., `main.py`, `app.py`).
  - Read specific source code files limiting to a maximum token count (~16k - 32k tokens depending on the chosen model) to avoid LLM context exhaustion.
  
### 3. LLM Integration
- **Provider**: Nebius Token Factory (OpenAI-compatible endpoints) or alternative.
- **Prompt Engineering**: Instruct the LLM to output pure JSON matching the required schema:
  - `summary`: A markdown human-readable summary.
  - `technologies`: A JSON array of string technology names.
  - `structure`: A markdown string describing layout.
- Use Structured Outputs or JSON mode if available, or ask it to respond with JSON block and parse it.

### 4. API Endpoints

#### `POST /buildcontext` (Debug)
- Accepts `{"github_url": "..."}` and returns the raw XML-tagged repository context as plain text.
- Useful for inspecting and iterating on the context payload before sending it to the LLM.

#### `POST /summarize`
- Fast validation using Pydantic model for request: `{"github_url": "..."}`
- Asynchronous execution flow: 
  1. Parse URL to get owner and repo name.
  2. Fetch tree and filter paths.
  3. Fetch contents of selected paths.
  4. Construct complex prompt.
  5. Call LLM API (timeout protected).
  6. Return parsed response.
- Error handling: Ensure errors return `{"status": "error", "message": "..."}` with appropriate HTTP codes.

### 5. Documentation (README.md)
- Step-by-step installation instructions using Python venv and `uvicorn`.
- Explanation for model selection (e.g., Llama-3 or Mistral through Nebius for optimal speed-to-quality ratio).
- Detailed elaboration of the repository content filtering and truncation approach to avoid maximum token limit errors.

## Verification Plan

### Automated/Manual Tests
- **Test 1**: Local deployment and testing against small target, e.g., `https://github.com/psf/requests`.
- **Test 2**: Request format validation (missing fields, invalid URLs).
- **Test 3**: Error handling validation (invalid GitHub repos, rate limiting).
- **Test 4**: Context limit test using a massive repository (e.g., React or Vue) to ensure truncation logic bounds the context window reliably.
