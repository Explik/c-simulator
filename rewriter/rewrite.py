from __future__ import print_function
import json
import sys
import os

# This is not required if you've installed pycparser into
# your site-packages/ with setup.py
sys.path.extend(['.', '..'])

from pycparser import c_parser, c_ast, parse_file, c_generator
from visitors import AssignmentTransformation, BinaryOpTransformation, DeclTransformation, FileAstTransformation, FlattenVisitor, FuncDefTransformation, IdTransformation, NodeTransformation, NotifyCreator, NotifyVisitor, ParentVisitor, LocationVisitor, DeclarationVisitor, ExpressionTypeVisitor, TransformationVisitor

def get_library_file_name(file_path): 
    file_path_components = os.path.split(file_path)
    file_folder = file_path_components[0]

    return os.path.join(file_folder, "library.js")

def get_temp_file_name(file_path, file_extension): 
    file_path_components = os.path.split(file_path)
    file_name_and_extension = file_path_components[-1].rsplit('.', 1)
    print(file_path_components)
    file_folder = '/'.join(file_path_components[:-1])
    file_name = file_name_and_extension[0]

    if file_folder:
        return os.path.join(file_folder, file_name + ".g." + file_extension)
    else: 
        return file_name + ".g." + file_extension    

def get_output_file_name(file_path): 
    file_path_components = os.path.split(file_path)
    file_folder = '/'.join(file_path_components[:-1])

    if file_folder: 
        return os.path.join(file_folder, "output.js")
    else: 
        return "output.js"

def start_meta_write(file_path1, file_path2): 
    c_file = open(file_path1, "r")
    c_code = c_file.read()
    c_code_escaped = json.dumps(c_code)

    js_code = ("var Module = Module || { };\n"
               "Module.preRun = Module.preRun || [];\n"
               f"Module.preRun.push(function() {{ Module.simulatorCode = {c_code_escaped} }})")
    js_file = open(file_path2, "w")
    js_file.write(js_code)
    js_file.close()

def start_rewrite(file_path1, file_path2):
    ast = parse_file(file_path1, use_cpp=True, cpp_path= 'clang', cpp_args= ['-E'])

    # Add metadata
    ParentVisitor().visit(ast)
    LocationVisitor().visit(ast)
    DeclarationVisitor().visit(ast)
    ExpressionTypeVisitor().visit(ast)

    # Rewrite root
    rewrittenAst = TransformationVisitor([
        FileAstTransformation(),
        FuncDefTransformation(),
        DeclTransformation(),
        AssignmentTransformation(),
        BinaryOpTransformation(),
        IdTransformation(),
        NodeTransformation()
    ]).visit(ast)
    
    generator = c_generator.CGenerator()
    transformed_code = generator.visit(rewrittenAst)

    output_f = open(file_path2, "w")
    output_f.write(transformed_code)
    output_f.close()

def start_transpile(file_path1, file_path2, file_path3, file_path4): 
    os.system('emcc %s -s WASM=1 -o %s -s "EXPORTED_FUNCTIONS=[\'_main\']" --pre-js %s --js-library %s' % (file_path1, file_path2, file_path3, file_path4))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise Exception("Sorry, please supply an input file")
    
    script_file = sys.argv[0]
    library_file = get_library_file_name(script_file)

    input_file = sys.argv[1]
    temp_c_file = get_temp_file_name(input_file, 'c')
    temp_js_file = get_temp_file_name(input_file, 'js')
    output_file = get_output_file_name(temp_c_file)

    start_meta_write(input_file, temp_js_file)
    start_rewrite(input_file, temp_c_file)
    start_transpile(temp_c_file, output_file, temp_js_file, library_file)