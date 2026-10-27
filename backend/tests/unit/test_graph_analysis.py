import unittest
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BACKEND_DIR)

from app.graph.traversal import find_shortest_path
from app.graph.centrality import compute_degree_centrality

class TestGraphAnalysis(unittest.TestCase):
    def test_shortest_path_discovery(self):
        edges = [
            {"source": "A", "target": "B"},
            {"source": "B", "target": "C"},
            {"source": "C", "target": "D"},
            {"source": "A", "target": "D"},
        ]
        # Shortest path from A to D is direct
        path = find_shortest_path(edges, "A", "D")
        self.assertEqual(path, ["A", "D"])

    def test_multi_hop_path(self):
        edges = [
            {"source": "A", "target": "B"},
            {"source": "B", "target": "C"},
        ]
        path = find_shortest_path(edges, "A", "C")
        self.assertEqual(path, ["A", "B", "C"])

    def test_degree_centrality_calculation(self):
        nodes = [{"id": "A"}, {"id": "B"}, {"id": "C"}]
        edges = [
            {"source": "A", "target": "B"},
            {"source": "C", "target": "B"},
        ]
        centralities = compute_degree_centrality(nodes, edges)
        self.assertEqual(centralities["B"]["in_degree"], 2)
        self.assertEqual(centralities["A"]["out_degree"], 1)

if __name__ == "__main__":
    unittest.main()
