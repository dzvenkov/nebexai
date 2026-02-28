import os
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

class SummaryResponse(BaseModel):
    summary: str
    technologies: List[str]
    structure: str

class LLMClient:
    """
    Client for interacting with the Nebius Token Factory (or compatible OpenAI endpoints).
    """
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.getenv("NEBIUS_API_KEY")
        if not self.api_key:
            raise ValueError("NEBIUS_API_KEY environment variable is not set.")
            
        self.base_url = base_url or os.getenv("NEBIUS_BASE_URL", "https://api.studio.nebius.ai/v1/")
        # Default model: Llama 3.3 70B (fast, excellent instruction following) or Mistral
        self.model = os.getenv("NEBIUS_MODEL", "meta-llama/Llama-3.3-70B-Instruct-fast")
        
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    async def generate_summary(self, repository_context: str) -> SummaryResponse:
        """
        Takes the XML-tagged repository context and uses the LLM to generate
        a structured summary, technology stack, and structure description.
        """
        system_prompt = (
            "You are an expert software architect and code analyst. Your job is to analyze "
            "the following repository context (which includes a directory structure and file contents) "
            "and provide a structured analysis.\n\n"
            "You MUST output raw JSON matching exactly the following schema. "
            "Do not include any markdown blocks (like ```json), just the raw JSON object.\n"
            "{\n"
            '  "summary": "A comprehensive markdown-formatted summary of what the repository does and how it works.",\n'
            '  "technologies": ["List", "of", "technologies", "frameworks", "languages", "used"],\n'
            '  "structure": "A markdown-formatted description of the repository layout and architecture."\n'
            "}"
        )

        user_prompt = (
            f"Please analyze the following GitHub repository:\n\n{repository_context}"
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # Low temperature for analytical consistency
                max_tokens=4000,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            if not content:
                raise ValueError("LLM returned an empty response.")
                
            # Parse the JSON response
            data = json.loads(content.strip())
            
            return SummaryResponse(
                summary=data.get("summary", "No summary provided."),
                technologies=data.get("technologies", []),
                structure=data.get("structure", "No structure provided.")
            )

        except Exception as e:
            raise Exception(f"Failed to generate summary via LLM: {str(e)}")
