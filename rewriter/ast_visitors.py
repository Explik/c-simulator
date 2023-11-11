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

class AstPrinter: 
    def __init__(self, filter = None) -> None:
        self.filter = filter

    def print(self, code, node, level=0):
        """Recursive function to traverse the AST."""
        print('  ' * level + self._stringify_node(code, node))

        use_filter = self.filter is not None and level == 0
        children = filter(self.filter, node.get_children()) if use_filter else node.get_children()
        for child in children:
            self.print(code, child, level + 1)

    def _stringify_node(self, code, node): 
        buffer = f"{get_node_type(node)}: "

        if hasattr(node, 'type') and hasattr(node.type, 'spelling') and len(f"{node.type.spelling}") != 0:
            buffer += f"type={node.type.spelling} "

        if hasattr(node, 'displayname') and len(f"{node.displayname}") != 0: 
            buffer += f"display_name={node.displayname} "

        if hasattr(node, 'extent'): 
            start = node.extent.start
            end = node.extent.end
            buffer += f"loc=l{start.line}c{start.column} "
            buffer += f"code={self._get_code_part(code, start, end)} "

        return buffer
    
    def _get_code_part(self, code, loc1, loc2):
        start_index = get_code_index(code, loc1)
        end_index = get_code_index(code, loc2)

        return "\"" + code[start_index:end_index].replace("\n", "\\n") +  "\""
    