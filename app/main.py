from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, field_validator
from app.github import GitHubClient
import re


app = FastAPI(title="NebexAI Summarizer")

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
        raise HTTPException(status_code=500, detail=str(e))
    
    return PlainTextResponse(content=context)

@app.post("/summarize")
async def summarize(request: SummarizeRequest):
    """
    Dummy endpoint that echoes the request body.
    """
    return {
        "status": "echo",
        "received": request.github_url,
        "note": "This is a dummy endpoint for verification."
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

