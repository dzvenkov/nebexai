import httpx
import os
from typing import List, Dict, Any, Optional

class GitHubClient:
    def __init__(self, token: Optional[str] = None):
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "nebexai-summarizer"
        }
        if token:
            self.headers["Authorization"] = f"token {token}"

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
            
            return response.json().get("tree", [])

    def filter_paths(self, tree: List[Dict[str, Any]]) -> List[str]:
        """Filter paths to include only relevant code and metadata files."""
        ignored_patterns = {
            '.git/', 'node_modules/', 'venv/', '.venv/', '__pycache__/', 
            'dist/', 'build/', '.idea/', '.vscode/', '.DS_Store'
        }
        ignored_extensions = {
            '.png', '.jpg', '.jpeg', '.gif', '.pdf', '.mp4', '.zip', 
            '.ico', '.lock', '.svg', '.bin', '.exe', '.dll', '.so'
        }
        
        relevant_paths = []
        for item in tree:
            path = item.get("path", "")
            if item.get("type") != "blob": continue
            
            # Check ignored prefixes
            if any(path.startswith(pattern) for pattern in ignored_patterns):
                continue
            
            # Check ignored middle segments
            if any(f"/{pattern}" in f"/{path}" for pattern in ignored_patterns):
                continue
            
            # Check extensions
            if any(path.lower().endswith(ext) for ext in ignored_extensions):
                continue
                
            relevant_paths.append(path)
            
        return relevant_paths

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
                return f"[Error fetching {path}]"
            
            return response.text
