from typing import List, Dict, Any, Protocol

class FileFilterStrategy(Protocol):
    def filter_paths(self, tree: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        ...

class BaseFileFilterStrategy:
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

class SizeLimiterFileFilterStrategy:
    """
    Applies a size limit threshold to a given list of files.
    
    Logic:
    1. Prioritize critical files (e.g. readmes, .md files, *doc* files).
       Sort them so files closest to root go first.
    2. For the remaining files, take one from each folder starting from root
       layer by layer until the total expected filesize reaches the limit.
    3. If a file puts the total over the limit, it's included but marked for 
       truncation.
    """
    def __init__(self, max_size_bytes: int = 100_000):
        # 100,000 bytes is roughly 100KB, which is ~25k-30k tokens for typical code.
        self.max_size_bytes = max_size_bytes

    def filter_paths(self, tree: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not tree:
            return []

        # 1. Separate into priority and remaining
        priority_items = []
        remaining_items = []
        
        for item in tree:
            path = item.get("path", "")
            lower_path = path.lower()
            name = lower_path.split("/")[-1]
            
            # Priority criteria: README, *.md, *.txt, *doc*
            is_priority = (
                "readme" in name or 
                name.endswith(".md") or 
                name.endswith(".txt") or 
                "doc" in lower_path
            )
            
            if is_priority:
                priority_items.append(item)
            else:
                remaining_items.append(item)

        # Sort priority items by depth (slashes) then name
        priority_items.sort(key=lambda x: (x.get("path", "").count("/"), x.get("path", "")))

        # 2. Group remaining items by folder depth and directory
        from collections import defaultdict
        
        # dir_map: dict of dir_path -> list of items
        # We sort items within each dir alphabetically
        dir_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for item in remaining_items:
            path = item.get("path", "")
            dir_path = "/".join(path.split("/")[:-1])
            dir_map[dir_path].append(item)
            
        for d in dir_map:
            dir_map[d].sort(key=lambda x: x.get("path", ""))

        # 3. Construct final list keeping track of sizes
        final_items = []
        current_size = 0

        def add_item_if_fits(item: Dict[str, Any], curr_sz: int) -> tuple[bool, int]:
            item_size = item.get("size", 0)
            
            if curr_sz + item_size > self.max_size_bytes:
                # If we have *some* room left, take it but mark it as truncated
                remaining_space = self.max_size_bytes - curr_sz
                if remaining_space > 0:
                    truncated_item = dict(item)
                    truncated_item["size"] = remaining_space
                    truncated_item["_truncated"] = True
                    final_items.append(truncated_item)
                    curr_sz += remaining_space
                return False, curr_sz
                
            final_items.append(item)
            return True, curr_sz + item_size

        # Add priority items first
        for item in priority_items:
            fits, current_size = add_item_if_fits(item, current_size)
            if not fits:
                return final_items

        # Now take one file from each folder, iterating until empty
        # Sort directories by depth first, so root folders go first
        sorted_dirs = sorted(dir_map.keys(), key=lambda d: d.count("/"))
        
        active = True
        while active:
            active = False
            for d in sorted_dirs:
                if dir_map[d]:
                    active = True
                    next_item = dir_map[d].pop(0)
                    fits, current_size = add_item_if_fits(next_item, current_size)
                    if not fits:
                        return final_items

        return final_items

class IndividualFileSizeFilterStrategy:
    """
    Omits any individual file that is larger than the specified limit.
    Useful to avoid spending an entire context budget on a single massive file.
    """
    def __init__(self, max_file_size_bytes: int = 50_000):
        # Default ~50KB per file
        self.max_file_size_bytes = max_file_size_bytes

    def filter_paths(self, tree: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            item for item in tree 
            if item.get("size", 0) <= self.max_file_size_bytes
        ]

class CompositeFileFilterStrategy:
    """
    Applies a list of filter strategies sequentially.
    The output of one strategy becomes the input to the next.
    """
    def __init__(self, strategies: List[FileFilterStrategy]):
        self.strategies = strategies

    def filter_paths(self, tree: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        current_tree = tree
        for strategy in self.strategies:
            current_tree = strategy.filter_paths(current_tree)
            if not current_tree:
                break
        return current_tree

class DefaultFileFilterStrategy(CompositeFileFilterStrategy):
    """
    The default filter composite: 
    1. Strips unwanted files/folders (.git, node_modules, binaries, etc)
    2. Drops single files that are too large (>50KB)
    3. Applies an overall size limit (~90KB), prioritizing docs and sampling folders.
    """
    def __init__(self):
        super().__init__([
            BaseFileFilterStrategy(),
            IndividualFileSizeFilterStrategy(max_file_size_bytes=50_000),
            SizeLimiterFileFilterStrategy(max_size_bytes=90_000)
        ])
