#!/usr/bin/env python

import collections
import re
import subprocess
import os, sys
from operator import attrgetter, methodcaller

DEFINED_SYMBOL_TYPE = 'S'
UNDEFINED_SYMBOL_TYPE = 'U'
UNKNOWN_SYMBOL_TYPE = '?'

def parse_symbol_string(symbol_string):
    """Takes a string like '                 U _OBJC_CLASS_$_NSView' and returns symbol type and name"""
    match = re.match(r".+ ([a-zA-Z]) (.*)$", symbol_string)
    if match:
        symbol_type = match.group(1)
        symbol_name = match.group(2)
        if symbol_type in [DEFINED_SYMBOL_TYPE, UNDEFINED_SYMBOL_TYPE]:
            return symbol_type, symbol_name
    return UNKNOWN_SYMBOL_TYPE, None

def global_symbols(filename):
    """Returns tuple of lists - (defined_symbols, undefined_symbols)."""
    defined_symbols = []
    undefined_symbols = []
    global_symbols_text = subprocess.check_output(["nm", "-g", filename])
    for line in global_symbols_text.splitlines():
        symbol_type, symbol_name = parse_symbol_string(line)
        if symbol_type == DEFINED_SYMBOL_TYPE:
            defined_symbols.append(symbol_name)
        elif symbol_type == UNDEFINED_SYMBOL_TYPE:
            undefined_symbols.append(symbol_name)
    return defined_symbols, undefined_symbols

class SymbolTable:
    """SymbolTable tracks in which file which symbol was defined."""
    def __init__(self):
        self._symbol_to_file_dict = dict()
        
    def add_defined_symbol_from_file(self, symbol_name, filename):
        conflicting_filename = self._symbol_to_file_dict.get(symbol_name)
        #assert conflicting_filename is None
        self._symbol_to_file_dict[symbol_name] = filename
        
    def file_for_symbol(self, symbol_name):
        return self._symbol_to_file_dict.get(symbol_name)

def short_filename(file_path):
    """Strips directory and extension from file path."""
    return os.path.splitext(os.path.split(file_path)[1])[0]

def readable_symbol_name(symbol_name):
    """Strips known unreadable prefixes."""
    prefixes = ('_OBJC_CLASS_$_', '_OBJC_METACLASS_$_')
    for prefix in prefixes:
        if symbol_name.startswith(prefix):
            symbol_name = symbol_name[len(prefix):]
            break  # Strip single prefix.
    return symbol_name

