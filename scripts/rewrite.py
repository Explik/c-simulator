from __future__ import print_function
import sys

# This is not required if you've installed pycparser into
# your site-packages/ with setup.py
sys.path.extend(['.', '..'])

from pycparser import c_parser, c_ast, parse_file, c_generator
from modules.visitors import FlattenVisitor, NotifyCreator, NotifyVisitor, ParentVisitor, LocationVisitor, DeclarationVisitor, ExpressionTypeVisitor

def start(filename1, filename2):
    ast = parse_file(filename1, use_cpp=True, cpp_path= 'clang', cpp_args= ['-E'])

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

    output_f = open(filename2, "w")
    output_f.write(transformed_code)
    output_f.close()

if __name__ == "__main__":
    if len(sys.argv) > 2:
        filename1 = sys.argv[1]
    else:
        filename1 = './scripts/example/input.c'

    if len(sys.argv) > 3:
        filename2 = sys.argv[1]
    else: 
        filename2 = './scripts/example/temp.c'

    start(filename1, filename2)