import httpx
import os
from typing import List, Dict, Any, Optional
from app.filters import FileFilterStrategy, DefaultFileFilterStrategy

class GitHubClient:
    def __init__(self, token: Optional[str] = None, file_filter: Optional[FileFilterStrategy] = None):
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "nebexai-summarizer"
        }
        if token:
            self.headers["Authorization"] = f"token {token}"
        self.file_filter = file_filter or DefaultFileFilterStrategy()

    async def get_repository_tree(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """Fetch the recursive file tree for the repository."""
        url = f"{self.base_url}/repos/{owner}/{repo}/git/trees/main?recursive=1"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            if response.status_code != 200:
                # Try master if main fails
                url = f"{self.base_url}/repos/{owner}/{repo}/git/trees/master?recursive=1"
                response = await client.get(url, headers=self.headers)
            
            if response.status_code != 200:
                raise Exception(f"Failed to fetch repository tree: {response.text}")
            
            tree_data = response.json()
            
        return tree_data.get("tree", [])

    def filter_paths(self, tree: List[Dict[str, Any]]) -> List[str]:
        """Filter paths to include only relevant code and metadata files."""
        return self.file_filter.filter_paths(tree)

    async def get_file_content(self, owner: str, repo: str, path: str) -> str:
        """Fetch raw content of a specific file."""
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/{path}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            if response.status_code != 200:
                # Try master
                url = f"https://raw.githubusercontent.com/{owner}/{repo}/master/{path}"
                response = await client.get(url)
            
            if response.status_code != 200:
                content = f"[Error fetching {path}]"
            else:
                content = response.text
                
        return content

    async def get_repository_context(self, owner: str, repo: str) -> str:
        """Fetch and aggregate filtered repository contents for LLM context."""
        tree = await self.get_repository_tree(owner, repo)
        filtered_paths = self.filter_paths(tree)
        
        # Build structure view
        structure = "Repository Structure:\n"
        for path in filtered_paths:
            structure += f"- {path}\n"
        
        # Fetch file contents
        contents = "\nFile Contents:\n"
        for path in filtered_paths:
            content = await self.get_file_content(owner, repo, path)
            contents += f"\n--- FILE: {path} ---\n{content}\n"
            
        return f"{structure}\n{contents}"

