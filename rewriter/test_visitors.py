import unittest
import re
from pycparser import c_ast, c_parser, c_generator
from visitors import AssignmentTransformation, BinaryOpTransformation, DeclTransformation, FileAstTransformation, FindVisitor, ConstantNotifyInfoCreator, FlattenVisitor, FuncDefTransformation, NodeTransformation, NotifyCreator, NotifyVisitor, ParentVisitor, LocationVisitor, DeclarationVisitor, ExpressionTypeVisitor, IdTransformation

def parse(src): 
    parser = c_parser.CParser(
                lex_optimize=False,
                yacc_debug=True,
                yacc_optimize=False,
                yacctab='yacctab')
    return parser.parse(src)
def stringify(node): 
    return c_generator.CGenerator().visit(node)

def find_node(root, predicate, skip_matches = 0): 
    return FindVisitor(predicate, skip_matches).visit(root)
def find_node_of_type(root, type, skip_matches = 0): 
    return find_node(root, lambda n: isinstance(n, type), skip_matches)
def find_decl_with_name(root, name, skip_matches = 0):
    return find_node(root, lambda n: isinstance(n, c_ast.Decl) and n.name == name, skip_matches)
def find_id_with_name(root, name, skip_matches = 0):
    return find_node(root, lambda n: isinstance(n, c_ast.ID) and n.name == name, skip_matches)

def fail(node):
   raise Exception()

def create_single_declaration(): 
    src = "int main() { int temp0; }"
    root = parse(src)
    return [find_node_of_type(root, c_ast.Decl, skip_matches=1)]

def create_multiple_declarations(): 
    src = "int main() { int temp0; int temp1;  }"
    root = parse(src)
    return [find_node_of_type(root, c_ast.Decl, skip_matches=1), find_node_of_type(root, c_ast.Decl, skip_matches=2)]

def create_identity_callback(): 
    def callback(node):
        return node

# Produces [ID("CALLBACK_EXPR_1, CALLBACK_VALUE_1")], [ID("CALLBACK_EXPR_2, CALLBACK_VALUE_2")], ...
def create_expression_callback():
    count = [0]  # Using a list to store the count as a mutable object

    def callback(node):
        count[0] += 1
        return c_ast.ExprList([c_ast.ID(f'CALLBACK_EXPR_{count[0]}'), c_ast.ID(f'CALLBACK_VALUE_{count[0]}')])

    return callback


# Produces [ID("CALLBACK_1")], [ID("CALLBACK_2")], ...
def create_statement_callback():
    count = [0]  # Using a list to store the count as a mutable object

    def callback(node):
        count[0] += 1
        return c_ast.ExprList([c_ast.ID(f'CALLBACK_{count[0]}')])

    return callback

# Produces METHOD("void CALLBACK_1() { }"), METHOD("void CALLBACK_2() { }")
def create_method_callback(): 
    count = [0]  # Using a list to store the count as a mutable object

    def callback(node):
        count[0] += 1
        src = f'void CALLBACK_{count[0]}() {{}}'
        root = parse(src)
        return find_node_of_type(root, c_ast.FuncDecl)

    return callback

class TestFindVisitor(unittest.TestCase):
    def test_find_nothing(self):  
        c1 = c_ast.Constant(type='int', value='1')
        visitor = FindVisitor(lambda n: 0)

        result = visitor.visit(c1)

        self.assertEqual(result, None)

    def test_find_first_constant(self): 
        c1 = c_ast.Constant(type='int', value='1')
        c2 = c_ast.Constant(type='int', value='5')
        b1 = c_ast.BinaryOp(op='+', left = c1, right= c2)
        
        visitor = FindVisitor(lambda n: isinstance(n, c_ast.Constant))
        result = visitor.visit(b1)

        self.assertEqual(result, c1)
    
    def test_find_second_constant(self): 
        c1 = c_ast.Constant(type='int', value='1')
        c2 = c_ast.Constant(type='int', value='5')
        b1 = c_ast.BinaryOp(op='+', left = c1, right= c2)
        
        visitor = FindVisitor(lambda n: isinstance(n, c_ast.Constant), skip=1)
        result = visitor.visit(b1)

        self.assertEqual(result, c2)


