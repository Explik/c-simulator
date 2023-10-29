# Based on https://stackoverflow.com/questions/19053707/converting-snake-case-to-lower-camel-case-lowercamelcase
def get_node_type(node): 
    kind = node.kind.name
    return "".join(x.capitalize() for x in kind.lower().split("_"))

class ModificationNode: 
    def getChildren(): 
        raise Exception("Not implemented")

class CompoundModificationNode(ModificationNode):
    def __init__(self, modifications: list[ModificationNode]) -> None:
        super().__init__()

class TemplatedModificationNode(ModificationNode): 
    pass 

# Based on pycparser's NodeVisitor
class AstVisitor:
    def visit(self, node) -> ModificationNode|None: 
        node_type = get_node_type(node)
        node_method_name = 'visit_' + node_type
        node_method = getattr(self, node_method_name, self.generic_visit)

        return node_method(node)

    def generic_visit(self, node) -> ModificationNode|None: 
        node_children = node.get_children()
        node_modifications = [self.visit(c) for c in node_children]
        node_filtered_modifications = [m for m in node_modifications if m != None]

        if len(node_filtered_modifications) == 0:
            return None
        elif len(node_filtered_modifications) == 1:
            return node_modifications[0]
        else:
            return CompoundModificationNode(node_modifications)
 
class AstPrinter: 
    def print(self, code, node, level=0):
        """Recursive function to traverse the AST."""
        print('  ' * level + self._stringify_node(code, node))

        for child in node.get_children():
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
            buffer += f"code={self._get_code_part(code, start.line, start.column, end.line, end.column)} "

        return buffer
    
    def _get_code_part(self, code, l1, c1, l2, c2):
        start_index = self._get_code_index(code, l1, c1)
        end_index = self._get_code_index(code, l2, c2)

        return "\"" + code[start_index:end_index].replace("\n", "\\n") +  "\""

    def _get_code_index(self, code, l, c): 
        current_l = l
        current_c = c - 1
        lines = code.split("\n")
        prior_lines = lines[0:current_l]
        if len(prior_lines) > 0:
            prior_lines[-1] = prior_lines[-1][0:current_c]
            return len("\n".join(prior_lines))
        else: 
            return current_c