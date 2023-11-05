import sys
import clang.cindex
from ast_visitors import AstPrinter, AstVisitor
from source_nodes import SourceTreeCreator, SourceTreePrinter
from source_visitors import NotifySourceTreeVisitor, ReplaceAdditionSourceTreeVisitor, ReplaceIdentifierSourceTreeVisitor, SourceTreeModifier

def get_code(file_name): 
    f = open(file_name)
    buffer = f.read()
    f.close()
    return buffer

print("Started...")
file_name = ''
code = get_code(file_name)
tu = clang.cindex.Index.create().parse(file_name)  # replace 'sample.c' with your file name

print('Traversing the AST...')
AstPrinter().print(code, tu.cursor)
print("\n")

print('Generating AST...')
source_root = SourceTreeCreator().create(code, tu.cursor)
SourceTreePrinter(False).print(source_root)
SourceTreePrinter(True).print(source_root)

print('Generating AST changes')
modification_root = NotifySourceTreeVisitor().visit(source_root)

print('Applying AST changes')
modified_source_root = SourceTreeModifier(modification_root).visit(source_root)

print(f"{modified_source_root}")

#modification = TransformationVisitor([IdTransformation()]).visit(tu.cursor)
#ModificationPrinter().print(modification)
#print("\n")

#print('Applying AST changes')
#newCode = modification.apply(code)
#print(newCode)