class TestParentVisitor(unittest.TestCase):
    def test_root_parent(self):  
        c1 = c_ast.Constant(type='int', value='1')

        pv = ParentVisitor()
        pv.visit(c1)

        self.assertEqual(c1.data['parent'], None)

    def test_child_parent(self): 
        c1 = c_ast.Constant(type='int', value='1')
        c2 = c_ast.Constant(type='int', value='5')
        b1 = c_ast.BinaryOp(op='+', left = c1, right= c2)

        pv = ParentVisitor()
        pv.visit(b1)

        self.assertEqual(b1.data['parent'], None)
        self.assertEqual(c1.data['parent'], b1)
        self.assertEqual(c2.data['parent'], b1)


class TestLocationVisitor(unittest.TestCase): 
    def get_substring_location(self, text, substring, skip_matches=0):
        matches = re.finditer(re.escape(substring), text)
        match = None

        for _ in range(skip_matches + 1):
            try:
                match = next(matches)
            except StopIteration:
                raise Exception('substring not found')

        start_index = match.start()
        end_index = match.end()

        start_line = text.count('\n', 0, start_index) + 1
        start_col = start_index - text.rfind('\n', 0, start_index)
        end_line = text.count('\n', 0, end_index) + 1
        end_col = end_index - text.rfind('\n', 0, end_index)
        return [start_line, start_col, end_line, end_col]

    def _test_location(self, root_src, node_src, node_type, skip_substrings = 0, skip_nodes = 0): 
        # Arrange
        root = parse(root_src)
        node = find_node_of_type(root, node_type, skip_nodes)
        expected_location = self.get_substring_location(root_src, node_src, skip_substrings)

        # Act
        LocationVisitor().visit(root)

        # Assert
        self.assertListEqual(expected_location, node.data['location'])

    def test_binary_location(self):
        src = '''
            int main() {
                return 5 * 6;
            }
        '''
        self._test_location(src, '5 * 6', c_ast.BinaryOp)

    def test_constant_location(self):
        src = '''
            int main() {
                return 578;
            }
        '''
        self._test_location(src, '578', c_ast.Constant)

    def test_decl_without_init(self):
        src = '''
            int main() {
                int i;
            }
        '''
        self._test_location(src, 'int i;', c_ast.Decl, skip_nodes=1)

    def test_decl_with_init(self):
        src = '''
            int main() {
                int i = 5;
            }
        '''
        self._test_location(src, 'int i = 5;', c_ast.Decl, skip_nodes=1)

    def test_funccall_without_parameters(self):
        src = '''
            int main() {
                return func();
            }
        '''
        self._test_location(src, 'func()', c_ast.FuncCall)

    def test_funccall_with_parameter(self):
        src = '''
            int main() {
                return func("Hello");
            }
        '''
        self._test_location(src, 'func("Hello")', c_ast.FuncCall)

    def test_funccall_with_multiple_parameters(self):
        src = '''
            int main() {
                return func("Hello", "World");
            }
        '''
        self._test_location(src, 'func("Hello", "World")', c_ast.FuncCall)
        
    def test_id_location(self):
        src = '''
            int main() {
                int xyz = 5;
                return xyz;
            }
        '''
        # xyz will match both decl and id, so skip_substrings=1 is needed to get xyz in "return xyz"
        self._test_location(src, 'xyz', c_ast.ID, skip_substrings = 1)


