from __future__ import print_function
import sys
import modules.visitors

# This is not required if you've installed pycparser into
# your site-packages/ with setup.py
sys.path.extend(['.', '..'])

from pycparser import c_parser, c_ast, parse_file, c_generator

# Finds first node matching predicate (depth-first)
class FindVisitor(c_ast.NodeVisitor): 
    def __init__(self, predicate):
        super(FindVisitor, self).__init__()
        self.predicate = predicate

    def visit(self, node):
        if self.predicate(node):
            return node
        for child in node: 
            result = self.visit(child)
            if result != None: 
                return result;
        return None;

    def generic_visit(self, node):
        return super().generic_visit(node)

# Adds parent data to node
class ParentVisitor(c_ast.NodeVisitor):
    def __init__(self):
        super(ParentVisitor, self).__init__()
        self.current_parent = None

    def generic_visit(self, node):
        node.data["parent"] = self.current_parent

        old_parent = self.current_parent
        self.current_parent = node
        for child_node in node:
            self.visit(child_node)
        self.current_parent = old_parent
        return node

# Adds location data to node
class LocationVisitor(c_ast.NodeVisitor): 
    def __init__(self) -> None:
        super(LocationVisitor, self).__init__()
    
    def visit_Constant(self, node): 
        node.data["location"] = [
            node.coord.line, # start line
            node.coord.column, # start column
            node.coord.line, # end line
            node.coord.column + len(node.value) # end column
        ]

    def visit_BinaryOp(self, node): 
        super().generic_visit(node)

        leftLocation = node.left.data["location"]
        rightLocation = node.right.data["location"]
        node.data["location"] = [
            leftLocation[0], # start line
            leftLocation[1], # start column
            rightLocation[2], # end line
            rightLocation[3] # end column
        ]

# Adds type data to node 
class TypeVisitor(c_ast.NodeVisitor):
    def __init__(self) -> None:
        super(TypeVisitor, self).__init__()
    
    def visit_Constant(self, node): 
        match node.type: 
            case "string":
                node.data["type"] = "char*"
            case _: 
                node.data["type"] = node.type

    def visit_BinaryOp(self, node): 
        super().generic_visit(node)

        leftType = node.left.data["type"]
        rightType = node.right.data["type"]

        # T + T -> T
        if (leftType == rightType):
            node.data["type"] = leftType

class IfVisitor(c_ast.NodeVisitor):
    def __init__(self):
        super(IfVisitor, self).__init__()
        self.temp_variables = []

    def visit_Compound(self, node):
        if(isinstance(node.data["parent"], c_ast.FuncDef)):
            node.show()
            self.generic_visit(node);
            
            for index, item in enumerate(self.temp_variables):
                node.block_items.insert(index, item)

            self.temp_variables = []
            node.show()

        else:
            self.generic_visit(node);
    
    def visit_Decl(self, node): 
        if isinstance(node.type, c_ast.TypeDecl):
            visitor = DecomposeVisitor(len(self.temp_variables))
            visitor.visit(node)
            self.temp_variables.extend(visitor.variables)
        node.show()

class DecomposeVisitor(c_ast.NodeVisitor):
    def __init__(self, counter = 0):
        self.counter = counter
        self.expression = c_ast.ExprList([])
        self.variables = []

    def visit_Decl(self, node):
        if node.init == None: 
            buffer = []
            name = 'temp' + str(self.counter)
            self.counter += 1

            buffer.append(self.createExpression(name, None))
            buffer.append(c_ast.ID(name))

            self.addDeclaration(name)
            node.init = c_ast.ExprList(buffer)
        else: 
            node.init = self.visit(node.init)
        
        return node

    def visit_BinaryOp(self, node):
        # Visit operator arguments (depth first)
        left = node.left if isinstance(node.left, c_ast.Constant) else self.visit(node.left)
        right = node.right if isinstance(node.right, c_ast.Constant) else self.visit(node.right)

        # Creates expr(temp_n = ...)
        buffer = []
        name = 'temp' + str(self.counter)
        self.counter += 1

        if isinstance(left, c_ast.ExprList):
            buffer.extend(left.exprs[:-1])
            left = left.exprs[-1]
        if (isinstance(right, c_ast.ExprList)):
            buffer.extend(right.exprs[:-1])
            right = right.exprs[-1]

        buffer.append(self.createExpression(name, c_ast.BinaryOp(node.op, left, right)))
        buffer.append(c_ast.ID(name))

        self.addDeclaration(name)
        return c_ast.ExprList(buffer)

    def visit_ID(self, node):
        buffer = []
        name = 'temp' + str(self.counter)
        self.counter += 1
    
        buffer.append(self.createExpression(name, node))
        buffer.append(c_ast.ID(name))

        self.addDeclaration(name)
        return c_ast.ExprList(buffer)
    
    def visit_Constant(self, node): 
        buffer = []
        name = 'temp' + str(self.counter)
        self.counter += 1
    
        buffer.append(self.createExpression(name, node))
        buffer.append(c_ast.ID(name))

        self.addDeclaration(name)
        return c_ast.ExprList(buffer)

    def createExpression(self, name, expr):
        tempValue = c_ast.ID(name) if expr == None else c_ast.Assignment('=', c_ast.ID(name), expr)

        return c_ast.FuncCall(
            c_ast.ID('expr'),
            c_ast.ExprList([
                c_ast.Constant('string', '""'),
                tempValue]))

    def addDeclaration(self, name):
        typeName = c_ast.IdentifierType(['int'])
        type = c_ast.TypeDecl(name, [], None, type = typeName)
        declaration = c_ast.Decl(name, [], [], [], [], type, None, None)
        self.variables.append(declaration)

def start(filename):
    ast = parse_file(filename, use_cpp=True, cpp_path= 'clang', cpp_args= ['-E'])

    # Add metadata
    ParentVisitor().visit(ast)
    #LocationVisitor().visit(ast)

    # Rewrite root
    IfVisitor().visit(ast)

    generator = c_generator.CGenerator()
    transformed_code = generator.visit(ast)
    print(transformed_code)


if __name__ == "__main__":
    if len(sys.argv) > 2:
        filename = sys.argv[1]
    else:
        filename = './main.c'

    start(filename)