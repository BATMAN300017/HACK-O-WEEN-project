from typing import List, Dict, Any, Set
from collections import defaultdict

def compute_connected_components(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> List[List[str]]:
    adj = defaultdict(set)
    for e in edges:
        s, t = e["source"], e["target"]
        adj[s].add(t)
        adj[t].add(s)
        
    visited: Set[str] = set()
    components: List[List[str]] = []
    
    for n in nodes:
        nid = n["id"]
        if nid not in visited:
            comp = []
            queue = [nid]
            visited.add(nid)
            while queue:
                curr = queue.pop(0)
                comp.append(curr)
                for neighbor in adj[curr]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
            components.append(comp)
            
    return components