class TestDeclarationVisitor(unittest.TestCase): 
    def test_single_variable(self):
        src = '''
            int main() {
                int i = 5;
                return i;
            }
        '''
        root = parse(src)
        declaration = find_decl_with_name(root,  'i')
        identifier = find_id_with_name(root, 'i')
        
        DeclarationVisitor().visit(root)

        self.assertEqual(identifier.data['declaration'], declaration)

    def test_multiple_variables(self):
        src = '''
            int main() {
                int i = 5;
                int j = 6;
                return i + j;
            }
        '''
        root = parse(src)
        declaration1 = find_decl_with_name(root,  'i')
        declaration2 = find_decl_with_name(root,  'j')
        identifier1 = find_id_with_name(root,  'i')
        identifier2 = find_id_with_name(root,  'j')
        
        DeclarationVisitor().visit(root)

        self.assertEqual(identifier1.data['declaration'], declaration1)
        self.assertEqual(identifier2.data['declaration'], declaration2)

    def test_shadowed_variables(self):
        src = '''
            int main() {
                int i = 5;
                {
                    int i = 7;
                    return i;
                }
            }
        '''
        root = parse(src)
        declaration = find_decl_with_name(root,  'i', skip_matches=1)
        identifier = find_id_with_name(root,  'i')
        
        DeclarationVisitor().visit(root)

        self.assertEqual(identifier.data['declaration'], declaration)

    def test_previously_shadowed_variables(self):
        src = '''
            int main() {
                int i = 5;
                {
                    int i = 7;
                }
                return i;
            }
        '''
        root = parse(src)
        declaration = find_decl_with_name(root,  'i')
        identifier = find_id_with_name(root,  'i')
        
        DeclarationVisitor().visit(root)

        self.assertEqual(identifier.data['declaration'], declaration)


class TestExpressionTypeVisitor(unittest.TestCase): 
    def _test_binaryop_constant(self, type, src): 
        """ Only handles binary operations consisting of constants
        """
        root_src = f'''
            {type} main() {{
                return {src};
            }}
        '''
        root = parse(root_src)
        binary_op = find_node_of_type(root,  c_ast.BinaryOp)
        
        ExpressionTypeVisitor().visit(root)

        self.assertEqual(binary_op.data['expression-type'], type)

    def test_binaryop_int_addition(self): 
        self._test_binaryop_constant('int', '5 + 6')
    
    def test_binaryop_int_multiplication(self): 
        self._test_binaryop_constant('int', '5 * 7')
    
    def test_binaryop_int_equals(self): 
        self._test_binaryop_constant('int', '5 == 7')

    def test_binaryop_string_equals(self): 
        self._test_binaryop_constant('int', '"yes" == "no"')

    def _test_constant(self, type, src): 
        root_src = f'''
            {type} main() {{
                return {src};
            }}
        '''
        root = parse(root_src)
        const = find_node_of_type(root,  c_ast.Constant)
        
        ExpressionTypeVisitor().visit(root)

        self.assertEqual(const.data['expression-type'], type)

    def test_constant_int(self):
        self._test_constant('int', '5')
    
    def test_constant_string(self):
        self._test_constant('char*', '"Hello there!"')

    def _test_assignment(self, type, name, expr): 
        src = f'''
            {type} main() {{
                {type} {name};
                return {expr};
            }}
        '''
        root = parse(src)
        binary_op = find_node_of_type(root,  c_ast.Assignment)
        
        ExpressionTypeVisitor().visit(root)

        self.assertEqual(binary_op.data['expression-type'], type)

    def test_assignment_regular(self):
        self._test_assignment('int', 'i', 'i = 5');

    def test_assignment_addition(self):
        self._test_assignment('int', 'i', 'i += 5');

    def test_id(self):
        src = '''
            int main() {
                int i = 5;
                return i;
            }
        '''
        root = parse(src)
        identifier = find_id_with_name(root,  'i')
        
        DeclarationVisitor().visit(root)
        ExpressionTypeVisitor().visit(root)

        self.assertEqual(identifier.data['expression-type'], 'int')

# Transforms any child nodes identified through introspection
# Please note, the transformation may not always produce a valid result,
# but should work well enough in most cases to avoid having to implement 
# a transformation per note type
class TestNodeTransformation(unittest.TestCase): 
    def test_apply_identity(self):
        transformation = NodeTransformation(
            fail, 
            create_identity_callback())

        src = "\n".join([
            'int main()',
            '{',
            '  for (int i = 0; i < 5; i++)',
            '    printf("%d", i);',
            '',
            '}'
        ])
        root = parse(src)
        output = transformation.apply(root)

        self.assertEqual(
            stringify(output).strip(), 
            src
        )

    def test_apply_return(self): 
        transformation = NodeTransformation(
            fail, 
            create_expression_callback())
        
        input = c_ast.Return(c_ast.ID("a"))
        output = transformation.apply(input)

        self.assertEqual(
            stringify(output), 
            'return CALLBACK_EXPR_1, CALLBACK_VALUE_1;'
        )
    
    def test_apply_for_loop(self): 
        transformation = NodeTransformation(
            fail, 
            create_statement_callback())
        
        src = '''
            int main() {
                for(int i = 0; i < 5; i++) 
                    printf("%d", f);
            }
        '''
        root = parse(src)
        input = find_node_of_type(root, c_ast.For)
        output = transformation.apply(input)

        self.assertEqual(
            stringify(output).strip(), 
            'for (CALLBACK_2; CALLBACK_1; CALLBACK_3)\n  CALLBACK_4;'
        )


