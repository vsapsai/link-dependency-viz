#!/usr/bin/env python

import unittest
from dependency_viz import *

class ReachableVertexesTestCase(unittest.TestCase):
	def test_simple_graph(self):
		builder = DirectedGraph.Builder()
		builder.add_edge_with_label("a", "b", "a->b")
		builder.add_edge_with_label("b", "c", "b->c")
		g = builder.build_graph()
		self.assertEqual(g.reachable_vertexes("c"), {})
		self.assertEqual(g.reachable_vertexes("b"), {"c": PathItem("c", "b", 1, set(["b->c"]))})
		self.assertEqual(g.reachable_vertexes("a"),
			{"b": PathItem("b", "a", 1, set(["a->b"])), "c": PathItem("c", "b", 2, set(["b->c"]))})

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
		self.assertEqual(g.reachable_vertexes("a"),
			{"b": PathItem("b", "a", 1, set(["a->b"])), "c": PathItem("c", "b", 2, set(["b->c"])),
			"d": PathItem("d", "c", 3, set(["c->d"]))})
		self.assertEqual(g.reachable_vertexes("b"),
			{"c": PathItem("c", "b", 1, set(["b->c"])), "d": PathItem("d", "c", 2, set(["c->d"]))})
		self.assertEqual(g.reachable_vertexes("c"),
			{"b": PathItem("b", "d", 2, set(["d->b"])), "d": PathItem("d", "c", 1, set(["c->d"]))})
		self.assertEqual(g.reachable_vertexes("d"),
			{"b": PathItem("b", "d", 1, set(["d->b"])), "c": PathItem("c", "b", 2, set(["b->c"])),})

if __name__ == "__main__":
	unittest.main()
