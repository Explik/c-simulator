class ModificationNode: 
    pass 

class CompoundModificationNode(ModificationNode):
    def __init__(self, modifications: list[ModificationNode]) -> None:
        super().__init__()

class TemplatedModificationNode(ModificationNode): 
    pass 

# Based on pycparser's NodeVisitor
class AstVisitor:
    def visit(self, node) -> ModificationNode|None: 
        node_type = self._get_node_type(node)
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
    
    def _get_node_type(self, node) -> str:
        # Based on https://stackoverflow.com/questions/19053707/converting-snake-case-to-lower-camel-case-lowercamelcase
        kind = node.kind.name
        return "".join(x.capitalize() for x in kind.lower().split("_"))