class DirectedGraph:
    class Builder:
        def __init__(self):
            self._edges = collections.defaultdict(list)

        def add_edge_with_label(self, from_vertex, to_vertex, edge_label):
            self._edges[from_vertex].append((to_vertex, edge_label))
            self.add_vertex(to_vertex)

        def add_edge_with_labels(self, from_vertex, to_vertex, edge_labels):
            assert len(edge_labels) > 0
            for label in edge_labels:
                self.add_edge_with_label(from_vertex, to_vertex, label)

        def add_vertex(self, vertex):
            if vertex not in self._edges:
                self._edges[vertex] = []

        def build_graph(self):
            adjacency_matrix = dict()
            for from_vertex, destinations in self._edges.iteritems():
                collected_destinations = collections.defaultdict(set)
                for to_vertex, edge_label in destinations:
                    collected_destinations[to_vertex].add(edge_label)
                adjacency_matrix[from_vertex] = dict(collected_destinations)
            return DirectedGraph(adjacency_matrix)

    def __init__(self, adjacency_matrix):
        self._adjacency_matrix = adjacency_matrix

    def __eq__(self, other):
        return self._adjacency_matrix == other._adjacency_matrix

    def __ne__(self, other):
        return not (self == other)
        
    def is_empty(self):
        return len(self._adjacency_matrix) == 0

    def vertexes(self):
        """Returns all vertexes."""
        return frozenset(self._adjacency_matrix.keys())

    def write_dot_file(self, filename, write_edge_labels=False):
        with open(filename, 'w') as f:
            f.write("digraph dependencies {\n")
            for from_vertex, destinations in self._adjacency_matrix.iteritems():
                for to_vertex, edge_labels in destinations.iteritems():
                    f.write(" " * 4)
                    f.write("%s -> %s" % (from_vertex, to_vertex))
                    if write_edge_labels:
                        f.write(" [label='%s']" % ", ".join(sorted(edge_labels)))
                    f.write(";\n")
                # Write vertex without outgoing nodes
                if len(destinations) == 0:
                    f.write(" " * 4)
                    f.write("%s;\n" % from_vertex)
            f.write("}\n")

    def subgraph(self, sub_vertexes):
        builder = DirectedGraph.Builder()
        for from_vertex, destinations in self._adjacency_matrix.iteritems():
            if from_vertex not in sub_vertexes:
                continue
            builder.add_vertex(from_vertex)
            for to_vertex, edge_labels in destinations.iteritems():
                if to_vertex in sub_vertexes:
                    builder.add_edge_with_labels(from_vertex, to_vertex, edge_labels)
        return builder.build_graph()

    def reversed_graph(self):
        builder = DirectedGraph.Builder()
        for from_vertex, destinations in self._adjacency_matrix.iteritems():
            builder.add_vertex(from_vertex)
            for to_vertex, edge_labels in destinations.iteritems():
                builder.add_edge_with_labels(to_vertex, from_vertex, edge_labels)
        return builder.build_graph()

    def _reachable_vertexes(self, from_vertex, visited):
        visited.add(from_vertex)
        reachable = dict()
        for to_vertex, edge_labels in self._adjacency_matrix[from_vertex].iteritems():
            if to_vertex in visited:
                continue
            new_path_item = PathItem(to_vertex, from_vertex, 1, edge_labels)
            current_path_item = reachable.get(to_vertex)
            if (current_path_item is None) or (new_path_item.distance < current_path_item.distance):
                reachable[to_vertex] = new_path_item
            transitive_reachable = self._reachable_vertexes(to_vertex, visited)
            for reachable_vertex, reachable_path_item in transitive_reachable.iteritems():
                current_path_item = reachable.get(reachable_vertex)
                if (current_path_item is None) or (reachable_path_item.distance + 1 < current_path_item.distance):
                    reachable[reachable_vertex] = PathItem(reachable_vertex,
                        reachable_path_item.prev_vertex,
                        reachable_path_item.distance + 1,
                        reachable_path_item.edge_labels)
        return reachable

    def reachable_vertexes(self, from_vertex):
        visited = set()
        return self._reachable_vertexes(from_vertex, visited)

class PathItem:
    def __init__(self, vertex, prev_vertex, distance, edge_labels):
        self.vertex = vertex
        self.prev_vertex = prev_vertex
        self.distance = distance
        self.edge_labels = edge_labels

    def __str__(self):
        return "%d: %s -> %s" % (self.distance, self.prev_vertex, self.vertex)

    def __eq__(self, other):
        return ((self.vertex == other.vertex) and
            (self.prev_vertex == other.prev_vertex) and
            (self.distance == other.distance) and
            (self.edge_labels == other.edge_labels))

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash(self.vertex) + hash(self.prev_vertex) + hash(self.distance) + hash(self.edge_labels)

    def path_from_root(self, path_items_dict):
        if self.distance == 1:
            return [self]
        return path_items_dict[self.prev_vertex].path_from_root(path_items_dict) + [self]

