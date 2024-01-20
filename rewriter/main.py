from glob import glob
from ast_visitors import AstPrinter
from pathlib import Path
from typer import Typer, Argument
from modification_nodes import ModificationTreePrinter
from source_nodes import SourceNode, SourceToken, SourceTreeCreator, SourceTreePrinter, SourceTypeResolver, get_source_unit
from source_visitors import CompositeTreeVisitor, PartialTreeVisitor_ArraySubscriptExpr, PartialTreeVisitor_BinaryOperator_Assignment, PartialTreeVisitor_BinaryOperator, PartialTreeVisitor_BinaryOperator_Atomic, PartialTreeVisitor_BinaryOperator_MemberAssignment, PartialTreeVisitor_BreakStmt, PartialTreeVisitor_CaseStmt, PartialTreeVisitor_CallExpr, PartialTreeVisitor_ConditionalOperator, PartialTreeVisitor_CstyleCastExpr, PartialTreeVisitor_DeclRefExpr, PartialTreeVisitor_FunctionDecl, PartialTreeVisitor_FunctionDecl_Prototype, PartialTreeVisitor_GenericLiteral, PartialTreeVisitor_MemberRefExpr, PartialTreeVisitor_ReturnStmt, PartialTreeVisitor_UnaryOperator, PartialTreeVisitor_UnaryOperator_Assignment, PartialTreeVisitor_UnaryOperator_Atomic, PartialTreeVisitor_VarDecl, PartialTreeVisitor_VarDecl_Static, SourceTreeModifier, NodeTreeVisitor, PartialTreeVisitor_StructDecl, get_modification_tree

app = Typer()

@app.command("show")
def show_files(
    pattern: str = Argument(..., help="Glob pattern for files"),
    clang_tree: bool = False,
    source_tree: bool = False,
    modification_tree: bool = False): 
    input_files = glob(pattern, recursive=True)
    show_all = not any([clang_tree, source_tree, modification_tree])
    
    print("show")
    for input_file in input_files:
        source_unit = get_source_unit(input_file)
        if clang_tree or show_all:
            print(f"Clang tree for {input_file}")
            tu_file_name = source_unit.get_clang_root().spelling
            tu_filter = lambda n: n.location.file.name == tu_file_name
            AstPrinter(tu_filter).print(source_unit.get_content(), source_unit.get_clang_root())

        source_root = source_unit.get_source_root()
        if source_tree or show_all:
            print(f"Source tree for {input_file}")
            SourceTreePrinter().print(source_root)

        modification_root = get_modification_tree(source_root)
        if modification_tree or show_all: 
            print(f"Modification tree for {input_file}")
            ModificationTreePrinter().print(modification_root)

@app.command("verify")
def verify_files(pattern: str = Argument(..., help="Glob pattern for files")): 
    input_files = glob(pattern, recursive=True)
    
    print("verify ")
    for input_file in input_files:
        # Verify source tree matches input

        print(input_file)

@app.command("rewrite")
def verify_files(pattern: str = Argument(..., help="Glob pattern for files")): 
    input_files = glob(pattern, recursive=True)
    
    print("rewrite") 
    for input_file in input_files:
        print(input_file)

if __name__ == "__main__": 
    app()
