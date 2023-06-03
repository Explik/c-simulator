import unittest
from pycparser import c_ast
from modules.visitors import FindVisitor, ParentVisitor

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
