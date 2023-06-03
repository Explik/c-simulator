import unittest
import re
from pycparser import c_ast, c_parser
from modules.visitors import FindVisitor, ParentVisitor, LocationVisitor, DeclarationVisitor

def parse(src): 
    parser = c_parser.CParser(
                lex_optimize=False,
                yacc_debug=True,
                yacc_optimize=False,
                yacctab='yacctab')
    return parser.parse(src)

def find_node(root, predicate, skip_matches = 0): 
    return FindVisitor(predicate, skip_matches).visit(root)
def find_node_of_type(root, type, skip_matches = 0): 
    return find_node(root, lambda n: isinstance(n, type), skip_matches)
def find_decl_with_name(root, name, skip_matches = 0):
    return find_node(root, lambda n: isinstance(n, c_ast.Decl) and n.name == name, skip_matches)
def find_id_with_name(root, name, skip_matches = 0):
    return find_node(root, lambda n: isinstance(n, c_ast.ID) and n.name == name, skip_matches)


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
        self._test_location(src, 'int i;', c_ast.Decl)

    def test_decl_with_init(self):
        src = '''
            int main() {
                int i = 5;
            }
        '''
        self._test_location(src, 'int i = 5;', c_ast.Decl)

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
