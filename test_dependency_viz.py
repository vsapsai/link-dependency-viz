#!/usr/bin/env python

import unittest
from dependency_viz import *

class ReachableVertexesTestCase(unittest.TestCase):
	def test_simple_graph(self):
		g = DirectedGraph()
		g.add_edge_with_label("a", "b", "a->b")
		g.add_edge_with_label("b", "c", "b->c")
		self.assertEqual(g.reachable_vertexes("c"), set())
		self.assertEqual(g.reachable_vertexes("b"), set(["c"]))
		self.assertEqual(g.reachable_vertexes("a"), set(["b", "c"]))

if __name__ == "__main__":
	unittest.main()
