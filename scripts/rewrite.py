from __future__ import print_function
import sys

# This is not required if you've installed pycparser into
# your site-packages/ with setup.py
sys.path.extend(['.', '..'])

from pycparser import c_parser, c_ast, parse_file, c_generator
from modules.visitors import ParentVisitor, LocationVisitor


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