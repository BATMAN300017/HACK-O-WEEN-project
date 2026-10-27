from typing import Dict, Any, List
from app.graph.centrality import compute_degree_centrality

def extract_graph_metrics(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> Dict[str, Any]:
    centralities = compute_degree_centrality(nodes, edges)
    max_degree = 0
    top_node = None
    for nid, deg in centralities.items():
        if deg["total_degree"] > max_degree:
            max_degree = deg["total_degree"]
            top_node = nid
            
    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "max_degree": max_degree,
        "hub_node_id": top_node,
        "density": round((2.0 * len(edges)) / (len(nodes) * (len(nodes) - 1)), 4) if len(nodes) > 1 else 0.0
    }