class DependencyReport():
    def __init__(self, filename, required_dependencies, provided_dependencies):
        self._filename = filename
        self._required_dependencies = required_dependencies
        self._provided_dependencies = provided_dependencies

    def __str__(self):
        return self.filename()

    def filename(self):
        return self._filename

    def required_dependencies(self):
        return self._required_dependencies

    def provided_dependencies(self):
        return self._provided_dependencies

    def required_dependencies_count(self):
        return len(self._required_dependencies)

    def provided_dependencies_count(self):
        return len(self._provided_dependencies)

    def most_distant_required_dependency(self):
        path_items = self.required_dependencies().values()
        return max(path_items, key=attrgetter("distance")) if len(path_items) > 0 else None

    def longest_required_distance(self):
        most_distant_dependency = self.most_distant_required_dependency()
        return most_distant_dependency.distance if most_distant_dependency is not None else 0

    def longest_required_path(self):
        most_distant_dependency = self.most_distant_required_dependency()
        return most_distant_dependency.path_from_root(self.required_dependencies()) if most_distant_dependency is not None else []

    def print_layered_dependencies(self, dependencies):
        print(self.filename())
        while len(dependencies) > 0:
            # Find closest dependencies.
            closest_dependencies = []
            for dependency in dependencies:
                if len(closest_dependencies) == 0:
                    closest_dependencies.append(dependency)
                elif dependency.distance < closest_dependencies[0].distance:
                    closest_dependencies = [dependency]
                elif dependency.distance == closest_dependencies[0].distance:
                    closest_dependencies.append(dependency)
            assert len(closest_dependencies) > 0
            # Print closest dependencies.
            # TODO: group by prev_vertex
            print(closest_dependencies[0].distance)
            for dependency in closest_dependencies:
                print("    %s <- %s [%s]" % (dependency.vertex, dependency.prev_vertex,
                    ", ".join(sorted(dependency.edge_labels))))
            # Remove closest dependencies from dependencies.
            closest_filenames = set(dependency.vertex for dependency in closest_dependencies)
            dependencies = [d for d in dependencies if d.vertex not in closest_filenames]

class Dependencies:
    _UNDEFINED_FILE = "<Undefined>"

    def __init__(self, link_file_list_filename):
        with open(link_file_list_filename, "r") as f:
            files_to_process = f.read().splitlines()
        symbol_table = SymbolTable()
        undefined_symbols = []
        # Remember where each defined symbol is defined.
        for file in files_to_process:
            defined, undefined = global_symbols(file)
            for symbol in defined:
                symbol_table.add_defined_symbol_from_file(symbol, file)
            undefined_symbols.append((file, undefined))
        # Find dependencies for undefined symbols.
        graph_builder = DirectedGraph.Builder()
        for file, undefined in undefined_symbols:
            short_file = short_filename(file)
            graph_builder.add_vertex(short_file)
            for symbol in undefined:
                defined_file = symbol_table.file_for_symbol(symbol)
                defined_file = short_filename(defined_file) if defined_file is not None else Dependencies._UNDEFINED_FILE
                graph_builder.add_edge_with_label(short_file, defined_file, readable_symbol_name(symbol))                    
        self._dependency_graph = graph_builder.build_graph()
        self._marked_files = frozenset([Dependencies._UNDEFINED_FILE])
        self._dependency_dicts = [None, None]

    def mark_files(self, link_file_list_filename):
        with open(link_file_list_filename, "r") as f:
            files = f.read().splitlines()
        files = [short_filename(f) for f in files]
        files.append(Dependencies._UNDEFINED_FILE)
        self._marked_files = frozenset(files)

    def files(self):
        return self._dependency_graph.vertexes()

    def marked_files(self):
        return self._marked_files

    def dump(self, filename, write_edge_labels=False):
        assert not self._dependency_graph.is_empty()
        self._dependency_graph.write_dot_file(filename, write_edge_labels)

    def dump_subgraph(self, filename, vertexes, write_edge_labels=False):
        subgraph = self._dependency_graph.subgraph(vertexes)
        assert not subgraph.is_empty()
        subgraph.write_dot_file(filename, write_edge_labels)

    def required_dependencies(self, filename, verbose=True, include_marked_files=True):
        filename = short_filename(filename)
        dependencies = self._all_dependencies_dict(include_marked_files)[filename].required_dependencies()
        return dependencies if verbose else set(dependencies.keys())

    def provided_dependencies(self, filename, verbose=True, include_marked_files=True):
        filename = short_filename(filename)
        dependencies = self._all_dependencies_dict(include_marked_files)[filename].provided_dependencies()
        return dependencies if verbose else set(dependencies.keys())

    def _all_dependencies_dict(self, include_marked_files):
        dict_index = 0 if include_marked_files else 1
        if self._dependency_dicts[dict_index] is None:
            dependency_dict = {}
            dependency_graph = self._dependency_graph
            if not include_marked_files:
                left_files = self.files() - self.marked_files()
                dependency_graph = dependency_graph.subgraph(left_files)
            reversed_dependency_graph = dependency_graph.reversed_graph()
            for filename in dependency_graph.vertexes():
                required_dependencies = dependency_graph.reachable_vertexes(filename)
                provided_dependencies = reversed_dependency_graph.reachable_vertexes(filename)
                report = DependencyReport(filename, required_dependencies, provided_dependencies)
                dependency_dict[filename] = report
            self._dependency_dicts[dict_index] = dependency_dict
        return self._dependency_dicts[dict_index]

    def all_dependencies(self, include_marked_files=True):
        return self._all_dependencies_dict(include_marked_files).values()

    def files_connection(self, file1, file2):
        file1 = short_filename(file1)
        file2 = short_filename(file2)
        result = []
        direct_dependencies = self.required_dependencies(file1, verbose=True, include_marked_files=True)
        if file2 in direct_dependencies:
            result.append(direct_dependencies[file2].path_from_root(direct_dependencies))
        reverse_dependencies = self.required_dependencies(file2, verbose=True, include_marked_files=True)
        if file1 in reverse_dependencies:
            result.append(reverse_dependencies[file1].path_from_root(reverse_dependencies))
        return result

    # Convenience methods which provide answers for common questions.

    def _top_files(self, criteria_method_name, count, include_marked_files=True, descending=True):
        result = self.all_dependencies()
        result.sort(key=methodcaller(criteria_method_name), reverse=descending)
        return result[:count]

    # Which file has most dependencies?
    def most_dependent_file(self, count=5):
        return self._top_files("required_dependencies_count", count, include_marked_files=True)

    # What is the longest chain of dependencies?
    def longest_dependency_chain(self, count=5):
        return self._top_files("longest_required_distance", count, include_marked_files=True)

    # What file is most needed?
    def most_used_file(self, count=5):
        return self._top_files("provided_dependencies_count", count, include_marked_files=False)

    # What file is most needed among those without external dependencies?
    def most_used_independent_file(self, count=5):
        independent_files = [report for report in self.all_dependencies(include_marked_files=False)
            if report.required_dependencies_count() == 0]
        independent_files.sort(key=methodcaller("provided_dependencies_count"), reverse=True)
        return independent_files[:count]

