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


class LocationVisitor(c_ast.NodeVisitor): 
    """Adds dynamic property 'location' to all nodes in tree
       location is defined as [start line, start column, end line, end column]
       NB Only partially implemented
    """
    
    def __init__(self):
        super().__init__()

    def _visit_width_based_node(self, node, length): 
        """Calculates width for nodes whoes extend is length dependent"""
        node.data["location"] = [
            node.coord.line,
            node.coord.column,
            node.coord.line,
            node.coord.column + length
        ]
    
    def _visit_child_based_node(self, node, first_child = None, last_child = None, padding = 0): 
        """Calculates width for nodes whoes extend is child dependent"""
        super().generic_visit(node)

        first_child = first_child if first_child is not None else node.children()[0][1]
        last_child = last_child if last_child is not None else node.children()[-1][1]
        
        if "location" not in first_child.data: 
            raise Exception(str(type(first_child)) + " is missing location")
        if "location" not in last_child.data: 
            raise Exception(str(type(last_child)) + " is missing location")

        first_location =  first_child.data["location"]
        last_location = last_child.data["location"]
        node.data["location"] = [
            first_location[0],
            first_location[1],
            last_location[2],
            last_location[3] + padding
        ]

    def generic_visit(self, node):
        return self._visit_child_based_node(node)

    def visit_Constant(self, node): 
        self._visit_width_based_node(node, len(node.value))

    def visit_BinaryOp(self, node): 
        self._visit_child_based_node(node, node.left, node.right)

    def visit_Decl(self, node): 
        self._visit_child_based_node(node, padding = 1 if len(node.children()) > 1 else len(node.name) + 2)

    def visit_FuncCall(self, node): 
        self._visit_child_based_node(node, padding = 0 if node.args is not None else 2)

    def visit_ID(self, node): 
        self._visit_width_based_node(node, len(node.name))

    def visit_IdentifierType(self, node): 
        self._visit_width_based_node(node, len(''.join(node.names)))

    def visit_ExprList(self, node): 
        self._visit_child_based_node(node, padding = 1)


class DeclarationVisitor(c_ast.NodeVisitor): 
    """Adds dynamic property 'declaration' to all identifier nodes in tree
       NB Only supports local variables
    """
    
    def __init__(self):
        super().__init__()
        self.block_declarations = [] # 2D array [block][variable]

    def visit_Compound(self, node):
        self.block_declarations.append([])
        for c in node:
            self.visit(c)
        self.block_declarations.pop()

    def visit_Decl(self, node): 
        if len(self.block_declarations) > 0:
            self.block_declarations[-1].append(node)

    def visit_ID(self, node): 
        for block in reversed(self.block_declarations): 
            for declaration in block: 
                if declaration.name == node.name:
                    node.data["declaration"] = declaration
                    return