class TestIdTransformation(unittest.TestCase):
    def test_apply_id(self):
        transformation = IdTransformation(
            lambda t: c_ast.ID("temp0"),
            fail
        )

        input = c_ast.ID("a", data={ "expression-type": "int", "location": [0, 1, 2, 3] })
        output = transformation.apply(input)

        self.assertEqual(
            stringify(output), 
            'temp0 = a, notify("a=eval;t=int;l=[0,1,2,3]", &temp0), temp0'
        )


class TestBinaryOpTransformation(unittest.TestCase): 
    def test_apply_left_right_constant(self): 
        transformation = BinaryOpTransformation(
            lambda t: c_ast.ID("temp0"),
            fail
        )

        input = c_ast.BinaryOp(
            '+', 
            c_ast.Constant('int', 1), 
            c_ast.Constant('int', 2), 
            data={ "expression-type": "int", "location": [0, 1, 2, 3] })
        output = transformation.apply(input)

        self.assertEqual(
            stringify(output), 
            'temp0 = 1 + 2, notify("a=eval;t=int;l=[0,1,2,3]", &temp0), temp0'
        )

    def test_apply_right_constant(self): 
        transformation = BinaryOpTransformation(
            lambda t: c_ast.ID("temp0"),
            create_expression_callback()
        )

        input = c_ast.BinaryOp(
            '+', 
            c_ast.ID('a'), 
            c_ast.Constant('int', 2), 
            data={ "expression-type": "int", "location": [0, 1, 2, 3] })
        output = transformation.apply(input)

        self.assertEqual(
            stringify(output), 
            'CALLBACK_EXPR_1, temp0 = CALLBACK_VALUE_1 + 2, notify("a=eval;t=int;l=[0,1,2,3]", &temp0), temp0'
        )
        # a + 2  
        # temp0 = a, notify("a=eval;t=int;l=[0,1,2,3]", &temp0), temp1 = temp0 + 2, notify("a=eval;t=int;l=[0,1,2,3]", &temp1), temp1

    def test_apply_left_constant(self): 
        transformation = BinaryOpTransformation(
            lambda t: c_ast.ID("temp0"),
            create_expression_callback()
        )

        input = c_ast.BinaryOp(
            '+', 
            c_ast.Constant('int', 1), 
            c_ast.ID('b'), 
            data={ "expression-type": "int", "location": [0, 1, 2, 3] })
        output = transformation.apply(input)

        self.assertEqual(
            stringify(output), 
            'CALLBACK_EXPR_1, temp0 = 1 + CALLBACK_VALUE_1, notify("a=eval;t=int;l=[0,1,2,3]", &temp0), temp0'
        )

    def test_apply_no_constants(self): 
        transformation = BinaryOpTransformation(
            lambda t: c_ast.ID("temp0"),
            create_expression_callback()
        )

        input = c_ast.BinaryOp(
            '+', 
            c_ast.ID('a'), 
            c_ast.ID('b'), 
            data={ "expression-type": "int", "location": [0, 1, 2, 3] })
        output = transformation.apply(input)

        self.assertEqual(
            stringify(output), 
            'CALLBACK_EXPR_1, CALLBACK_EXPR_2, temp0 = CALLBACK_VALUE_1 + CALLBACK_VALUE_2, notify("a=eval;t=int;l=[0,1,2,3]", &temp0), temp0'
        )


