#!/usr/bin/env python

import unittest
from dependency_viz import *

class ReachableVertexesTestCase(unittest.TestCase):
	def test_simple_graph(self):
		builder = DirectedGraph.Builder()
		builder.add_edge_with_label("a", "b", "a->b")
		builder.add_edge_with_label("b", "c", "b->c")
		g = builder.build_graph()
		self.assertEqual(g.reachable_vertexes("c"), set())
		self.assertEqual(g.reachable_vertexes("b"), set(["c"]))
		self.assertEqual(g.reachable_vertexes("a"), set(["b", "c"]))

if __name__ == "__main__":
	unittest.main()
