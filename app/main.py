from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator
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
