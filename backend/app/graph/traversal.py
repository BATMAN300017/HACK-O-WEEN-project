from typing import List, Dict, Any, Optional
from collections import deque

def find_shortest_path(edges: List[Dict[str, Any]], start_id: str, end_id: str, max_depth: int = 5) -> Optional[List[str]]:
    adj = {}
    for e in edges:
        s, t = e["source"], e["target"]
        if s not in adj:
            adj[s] = []
        adj[s].append(t)
        
    queue = deque([[start_id]])
    visited = {start_id}
    
    while queue:
        path = queue.popleft()
        if len(path) > max_depth + 1:
            break
        current = path[-1]
        if current == end_id:
            return path
            
        for neighbor in adj.get(current, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(path + [neighbor])
                
    return None