class TestAssignmentTransformation(unittest.TestCase): 
    def test_apply_constant(self): 
        transformation = AssignmentTransformation(
            lambda t: c_ast.ID("temp0"),
            fail
        )

        input = c_ast.Assignment(
            '=', 
            c_ast.ID("a"), 
            c_ast.Constant("int", 123), 
            data={ "expression-type": "int", "location": [0, 1, 2, 3] })
        output = transformation.apply(input)

        self.assertEqual(
            stringify(output), 
            'temp0 = (a = 123), notify("a=assign;t=int;i=a", &temp0), temp0'
        )
    
    def test_apply_non_constant(self): 
        transformation = AssignmentTransformation(
            lambda t: c_ast.ID("temp0"),
            create_expression_callback()
        )

        input = c_ast.Assignment(
            '=', 
            c_ast.ID("a"), 
            c_ast.ID("b"), 
            data={ "expression-type": "int", "location": [0, 1, 2, 3] })
        output = transformation.apply(input)

        self.assertEqual(
            stringify(output), 
            'CALLBACK_EXPR_1, temp0 = (a = CALLBACK_VALUE_1), notify("a=assign;t=int;i=a", &temp0), temp0'
        )


class TestDeclTransformation(unittest.TestCase): 
    def test_apply_non_initialized(self): 
        transformation = DeclTransformation(
            lambda t: c_ast.ID("temp0"),
            fail
        )

        src = '''
            int main() {
                int abc;
            }
        '''
        root = parse(src)
        input = find_node_of_type(root, c_ast.Decl, skip_matches=1)
        input.data = { "expression-type": "int" }
        output = transformation.apply(input)

        self.assertEqual(
            stringify(output), 
            'int abc = (notify("a=decl;t=int;i=abc", &temp0), temp0)'
        )

    def test_apply_constant_initialized(self): 
        transformation = DeclTransformation(
            lambda t: c_ast.ID("temp0"),
            fail
        )

        src = '''
            int main() {
                int abc = 5;
            }
        '''
        root = parse(src)
        input = find_node_of_type(root, c_ast.Decl, skip_matches=1)
        input.data = { "expression-type": "int" }
        output = transformation.apply(input)

        self.assertEqual(
            stringify(output), 
            'int abc = (temp0 = 5, notify("a=decl;t=int;i=abc", &temp0), temp0)'
        )
    
    def test_apply_non_constant_initialized(self): 
        transformation = DeclTransformation(
            lambda t: c_ast.ID("temp0"),
            create_expression_callback()
        )

        src = '''
            int main() {
                int abc = i;
            }
        '''
        root = parse(src)
        input = find_node_of_type(root, c_ast.Decl, skip_matches=1)
        input.data = { "expression-type": "int" }
        output = transformation.apply(input)

        self.assertEqual(
            stringify(output), 
            'int abc = (CALLBACK_EXPR_1, temp0 = CALLBACK_VALUE_1, notify("a=decl;t=int;i=abc", &temp0), temp0)'
        )


class TestFuncDef(unittest.TestCase): 
    def test_apply_single_statement(self): 
        transformation = FuncDefTransformation(
            fail, 
            create_single_declaration,
            create_statement_callback()
        )

        src = '''
            int main() {
                int a = 4 * 4;
            }
        '''
        root = parse(src)
        input = find_node_of_type(root, c_ast.FuncDef)
        output = transformation.apply(input)
        
        self.assertEqual(
            stringify(output).strip(),
            'int main()\n{\n  int temp0;\n  CALLBACK_1;\n}'
        )

    def test_apply_multiple_statement(self): 
        transformation = FuncDefTransformation(
            fail, 
            create_multiple_declarations,
            create_statement_callback()
        )

        src = '''
            int main() {
                int a = 4 * 4;
                int b = 5 * 5;
            }
        '''
        root = parse(src)
        input = find_node_of_type(root, c_ast.FuncDef)
        output = transformation.apply(input)
        
        self.assertEqual(
            stringify(output).strip(),
            'int main()\n{\n  int temp0;\n  int temp1;\n  CALLBACK_1;\n  CALLBACK_2;\n}'
        )


