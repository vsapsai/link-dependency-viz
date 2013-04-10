#!/usr/bin/env python

import unittest
from dependency_viz import *

class ReachableVertexesTestCase(unittest.TestCase):
	def test_simple_graph(self):
		builder = DirectedGraph.Builder()
		builder.add_edge_with_label("a", "b", "a->b")
		builder.add_edge_with_label("b", "c", "b->c")
		g = builder.build_graph()
		self.assertEqual(set(g.reachable_vertexes("c").keys()), set())
		self.assertEqual(set(g.reachable_vertexes("b").keys()), set(["c"]))
		self.assertEqual(set(g.reachable_vertexes("a").keys()), set(["b", "c"]))

	def test_separate_vertexes(self):
		builder = DirectedGraph.Builder()
		builder.add_vertex("a")
		builder.add_vertex("b")
		g = builder.build_graph()
		self.assertEqual(g.reachable_vertexes("a"), {})
		self.assertEqual(g.reachable_vertexes("b"), {})

	def test_self_reference(self):
		builder = DirectedGraph.Builder()
		builder.add_edge_with_label("a", "a", "cycle")
		g = builder.build_graph()
		self.assertEqual(g.reachable_vertexes("a"), {})

	def test_cycle(self):
		# a -> b -> c
		#      ^\ /_
		#        d
		builder = DirectedGraph.Builder()
		builder.add_edge_with_label("a", "b", "a->b")
		builder.add_edge_with_label("b", "c", "b->c")
		builder.add_edge_with_label("c", "d", "c->d")
		builder.add_edge_with_label("d", "b", "d->b")
		g = builder.build_graph()
		self.assertEqual(set(g.reachable_vertexes("a").keys()), set(["b", "c", "d"]))
		self.assertEqual(set(g.reachable_vertexes("b").keys()), set(["c", "d"]))
		self.assertEqual(set(g.reachable_vertexes("c").keys()), set(["b", "d"]))
		self.assertEqual(set(g.reachable_vertexes("d").keys()), set(["b", "c"]))

if __name__ == "__main__":
	unittest.main()