def print_usage():
    print """You must provide LINK_FILE_LIST_FILE
Usage: dependency-viz LINK_FILE_LIST_FILE"""

def get_files_to_process():
    if len(sys.argv) != 2:
        print_usage()
        sys.exit(1)
    linkFileListFilename = sys.argv[1]
    with open(linkFileListFilename, "r") as f:
        files_to_process = f.read().splitlines()
    return files_to_process

def main():
    if len(sys.argv) != 2:
        print_usage()
        sys.exit(1)
    link_file_list_filename = sys.argv[1]
    dependencies = Dependencies(link_file_list_filename)
    dependencies.dump("dependency.dot")

if __name__ == "__main__":
    main()

# I have an idea to run dependency-viz from Python REPL, not as a standalone
# command line tool.  It will reduce UI overhead.
#
# How I want to use dependency-visualizer (wishful thinking):
# > dependencies = Dependencies(linkFileListFilename)
# > dependencies.mark_files(unitTestLinkFileListFilename)
#
# -- write a graph
# > dependencies.dump("dependency.dot", write_edge_labels)
# > dependencies.dump_subgraph("dependency.dot", vertexes, write_edge_labels)
#
# -- trivial getters
# > print dependencies.files()
# > print dependencies.marked_files()
#
# -- what [transitive] dependencies should be satisfied to add file to tests
# > print dependencies.required_dependencies(filename, verbose, include_marked_files)
#
# -- find which file is most needed
# > print dependencies.provided_dependencies(filename, verbose, include_marked_files)
# > dependencies.all_dependencies()  # returns filename with provided and required dependencies
# > dependencies.files_connection(file1, file2)  # paths file1->file2, file2->file1
#
# -- pretty print dependencies
# > r.print_layered_dependencies(r.required_dependencies().values())
#
# -- kinda cycle detection
# > dependencies.strong_connected_components()

# TODO:
# - fix function symbols, because they are T _FunctionName, S _FunctionName.eh
