from __future__ import print_function
import sys

# This is not required if you've installed pycparser into
# your site-packages/ with setup.py
sys.path.extend(['.', '..'])

from pycparser import c_parser, c_ast, parse_file, c_generator
from modules.visitors import FlattenVisitor, NotifyCreator, NotifyVisitor, ParentVisitor, LocationVisitor, DeclarationVisitor, ExpressionTypeVisitor

def start(filename):
    ast = parse_file(filename, use_cpp=True, cpp_path= 'clang', cpp_args= ['-E'])

    # Add metadata
    ParentVisitor().visit(ast)
    LocationVisitor().visit(ast)
    DeclarationVisitor().visit(ast)
    ExpressionTypeVisitor().visit(ast)

    # Rewrite root
    FlattenVisitor().visit(ast)
    NotifyVisitor(NotifyCreator()).visit(ast)
    
    generator = c_generator.CGenerator()
    transformed_code = generator.visit(ast)
    print(transformed_code)


if __name__ == "__main__":
    if len(sys.argv) > 2:
        filename = sys.argv[1]
    else:
        filename = './scripts/main.c'

    start(filename)