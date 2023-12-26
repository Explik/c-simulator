import sys
import shutil
import json
import os
import subprocess
import clang.cindex
from ast_visitors import AstPrinter
from pathlib import Path
from modification_nodes import ModificationTreePrinter
from source_nodes import SourceNode, SourceToken, SourceTreeCreator, SourceTreePrinter, SourceTypeResolver
from source_visitors import CompositeTreeVisitor, PartialTreeVisitor_ArraySubscriptExpr, PartialTreeVisitor_BinaryOperator_Assignment, PartialTreeVisitor_BinaryOperator, PartialTreeVisitor_BinaryOperator_Atomic, PartialTreeVisitor_BinaryOperator_MemberAssignment, PartialTreeVisitor_BreakStmt, PartialTreeVisitor_CaseStmt, PartialTreeVisitor_CallExpr, PartialTreeVisitor_ConditionalOperator, PartialTreeVisitor_CstyleCastExpr, PartialTreeVisitor_DeclRefExpr, PartialTreeVisitor_FunctionDecl, PartialTreeVisitor_FunctionDecl_Prototype, PartialTreeVisitor_GenericLiteral, PartialTreeVisitor_MemberRefExpr, PartialTreeVisitor_ReturnStmt, PartialTreeVisitor_UnaryOperator, PartialTreeVisitor_UnaryOperator_Assignment, PartialTreeVisitor_UnaryOperator_Atomic, PartialTreeVisitor_VarDecl, PartialTreeVisitor_VarDecl_Static, SourceTreeModifier, NodeTreeVisitor, PartialTreeVisitor_StructDecl

def read_file(file_name): 
    f = open(file_name)
    buffer = f.read()
    f.close()
    return buffer

def write_file(file_name, content): 
    f = open(file_name, "x")
    f.write(content)
    f.close()

def run_command(command): 
    try:
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        return (result.returncode, result.stdout)
    except subprocess.CalledProcessError as e:
        return (e.returncode, e.output)

def get_path_with_name(file_path, file_name): 
    file_path_components = os.path.split(file_path)
    file_folder = file_path_components[0]

    return os.path.join(file_folder, file_name)

def get_path_with_extension(source_path, file_extension):
    file_path_components = os.path.split(source_path)
    file_name_and_extension = file_path_components[-1].rsplit('.', 1)
    print(file_path_components)
    file_folder = '/'.join(file_path_components[:-1])
    file_name = file_name_and_extension[0]

    if file_folder:
        return os.path.join(file_folder, file_name + "." + file_extension)
    else: 
        return file_name + "." + file_extension    

def generate_temp_files(source_path, prejs_path, c_target_path, js_target_path):
    # Build c file
    source_content = read_file(source_path)
    
    print('\nGenerating AST...')
    tu = clang.cindex.Index.create().parse(source_path)
    tu_filter = lambda n: n.location.file.name == source_path
    AstPrinter(tu_filter).print(source_content, tu.cursor)

    print('\nGenerating source tree...')
    SourceToken.reset()
    SourceNode.reset()

    source_root = SourceTreeCreator(tu_filter).create(source_content, tu.cursor)
    SourceTreePrinter().print(source_root)
    if f"{source_root}".strip() != f"{source_content}".strip():
        raise Exception(f"Failed to generate source tree. Generated tree: \n {source_root}")

    print('\nGenerating modification tree...')
    partial_visitors = [
        PartialTreeVisitor_StructDecl(),
        PartialTreeVisitor_FunctionDecl_Prototype(),
        PartialTreeVisitor_FunctionDecl(),
        PartialTreeVisitor_CaseStmt(),
        PartialTreeVisitor_BreakStmt(),
        PartialTreeVisitor_ReturnStmt(),
        PartialTreeVisitor_VarDecl_Static(),
        PartialTreeVisitor_VarDecl(),
        PartialTreeVisitor_CstyleCastExpr(),
        PartialTreeVisitor_ArraySubscriptExpr(),
        PartialTreeVisitor_CallExpr(),
        PartialTreeVisitor_ConditionalOperator(),
        PartialTreeVisitor_BinaryOperator_Atomic(),
        PartialTreeVisitor_BinaryOperator_MemberAssignment(),
        PartialTreeVisitor_BinaryOperator_Assignment(),
        PartialTreeVisitor_BinaryOperator(),
        PartialTreeVisitor_UnaryOperator_Atomic(),
        PartialTreeVisitor_UnaryOperator_Assignment(),
        PartialTreeVisitor_UnaryOperator(),
        PartialTreeVisitor_MemberRefExpr(),
        PartialTreeVisitor_DeclRefExpr(),
        PartialTreeVisitor_GenericLiteral()
    ]
    composite_visitor = CompositeTreeVisitor(partial_visitors)
    modification_root = composite_visitor.visit(source_root)
    ModificationTreePrinter().print(modification_root)
    
    print("\nGenerating code file...")
    modified_source_root = SourceTreeModifier([modification_root]).visit(source_root)
    c_target_declarations = "\n".join([
        "void notify_0(int ref);",
        "void notify_1(int ref, void* ptr1);",
        "void notify_2(int ref, void* ptr1, void* ptr2);",
        "void notify_3(int ref, void* ptr1, void* ptr2, void* ptr3);",
        "void notify_4(int ref, void* ptr1, void* ptr2, void* ptr3, void* ptr4);",
        "void notify_5(int ref, void* ptr1, void* ptr2, void* ptr3, void* ptr4, void* ptr5);",
        "void notify_6(int ref, void* ptr1, void* ptr2, void* ptr3, void* ptr4, void* ptr5, void* ptr6);",
        "void notify_7(int ref, void* ptr1, void* ptr2, void* ptr3, void* ptr4, void* ptr5, void* ptr6, void* ptr7);",
        "void notify_8(int ref, void* ptr1, void* ptr2, void* ptr3, void* ptr4, void* ptr5, void* ptr6, void* ptr7, void* ptr8);",
        "void notify_9(int ref, void* ptr1, void* ptr2, void* ptr3, void* ptr4, void* ptr5, void* ptr6, void* ptr7, void* ptr8, void* ptr9);",
        "void notify_10(int ref, void* ptr1, void* ptr2, void* ptr3, void* ptr4, void* ptr5, void* ptr6, void* ptr7, void* ptr8, void* ptr9, void* ptr10);",
    ])
    c_target_content = f"{c_target_declarations}\n{modified_source_root}"
    write_file(c_target_path, c_target_content)

    print('\nGenerating code metadata file...')
    statement_visitor = NodeTreeVisitor()
    statement_visitor.visit(source_root)
    statements_json = [n.serialize(source_content) for n in statement_visitor.get_nodes()]
    statement_json = "[\n    " + ",\n    ".join(statements_json) +"\n  ]"

    notifications_json = [n.serialize(source_content) for n in composite_visitor.get_notifies()]
    notification_json = "[\n    " + ",\n    ".join(notifications_json) +"\n  ]"

    types_json = [t.serialize() for t in SourceTypeResolver.get_builtin_types()]
    type_json = "[\n    " + ",\n    ".join(types_json) +"\n  ]"

    code_json = json.dumps(source_content)
    
    js_target_content = read_file(prejs_path)
    js_target_content = js_target_content.replace("{code}", code_json) 
    js_target_content = js_target_content.replace("{statements}", statement_json)
    js_target_content = js_target_content.replace("{notifications}", notification_json)
    js_target_content = js_target_content.replace("{types}", type_json)
    write_file(js_target_path, js_target_content)