class TestFileAstTransformation(unittest.TestCase):
    def test_apply_without_includes(self): 
        transformation = FileAstTransformation(
            fail, 
            create_method_callback()
        )

        src = '''
            int main() { }
        '''
        input = parse(src)
        output = transformation.apply(input)

        self.assertEqual(
            stringify(output).strip(),
            'void notify(char *metadata, void *data);\nvoid CALLBACK_1();'
        )
        

class TestFlattenVisitor(unittest.TestCase):
    def _test_flatten_node(self, node, src_expr, src_variables):
        root = parse('void func() { }')
        compound = find_node_of_type(root, c_ast.Compound)
        compound.block_items = [node]

        fv = FlattenVisitor()
        fv.visit(root)

        actual_src_expr = c_generator.CGenerator().visit(compound.block_items[-1])
        actual_src_variables = [c_generator.CGenerator().visit(x) for x in compound.block_items[:-1]]

        self.assertEqual(actual_src_expr, src_expr)
        self.assertListEqual(actual_src_variables, src_variables)

    def test_flatten_constant(self):  
        c1 = c_ast.Constant(type='int', value='5', data={'expression-type': 'int'})

        self._test_flatten_node(
            c1, 
            'temp0 = 5, temp0', 
            ['int temp0'])
        
    def test_flatten_id(self):  
        i1 = c_ast.ID(name='i', data = {'expression-type': 'char'})

        self._test_flatten_node(
            i1, 
            'temp0 = i, temp0', 
            ['char temp0'])
        
    def test_flatten_binaryop_with_constants(self): 
        c1 = c_ast.Constant(type='int', value='1', data = {'expression-type': 'int'})
        c2 = c_ast.Constant(type='int', value='5', data = {'expression-type': 'int'})
        b1 = c_ast.BinaryOp(op='+', left=c1, right=c2, data = {'expression-type': 'int'})

        self._test_flatten_node(
            b1, 
            'temp0 = 1 + 5, temp0', 
            ['int temp0'])

    def test_flatten_binaryop_with_left_constant(self): 
        c1 = c_ast.Constant(type='int', value='2')
        i1 = c_ast.ID(name = 'j', data = {'expression-type': 'int'})
        b1 = c_ast.BinaryOp(op='*', left=c1, right=i1, data = {'expression-type': 'int'})

        self._test_flatten_node(
            b1, 
            'temp0 = j, temp1 = 2 * temp0, temp1', 
            ['int temp0', 'int temp1'])

    def test_flatten_binaryop_with_right_constant(self): 
        i1 = c_ast.ID(name = 'i', data = {'expression-type': 'int'})
        c1 = c_ast.Constant(type='int', value='67')
        b1 = c_ast.BinaryOp(op='-', left=i1, right=c1, data = {'expression-type': 'int'})

        self._test_flatten_node(
            b1, 
            'temp0 = i, temp1 = temp0 - 67, temp1', 
            ['int temp0', 'int temp1'])

    def test_flatten_binaryop_without_constants(self): 
        i1 = c_ast.ID(name = 'i', data = {'expression-type': 'int'})
        i2 = c_ast.ID(name = 'j', data = {'expression-type': 'int'})
        b1 = c_ast.BinaryOp(op='%', left=i1, right=i2, data = {'expression-type': 'int'})

        self._test_flatten_node(
            b1, 
            'temp0 = i, temp1 = j, temp2 = temp0 % temp1, temp2', 
            ['int temp0', 'int temp1', 'int temp2'])

    def test_flatten_decl_without_init(self): 
        src = '''
            int main() {
                int i;
            }
        '''
        root = parse(src)
        node = find_decl_with_name(root, 'i')
        node.data['expression-type'] = 'int'

        self._test_flatten_node(
            node, 
            'int i = (temp0, temp0)', 
            ['int temp0'])
        
    def test_flatten_decl_with_init(self): 
        src = '''
            int main() {
                int i = 5;
            }
        '''
        root = parse(src)
        c1 = find_node_of_type(root, c_ast.Constant)
        d1 = find_decl_with_name(root, 'i')
        c1.data['expression-type'] = 'int'
        d1.data['expression-type'] = 'int'

        self._test_flatten_node(
            d1, 
            'int i = (temp0 = 5, temp0)', 
            ['int temp0'])
    
    def test_flatten_funccall_void(self): 
        f1 = c_ast.FuncCall(c_ast.ID('f'), None, data={'expression-type': 'void'})

        self._test_flatten_node(
            f1, 
            'f()', 
            [])

    def test_flatten_funccall_without_parameters(self): 
        f1 = c_ast.FuncCall(c_ast.ID('f'), None, data={'expression-type': 'float'})

        self._test_flatten_node(
            f1, 
            'temp0 = f(), temp0', 
            ['float temp0'])
    
    def test_flatten_funccall_with_constant_arguments(self): 
        c1 = c_ast.Constant(type='int', value='1', data = {'expression-type': 'int'})
        c2 = c_ast.Constant(type='int', value='2', data = {'expression-type': 'int'})
        f1 = c_ast.FuncCall(
            c_ast.ID('f'), 
            c_ast.ExprList([c1, c2]),
            data={'expression-type': 'double'})

        self._test_flatten_node(
            f1, 
            'temp0 = f(1, 2), temp0', 
            ['double temp0'])
    
    def test_flatten_funccall_with_non_constant_argument(self): 
        i1 = c_ast.ID(name = 'i', data = {'expression-type': 'int'})
        f1 = c_ast.FuncCall(
            c_ast.ID('f'), 
            c_ast.ExprList([i1]),
            data={'expression-type': 'short'})

        self._test_flatten_node(
            f1, 
            'temp0 = i, temp1 = f(temp0), temp1', 
            ['int temp0', 'short temp1'])
    
    def test_flatten_funccall_with_non_constant_arguments(self): 
        i1 = c_ast.ID(name = 'i', data = {'expression-type': 'int'})
        i2 = c_ast.ID(name = 'j', data = {'expression-type': 'int'})
        f1 = c_ast.FuncCall(
            c_ast.ID('f'), 
            c_ast.ExprList([i1, i2]),
            data={'expression-type': 'short'})

        self._test_flatten_node(
            f1, 
            'temp0 = i, temp1 = j, temp2 = f(temp0, temp1), temp2', 
            ['int temp0', 'int temp1', 'short temp2'])
    
    def test_flatten_funccall_with_mixed_arguments(self): 
        c1 = c_ast.Constant(type='int', value='45', data = {'expression-type': 'int'})
        i1 = c_ast.ID(name = 'i', data = {'expression-type': 'int'})
        f1 = c_ast.FuncCall(
            c_ast.ID('f'), 
            c_ast.ExprList([c1, i1]),
            data={'expression-type': 'short'})

        self._test_flatten_node(
            f1, 
            'temp0 = i, temp1 = f(45, temp0), temp1', 
            ['int temp0', 'short temp1'])
    
    def test_flatten_assignment_with_constant(self): 
        i1 = c_ast.ID(name = 'i', data = {'expression-type': 'int'})
        c1 = c_ast.Constant(type='short', value='2', data={'expression-type': 'short'})
        b1 = c_ast.Assignment('=', i1, c1, data = {'expression-type': 'int'})

        self._test_flatten_node(
            b1,
            'temp0 = (i = 2), temp0', 
            ['int temp0'])
        
    def test_flatten_assignment_with_non_constant(self): 
        i1 = c_ast.ID(name = 'i', data = {'expression-type': 'int'})
        i2 = c_ast.ID(name = 'j', data = {'expression-type': 'short'})
        b1 = c_ast.Assignment('=', i1, i2, data = {'expression-type': 'int'})

        self._test_flatten_node(
            b1,
            'temp0 = j, temp1 = (i = temp0), temp1', 
            ['short temp0', 'int temp1'])

    def test_flatten_return_with_constant(self):
        c1 = c_ast.Constant(type='int', value = '5', data={ 'expression-type': 'int' })
        r1 = c_ast.Return(c1)

        self._test_flatten_node(
            r1,
            'return temp0 = 5, temp0;',
            ['int temp0'])


