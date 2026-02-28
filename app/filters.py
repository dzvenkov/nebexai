from typing import List, Dict, Any, Protocol

class FileFilterStrategy(Protocol):
    def filter_paths(self, tree: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        ...

class DefaultFileFilterStrategy:
    def filter_paths(self, tree: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        ignored_patterns = {
            '.git/', 'node_modules/', 'venv/', '.venv/', '__pycache__/', 
            'dist/', 'build/', '.idea/', '.vscode/', '.DS_Store'
        }
        ignored_extensions = {
            '.png', '.jpg', '.jpeg', '.gif', '.pdf', '.mp4', '.zip', 
            '.ico', '.lock', '.svg', '.bin', '.exe', '.dll', '.so'
        }
        
        relevant_items = []
        for item in tree:
            path = item.get("path", "")
            if item.get("type") != "blob": continue
            
            # Check ignored directory segments
            if any(f"/{pattern}" in f"/{path}" for pattern in ignored_patterns):
                continue
            
            # Check extensions
            if any(path.lower().endswith(ext) for ext in ignored_extensions):
                continue
                
            relevant_items.append(item)
            
        return relevant_items
