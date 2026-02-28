from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, field_validator
from app.github import GitHubClient
from app.llm import LLMClient, SummaryResponse
import re


app = FastAPI(title="NebexAI Summarizer")

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Formats payload validation errors into a clean, unified structure."""
    errs = exc.errors()
    msg = errs[0]["msg"].replace("Value error, ", "") if errs else str(exc)
    return JSONResponse(
        status_code=422,
        content={"status": "error", "message": msg},
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Formats standard HTTP exceptions into the unified structure."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "message": str(exc.detail)},
    )

GITHUB_URL_PATTERN = re.compile(
    r"^https://github\.com/[a-zA-Z0-9\-_.]+/[a-zA-Z0-9\-_.]+/?$"
)

class SummarizeRequest(BaseModel):
    github_url: str

    @field_validator("github_url")
    @classmethod
    def validate_github_url(cls, v: str) -> str:
        if not GITHUB_URL_PATTERN.match(v):
            raise ValueError(
                "Invalid GitHub URL. Expected format: https://github.com/{owner}/{repo}"
            )
        return v.rstrip("/")

def _parse_github_url(url: str) -> tuple[str, str]:
    """Extract owner and repo from a validated GitHub URL."""
    parts = url.rstrip("/").split("/")
    return parts[-2], parts[-1]

@app.post("/buildcontext")
async def build_context(request: SummarizeRequest):
    """
    Debug endpoint: returns the raw repository context that would be sent to the LLM.
    """
    owner, repo = _parse_github_url(request.github_url)
    
    try:
        async with GitHubClient() as gh:
            context = await gh.get_repository_context(owner, repo)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GitHub error: {str(e)}")
    
    return PlainTextResponse(content=context)

@app.post("/summarize", response_model=SummaryResponse)
async def summarize(request: SummarizeRequest):
    """
    Fetches the GitHub repository context and summarizes it using an LLM.
    """
    owner, repo = _parse_github_url(request.github_url)
    
    try:
        # Step 1: Fetch and filter repository context
        async with GitHubClient() as gh:
            context = await gh.get_repository_context(owner, repo)
            
        # Step 2: Generate summary using the LLM client
        llm = LLMClient()
        summary_response = await llm.generate_summary(context)
        
        return summary_response
        
    except Exception as e:
        # Log error in console and return 500
        print(f"Error summarising repo {owner}/{repo}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

