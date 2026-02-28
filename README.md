# NebexAI Summarizer

A fast, asynchronous API service that takes a GitHub repository URL and returns a comprehensive, LLM-generated summary, including the project's purpose, technology stack, and architectural structure.

It is built as the submission for the **AI Performance Engineering 2026** assignment.

---

## 1. Setup and Run Instructions

Assuming a clean machine with Python 3.10+ installed:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/dzvenkov/nebexai.git
   cd nebexai
   ```

2. **Create and activate a virtual environment**:
   ```bash
   # Windows
   python -m venv .venv
   .\.venv\Scripts\activate

   # Linux/macOS
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**:
   Create a `.env` file in the root directory (or export directly) with your Nebius Token Factory API key:
   ```bash
   NEBIUS_API_KEY=your_api_key_here
   ```

5. **Run the Server**:
   Start the FastAPI server via Uvicorn:
   ```bash
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

6. **Test the API**:
   Send a POST request to the `/summarize` endpoint:
   ```bash
   curl -X POST http://127.0.0.1:8000/summarize \
        -H "Content-Type: application/json" \
        -d '{"github_url": "https://github.com/psf/requests"}'
   ```

---

## 2. Model Selection

I chose `meta-llama/Llama-3.3-70B-Instruct-fast` via the Nebius Token Factory API. This model offers an exceptional balance between rapid inference speed and high-quality instruction following, which is critical for reliably outputting standard JSON without markdown bloat across complex repository contexts.

---

## 3. Repository Handling Approach

To handle large repositories within LLM context limits (and optimize processing time), I implemented a **Composite Strategy Pattern** (`app/filters.py`) that pipes the repository layout through three sequential filters:

1. **Deny-list Filtering (`BaseFileFilterStrategy`)**: First, I aggressively strip out noise. This ignores common folders (`.git`, `node_modules`, `venv`, `__pycache__`, `dist`) and drops binary/asset extensions (`.png`, `.pdf`, `.mp4`, `.zip`, `.lock`, etc.).
2. **Individual Size Limit (`IndividualFileSizeFilterStrategy`)**: I drop any single file exceeding 50KB. This prevents one massive generated source file or mapping from instantaneously exhausting the context budget.
3. **Priority Context & Budgeting (`SizeLimiterFileFilterStrategy`)**:
   - **Priority Match**: I prioritize files that provide disproportionate context about the project's purpose and architecture. This immediately captures core documentation (`README`, `*.md`), community standards (`CONTRIBUTING.md`), CI/CD and deployment manifests (`dockerfile`, `kubernetes`, `.gitlab-ci`, `terraform`), and dependency trees (`package.json`, `pyproject.toml`, `requirements.txt`).
   - **Layered Sampling**: For the remaining source code files, I group them by directory and sample one file per folder layer-by-layer (starting closest to the root). I accumulate these until a hard context limit of 90KB is reached. If a file puts the payload slightly over the limit, it is seamlessly truncated.

This ensures the LLM receives maximum structural, instructional, and architectural context upfront, avoiding token exhaustion while still exposing a representative sample of the application code.

---

## Project Structure
- `app/main.py`: Main FastAPI application and endpoints.
- `app/github.py`: Async GitHub API interactions (tree fetching, content harvesting).
- `app/filters.py`: Pluggable Composite filter strategies.
- `app/llm.py`: Async OpenAI client handling prompt injection and schema parsing.
- `test_summarize.ps1`: Helper script to automatically start the server, generate a summary, and print the resulting JSON visually.
