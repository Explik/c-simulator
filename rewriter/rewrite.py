import sys
import json
import os
import clang.cindex
from ast_visitors import AstPrinter
from source_nodes import SourceTreeCreator, SourceTreePrinter
from source_visitors import CompositeTreeVisitor, NotifyDataSerializer, PartialTreeVisitor_BinaryOperator_Assignment, PartialTreeVisitor_BinaryOperator, PartialTreeVisitor_CallExpr, PartialTreeVisitor_DeclRefExpr, PartialTreeVisitor_FunctionDecl, PartialTreeVisitor_GenericLiteral, PartialTreeVisitor_TranslationUnit, PartialTreeVisitor_UnaryOperator, PartialTreeVisitor_UnaryOperator_Assignment, PartialTreeVisitor_VarDecl, SourceTreeModifier

def read_file(file_name): 
    f = open(file_name)
    buffer = f.read()
    f.close()
    return buffer

def write_file(file_name, content): 
    f = open(file_name, "w")
    f.write(content)
    f.close()

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

def generate_temp_files(source_path, c_target_path, js_target_path):
    source_content = read_file(source_path)
    
    print('\nGenerating AST...')
    tu = clang.cindex.Index.create().parse(source_path)
    tu_filter = lambda n: n.location.file.name == source_path
    AstPrinter(tu_filter).print(source_content, tu.cursor)

    print('\nGenerating source tree...')
    source_root = SourceTreeCreator(tu_filter).create(source_content, tu.cursor)
    SourceTreePrinter(False).print(source_root)
    SourceTreePrinter(True).print(source_root)

    print('\nGenerating modification tree...')
    partial_visitors = [
        #PartialTreeVisitor_TranslationUnit(),
        #PartialTreeVisitor_FunctionDecl(),
        #PartialTreeVisitor_VarDecl(),
        PartialTreeVisitor_CallExpr(),
        PartialTreeVisitor_BinaryOperator_Assignment(),
        PartialTreeVisitor_BinaryOperator(),
        PartialTreeVisitor_UnaryOperator_Assignment(),
        PartialTreeVisitor_UnaryOperator(),
        PartialTreeVisitor_DeclRefExpr(),
        #PartialTreeVisitor_GenericLiteral()
    ]
    composite_visitor = CompositeTreeVisitor(partial_visitors)
    modification_root = composite_visitor.visit(source_root)

    print('\nGenerating metadata file...')
    notifications = composite_visitor.get_notifies()
    notification_json = NotifyDataSerializer().serialize_list(notifications)
    code_json = json.dumps(source_content)
    js_target_content = (
        "var Module = Module || { };\n"
        "Module.print = function() { \n   Module.simulatorSteps = Module.simulatorSteps || [];\n   Module.simulatorSteps.push({ action: \"stdout\", value: Array.from(arguments).join(\"\") + \"\\\\n\\n\"});\n}\n"
        "Module.printErr = function() { \n   Module.simulatorSteps = Module.simulatorSteps || [];\n   Module.simulatorSteps.push({ action: \"stderr\", value: Array.from(arguments).join(\"\") + \"\\\\n\\n\"});\n}\n"
        "Module.preRun = Module.preRun || [];\n"
        f"Module.preRun.push(function() {{\n Module.simulatorCode = {code_json};\n Module.simulatorNotifications = {notification_json}; \n}})"
    )
    write_file(js_target_path, js_target_content)

    print("\nGenerating code file...")
    modified_source_root = SourceTreeModifier([modification_root]).visit(source_root)
    c_target_content = f"void notify(int ref);\n {modified_source_root}"
    write_file(c_target_path, c_target_content)

if __name__ == "__main__":
    #if len(sys.argv) < 2:
    #    raise Exception("Sorry, please supply an input file")

    script_file = sys.argv[0]
    input_file = 'C:\\Users\\ovs\\source\\repos\\c-simulator\\examples\\basic-example\\main.c' #sys.argv[1]

    # Generate temporary files 
    temp_c_path = get_path_with_extension(input_file, 'g.c')
    temp_js_path = get_path_with_extension(input_file, 'g.js')
    generate_temp_files(input_file, temp_c_path, temp_js_path)

    # Generate output file
    library_path = get_path_with_name(script_file, 'library.js')
    output_c_path = get_path_with_name(input_file, 'output.js')
    args = (temp_c_path, temp_js_path, library_path, output_c_path)
    command = 'emcc %s -s WASM=1 -s "EXPORTED_FUNCTIONS=[\'_main\']" -s "NO_EXIT_RUNTIME=0" --pre-js %s --js-library %s -o %s' % args
    print(command)
    os.system(command)