def generate_output_files(script_file, input_file, output_directory, run_dry_run = True): 
    # Reset application state 
    os.makedirs(output_directory, exist_ok=True)
    SourceNode.id = 0

    # Copy source file
    c_output_file = os.path.join(output_directory, 'source.c')
    shutil.copyfile(input_file, c_output_file)

    # Dry-run 
    if run_dry_run:
        dry_run_js_output = os.path.join(output_directory, 'dryrun.js')
        dry_run_wasm_output = os.path.join(output_directory, 'dryrun.wasm')
        dry_run_command = 'emcc \"%s\" -s WASM=1 -s "EXPORTED_FUNCTIONS=[\'_main\']" -s "NO_EXIT_RUNTIME=0" -o \"%s\"' % (input_file, dry_run_js_output)
        (dry_run_result, dry_run_console) = run_command(dry_run_command)
        if (os.path.exists(dry_run_js_output)): 
            os.remove(dry_run_js_output)
        if (os.path.exists(dry_run_wasm_output)):
            os.remove(dry_run_wasm_output)

        if dry_run_result != 0: 
            raise Exception("Dry run \"%s\" failed with status %s and the following console output \n%s" % (dry_run_command, dry_run_result, dry_run_console))

    # Generate temporary files 
    prejs_path = get_path_with_name(script_file, 'prejs.js')
    temp_c_path = os.path.join(output_directory, 'temp.g.c')
    temp_js_path = os.path.join(output_directory, 'temp.g.js')
    generate_temp_files(input_file, prejs_path, temp_c_path, temp_js_path)

    # Generate output.js file
    output_c_path = os.path.join(output_directory, 'output.js')
    library_path = get_path_with_name(script_file, 'library.js')
    args = (temp_c_path, temp_js_path, library_path, output_c_path)
    command = 'emcc \"%s\" -s WASM=1 -s "EXPORTED_FUNCTIONS=[\'_main\']" -s "NO_EXIT_RUNTIME=0" --pre-js \"%s\" --js-library \"%s\" -o \"%s\"' % args
    (command_result, command_console) = run_command(command)
    
    if command_result != 0: 
        raise Exception("Rewrite \"%s\" failed with status %s and the following console output \n%s" % (dry_run_command, dry_run_result, command_console))

    # Generate index.html file
    index_source_file = get_path_with_name(script_file, 'index.html')
    index_output_file = os.path.join(output_directory, 'index.html')

    shutil.copyfile(index_source_file, index_output_file)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise Exception("Sorry, please supply an input file")

    script_file = sys.argv[0]
    script_file_directory = os.path.split(script_file)[0]
    input_file = sys.argv[1]
    input_file_directory = os.path.split(input_file)[0]
    output_directory = sys.argv[2] if len(sys.argv) >= 3 else input_file_directory

    generate_output_files(script_file, input_file, output_directory)