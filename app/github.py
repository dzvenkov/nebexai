import httpx
from typing import List, Dict, Any, Optional
from app.filters import FileFilterStrategy, DefaultFileFilterStrategy

class GitHubClient:
    BRANCH_CANDIDATES = ["main", "master"]

    def __init__(self, token: Optional[str] = None, file_filter: Optional[FileFilterStrategy] = None):
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "nebexai-summarizer"
        }
        if token:
            self.headers["Authorization"] = f"token {token}"
        self.file_filter = file_filter or DefaultFileFilterStrategy()
        self._default_branch: Optional[str] = None
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "GitHubClient":
        self._client = httpx.AsyncClient(headers=self.headers)
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("GitHubClient must be used as an async context manager")
        return self._client

    async def _resolve_default_branch(self, owner: str, repo: str) -> str:
        """Detect the default branch by trying candidates, caching the result."""
        if self._default_branch is not None:
            return self._default_branch
        
        for branch in self.BRANCH_CANDIDATES:
            url = f"{self.base_url}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
            response = await self.client.get(url)
            if response.status_code == 200:
                self._default_branch = branch
                return branch
        
        raise Exception(f"Failed to resolve default branch for {owner}/{repo}")

    async def get_repository_tree(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """Fetch the recursive file tree for the repository."""
        branch = await self._resolve_default_branch(owner, repo)
        url = f"{self.base_url}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
        response = await self.client.get(url)
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch repository tree: {response.text}")
        
        tree_data = response.json()
        return tree_data.get("tree", [])

    def filter_paths(self, tree: List[Dict[str, Any]]) -> List[str]:
        """Filter paths to include only relevant code and metadata files."""
        return self.file_filter.filter_paths(tree)

    async def get_file_content(self, owner: str, repo: str, path: str) -> str:
        """Fetch raw content of a specific file."""
        branch = await self._resolve_default_branch(owner, repo)
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
        response = await self.client.get(url)
        
        if response.status_code != 200:
            return f"[Error fetching {path}]"
        
        return response.text

    async def get_repository_context(self, owner: str, repo: str) -> str:
        """Fetch and aggregate filtered repository contents for LLM context."""
        tree = await self.get_repository_tree(owner, repo)
        filtered_paths = self.filter_paths(tree)
        
        # Sort paths so files closer to root (shorter paths) come first
        filtered_paths.sort(key=lambda p: (p.count('/'), len(p), p))
        
        # Build structure view
        structure = "<repository_structure>\n"
        for path in filtered_paths:
            structure += f"  <path>{path}</path>\n"
        structure += "</repository_structure>\n"
        
        # Fetch file contents
        contents = "<repository_contents>\n"
        for path in filtered_paths:
            content = await self.get_file_content(owner, repo, path)
            contents += f'  <file path="{path}">\n{content}\n  </file>\n'
        contents += "</repository_contents>\n"
            
        return f"{structure}\n{contents}"


