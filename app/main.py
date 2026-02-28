from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


app = FastAPI(title="NebexAI Summarizer")

class SummarizeRequest(BaseModel):
    github_url: str

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
