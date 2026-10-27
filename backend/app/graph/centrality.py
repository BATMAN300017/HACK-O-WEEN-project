from typing import List, Dict, Any
from collections import defaultdict

def compute_degree_centrality(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    in_deg = defaultdict(int)
    out_deg = defaultdict(int)
    
    for e in edges:
        s, t = e["source"], e["target"]
        out_deg[s] += 1
        in_deg[t] += 1
        
    centralities = {}
    for n in nodes:
        nid = n["id"]
        centralities[nid] = {
            "in_degree": in_deg[nid],
            "out_degree": out_deg[nid],
            "total_degree": in_deg[nid] + out_deg[nid]
        }
    return centralities