class TestNotifyCreator(unittest.TestCase): 
    def test_location(self): 
        # Tests serialization of LocationVisitor data
        input = { "location": [0, 1, 2, 3] }
        
        actual = NotifyCreator().create(input)
        expected = ["l=[0,1,2,3]"]

        self.assertEqual(actual, expected)

    def test_expression_type(self): 
        # Tests serilization of ExpressionTypeVisitor data 
        input = { "expression-type": "string" }

        actual = NotifyCreator().create(input)
        expected = ["t=string"]

        self.assertEqual(actual, expected)

    def test_combination(self): 
        # NotifyCreator does not guarantee order
        input = { 
            "expression-type": "string*",
            "location": [0, 1, 2, 3]
        }

        actual = NotifyCreator().create(input)
        expected1 = ["t=string*;l=[0,1,2,3]"]
        expected2 = ["l=[0,1,2,3];t=string*"]

        self.assertTrue(actual == expected1 or actual == expected2);


class TestNotifyVisitor(unittest.TestCase):
    def _test_notify_node(self, src, expected, times = 1):

        root = parse(src);
        exprlist = find_node_of_type(root, c_ast.ExprList)
        if exprlist is not None and len(exprlist.exprs) > 0:
            for expr in exprlist.exprs[:-1]: 
                expr.data = {'flattened': True }

        creator = ConstantNotifyInfoCreator(times)
        visitor = NotifyVisitor(creator)
        visitor.visit(root)

        root_src = c_generator.CGenerator().visit(root)
        self.assertEqual(root_src.strip(), expected.strip())
    
    def test_notify_declaration(self):
        src = '''
int main() {
}'''
        expected = '''
void notify(char *metadata, void *data);
int main()
{
}'''
        root = parse(expected)
        self._test_notify_node(src, expected)

    def test_notify_undefined(self):
        src = '''
int main() {
  int temp0;
  return temp0, temp0;
}'''
        expected = '''
void notify(char *metadata, void *data);
int main()
{
  int temp0;
  return temp0, notify("CONSTANT0", &temp0), temp0;
}'''
        self._test_notify_node(src, expected)

    def test_notify_undefined_doubled(self):
        src = '''
int main() {
  int temp0;
  return temp0, temp0;
}'''
        expected = '''
void notify(char *metadata, void *data);
int main()
{
  int temp0;
  return temp0, notify("CONSTANT0", &temp0), notify("CONSTANT0", &temp0), temp0;
}'''
        self._test_notify_node(src, expected, 2)

    def test_notify_constant(self): 
        src = '''
int main() {
  int temp0;
  return temp0 = 5, temp0;
}'''
        expected = '''
void notify(char *metadata, void *data);
int main()
{
  int temp0;
  return temp0 = 5, notify("CONSTANT0", &temp0), temp0;
}'''
        self._test_notify_node(src, expected)

    def test_notify_constant_trippled(self): 
        src = '''
int main() {
  int temp0;
  return temp0 = 5, temp0;
}'''
        expected = '''
void notify(char *metadata, void *data);
int main()
{
  int temp0;
  return temp0 = 5, notify("CONSTANT0", &temp0), notify("CONSTANT0", &temp0), notify("CONSTANT0", &temp0), temp0;
}'''
        self._test_notify_node(src, expected, 3)

    def test_notify_binary(self): 
        src = '''
int main() {
  int temp0;
  int temp1;
  return temp0 = j, temp1 = 2 * temp0, temp1;
}'''
        expected = '''
void notify(char *metadata, void *data);
int main()
{
  int temp0;
  int temp1;
  return temp0 = j, notify("CONSTANT0", &temp0), temp1 = 2 * temp0, notify("CONSTANT1", &temp1), temp1;
}'''
        self._test_notify_node(src, expected) 

    def test_notify_binary_doubled(self): 
        src = '''
int main() {
  int temp0;
  int temp1;
  return temp0 = j, temp1 = 2 * temp0, temp1;
}'''
        expected = '''
void notify(char *metadata, void *data);
int main()
{
  int temp0;
  int temp1;
  return temp0 = j, notify("CONSTANT0", &temp0), notify("CONSTANT0", &temp0), temp1 = 2 * temp0, notify("CONSTANT1", &temp1), notify("CONSTANT1", &temp1), temp1;
}'''
        self._test_notify_node(src, expected, 2) 