#!/usr/bin/env python

import collections
import re
import subprocess
import os, sys

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

class DirectedGraph:
    def __init__(self):
        self._adjacency_matrix = collections.defaultdict(list)
        
    def add_edge_with_label(self, from_vertex, to_vertex, edge_label):
        self._adjacency_matrix[from_vertex].append((to_vertex, edge_label))
        
    def is_empty(self):
        return len(self._adjacency_matrix) == 0
        
    def _collect_same_destination_vertex(self):
        result = dict()
        for from_vertex, destinations in self._adjacency_matrix.iteritems():
            collected_destinations = collections.defaultdict(list)
            for to_vertex, edge_label in destinations:
                collected_destinations[to_vertex].append(edge_label)
            result[from_vertex] = collected_destinations
        return result

    def write_dot_file(self, filename):
        nice_adjacency_matrix = self._collect_same_destination_vertex()
        with open(filename, 'w') as f:
            f.write("digraph dependencies {\n")
            for from_vertex, destinations in nice_adjacency_matrix.iteritems():
                for to_vertex, edge_labels in destinations.iteritems():
                    f.write(" " * 4)
                    f.write("%s -> %s [label='%s'];\n" %
                        (from_vertex, to_vertex, ", ".join(edge_labels)))
            f.write("}\n")
    
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
    files_to_process = get_files_to_process()
    symbol_table = SymbolTable()
    undefined_symbols = []
    # Remember where each defined symbol is defined.
    for file in files_to_process:
        defined, undefined = global_symbols(file)
        for symbol in defined:
            symbol_table.add_defined_symbol_from_file(symbol, file)
        undefined_symbols.append((file, undefined))
    # Find dependencies for undefined symbols.
    dependency_graph = DirectedGraph()
    for file, undefined in undefined_symbols:
        short_file = short_filename(file)
        for symbol in undefined:
            defined_file = symbol_table.file_for_symbol(symbol)
            if defined_file is not None:
                dependency_graph.add_edge_with_label(short_file, short_filename(defined_file), symbol)
    if not dependency_graph.is_empty():
        dependency_graph.write_dot_file("dependency.dot")

if __name__ == "__main__":
    main()