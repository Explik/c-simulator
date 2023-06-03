from pycparser import c_ast

class FindVisitor(c_ast.NodeVisitor): 
    """ Finds first node matching predicate (depth-first)
    """
    def __init__(self, predicate, skip = 0):
        super().__init__()
        self.predicate = predicate
        self.skip = skip

    def visit(self, node):
        if self.predicate(node):
            return node
        for child in node: 
            result = self.visit(child)
            if result != None:
                if self.skip == 0: return result
                else: self.skip -= 1
        return None;

    def generic_visit(self, node):
        return super().generic_visit(node)


class ParentVisitor(c_ast.NodeVisitor): 
    """Adds dynamic property 'parent' to all nodes in tree
       Based on: https://github.com/eliben/pycparser/wiki/FAQ#why-dont-ast-nodes-in-pycparser-have-parent-links
    """

    def __init__(self):
        super().__init__()
        self.current_parent = None
        
    def generic_visit(self, node):
        node.data["parent"] = self.current_parent

        oldparent = self.current_parent
        self.current_parent = node
        for c in node:
            self.visit(c)
        self.current_parent = oldparent


