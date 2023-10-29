import sys
import clang.cindex
from ast_visitors import AstPrinter, AstVisitor, CompoundModificationNode, ModificationNode, ModificationPrinter, ReplaceIdentifierVisitor

class IdempotentAstVisitor(AstVisitor):
    def generic_visit(self, node) -> ModificationNode | None:
        return super().generic_visit(node)

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

print('Generating AST changes...')
modification = CompoundModificationNode([
    ReplaceIdentifierVisitor("i", "new_i").visit(tu.cursor),
    ReplaceIdentifierVisitor("j", "new_j").visit(tu.cursor)
])
ModificationPrinter().print(modification)
print("\n")

print('Applying AST changes')
newCode = modification.apply(code)
print(newCode)