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
                

class ExpressionTypeResolver(c_ast.NodeVisitor):
    def __init__(self): 
        super().__init__()

    def _translate_type(self, type): 
        if (type == 'string'):
            return 'char*'
        else: 
            return type

    def visit_Constant(self, node): 
        return self._translate_type(node.type)
    
    def visit_IdentifierType(self, node): 
        return node.names[0]

    def visit_TypeDecl(self, node): 
        return self.visit(node.type)

    def visit_PtrDecl(self, node): 
        return self.visit(node.type) + "*"

    def visit_Decl(self, node): 
        return self.visit(node.type)


class ExpressionTypeVisitor(c_ast.NodeVisitor): 
    """Adds dynamic property 'expression-type' to all expression nodes in tree
       NB Requires dynamic 'declaration' to work
       See: https://www.tutorialspoint.com/cprogramming/c_operators.htm
    """

    def __init__(self, property_name = "expression-type"): 
        super().__init__()
        self.property_name = property_name

    def visit_Constant(self, node): 
        node.data[self.property_name] = ExpressionTypeResolver().visit(node)

    def visit_ID(self, node): 
        declaration = node.data.get('declaration') 
        if declaration is None:
            return 
        
        node.data[self.property_name] = ExpressionTypeResolver().visit(declaration)
    
    def visit_UnaryOp(self, node): 
        super().generic_visit(node)
    
        if node.op in ['++']:
            node.data[self.property_name] = node.id.data[self.property_name]

    def visit_BinaryOp(self, node): 
        super().generic_visit(node)
    
        if node.op in ['==', '!=', '<', '<=', '>', '>=', '&&']: 
            node.data[self.property_name] = 'int'
        
        if node.op in ['+', '*']:
            if node.left.data[self.property_name] == node.right.data[self.property_name]:
                 node.data[self.property_name] = node.left.data[self.property_name]

    def visit_Assignment(self, node): 
        super().generic_visit(node)
        
        if node.op in ['=', '+=']:
            node.data[self.property_name] = node.rvalue.data[self.property_name]

# Used by FlattenVisitor
class FlattenVisitor(c_ast.NodeVisitor):
    def __init__(self, counter = 0):
        self.counter = counter

    def visit_Decl(self, node):
        init = None
        variables = None

        if node.init == None: 
            name = 'temp' + str(self.counter)
            self.counter += 1

            init = c_ast.ExprList([c_ast.ID(name), c_ast.ID(name)])
            variables = [self.create_declaration(name, node)]
        else: 
            self.visit(node.init)

            init = node.init.data['flattened-expression']
            variables = node.init.data['flattened-variables']
        
        node.data['flattened-expression'] = c_ast.Decl(
                name=node.name,
                quals=node.quals,
                align=node.align,
                storage=node.storage,
                funcspec=node.funcspec,
                type=node.type, 
                init = init,
                bitsize=node.bitsize,
                coord=node.coord,
                data=node.data
            )
        node.data['flattened-variables'] = variables

    def visit_BinaryOp(self, node):
        expr_buffer = []
        variable_buffer = []
        left_expr = node.left
        right_expr = node.right

        # Visit operator arguments (depth first approach)
        if not isinstance(node.left, c_ast.Constant): 
            self.visit(node.left)
            left_expr = node.left.data['flattened-expression'].exprs[-1]
            expr_buffer.extend(node.left.data['flattened-expression'].exprs[:-1])
            variable_buffer.extend(node.left.data['flattened-variables'])
        if not isinstance(node.right, c_ast.Constant): 
            self.visit(node.right)
            right_expr = node.right.data['flattened-expression'].exprs[-1]
            expr_buffer.extend(node.right.data['flattened-expression'].exprs[:-1])
            variable_buffer.extend(node.right.data['flattened-variables'])

        # Visit operator itself
        name = 'temp' + str(self.counter)
        self.counter += 1

        expr_buffer.append(c_ast.Assignment('=', c_ast.ID(name), c_ast.BinaryOp(node.op, left_expr, right_expr)))
        expr_buffer.append(c_ast.ID(name))
        variable_buffer.append(self.create_declaration(name, node))

        node.data['flattened-expression'] = c_ast.ExprList(expr_buffer)
        node.data['flattened-variables'] = variable_buffer

    def visit_ID(self, node):
        name = 'temp' + str(self.counter)
        self.counter += 1

        node.data['flattened-expression'] = self.create_expression(name, node)
        node.data['flattened-variables'] = [self.create_declaration(name, node)]
    
    def visit_Constant(self, node): 
        name = 'temp' + str(self.counter)
        self.counter += 1

        node.data['flattened-expression'] = self.create_expression(name, node)
        node.data['flattened-variables'] = [self.create_declaration(name, node)]

    def visit_FuncCall(self, node): 
        args_buffer = []
        expr_buffer = []
        variable_buffer = []

        # Visit function arguments
        if node.args is not None: 
            for arg in node.args: 
                if isinstance(arg, c_ast.Constant): 
                    args_buffer.append(arg)
                else: 
                    self.visit(arg)
                    args_buffer.append(arg.data['flattened-expression'].exprs[-1])
                    expr_buffer.extend(arg.data['flattened-expression'].exprs[:-1])
                    variable_buffer.extend(arg.data['flattened-variables'])

        # Visit function call
        if node.data['expression-type'] != 'void':
            name = 'temp' + str(self.counter)
            self.counter += 1

            expr_buffer.append(c_ast.Assignment('=', c_ast.ID(name), c_ast.FuncCall(node.name, c_ast.ExprList(args_buffer))))
            expr_buffer.append(c_ast.ID(name))
            variable_buffer.append(self.create_declaration(name, node))
        else: 
            expr_buffer.append(node)

        node.data['flattened-expression'] = c_ast.ExprList(expr_buffer)
        node.data['flattened-variables'] = variable_buffer

    def create_expression(self, name, expr):
        temp_value = c_ast.ID(name) if expr == None else c_ast.Assignment('=', c_ast.ID(name), expr)

        return c_ast.ExprList([temp_value, c_ast.ID(name)])
    
    def create_declaration(self, name, node): 
        # Does not support pointer types 
        type_identifier = c_ast.IdentifierType([node.data['expression-type']])
        type_decl = c_ast.TypeDecl(name, [], None, type = type_identifier)
        
        return c_ast.Decl(name, [], [], [], [], type_decl, None, None)
        
    def addDeclaration(self, name):
        typeName = c_ast.IdentifierType(['int'])
        type = c_ast.TypeDecl(name, [], None, type = typeName)
        declaration = c_ast.Decl(name, [], [], [], [], type, None, None)
        self.variables.append(declaration)