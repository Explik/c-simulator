# Based on https://stackoverflow.com/questions/19053707/converting-snake-case-to-lower-camel-case-lowercamelcase
from typing import Callable

def get_node_type(node): 
    kind = node.kind.name
    return "".join(x.capitalize() for x in kind.lower().split("_"))

def get_code_index(code, location) -> int: 
    current_l = location.line
    current_c = location.column - 1
    lines = code.split("\n")
    prior_lines = lines[0:current_l]
    if len(prior_lines) > 0:
        prior_lines[-1] = prior_lines[-1][0:current_c]
        return len("\n".join(prior_lines))
    else: 
        return current_c

class ClangNodeStringifier: 
    def stringify(self, node): 
        """Generates string representing clang node"""
        buffer = []

        if hasattr(node, 'type') and hasattr(node.type, 'spelling') and len(f"{node.type.spelling}") != 0:
            buffer.append(f"type={node.type.spelling}")

        if hasattr(node, 'displayname') and len(f"{node.displayname}") != 0: 
            buffer.append(f"display_name={node.displayname}")

        node_name = get_node_type(node)
        node_args = ", ".join(buffer)
        return f"{node_name}({node_args})"

class ClangRootPrinter: 
    def __init__(self, stringifier = None) -> None:
        self.stringifier = stringifier or ClangNodeStringifier()

    def print(self, root): 
        """Recursive function to traverse the AST originating from entry file"""
        file_name = root.spelling
        children = [c for c in root.get_children() if c.location.file.name == file_name]
        self._print(root, children, 0)

    def _print(self, node, node_children, level=0):
        print('  ' * level + self.stringifier.stringify(node))
        
        for child in node_children: 
            self._print(child, child.get_children(), level + 1)