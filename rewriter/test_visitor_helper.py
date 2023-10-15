import unittest
from pycparser import c_ast, c_generator
from visitors_helper import createNotify

def stringify(node): 
   return c_generator.CGenerator().visit(node)

class TestHelpers(unittest.TestCase):
    def test_create_notify_single(self):  
        notify_node = createNotify("t=int", c_ast.ID("id"))
        notify_src = stringify(notify_node)

        self.assertEqual(notify_src, "notify(\"t=int\", &id)")
    
    def test_create_notify_multiple(self):  
        notify_node = createNotify(["t=int", "l=[0,1,2,3]"], c_ast.ID("id"))
        notify_src = stringify(notify_node)

        self.assertEqual(notify_src, "notify(\"t=int;l=[0,1,2,3]\", &id)")
    

