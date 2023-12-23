import unittest
from source_nodes import SourceText, SourceToken, SourceNode

class SourceTextTests(unittest.TestCase):
    def test_equality(self): 
        source_text_1 = SourceText.create(None, None, "value")
        source_text_2 = SourceText.create(None, None, "value")

        self.assertEquals(source_text_1, source_text_2)

    def test_non_equality(self): 
        source_text_1 = SourceText.create(None, None, "value_1")
        source_text_2 = SourceText.create(None, None, "value_2")

        self.assertNotEquals(source_text_1, source_text_2)

    def test_to_string(self):
        source_text = SourceText.create(None, None, "value")

        self.assertEquals(f"{source_text}", "value")


class SourceTokenTests(unittest.TestCase):
    def test_create_increments_id(self):
        source_token_1 = SourceToken.create(None, None, "value_1", None)
        source_token_2 = SourceToken.create(None, None, "value_2", None)

        self.assertEquals(source_token_1.id + 1, source_token_2.id)
    
    def test_copy_copies_id(self):
        source_token_1 = SourceToken.create(None, None, "value_1", None)
        source_token_2 = SourceToken.copy(source_token_1)

        self.assertEquals(source_token_1.id, source_token_2.id)
    
    def test_equality(self): 
        source_token_1 = SourceToken.create(None, None, "value_1", None)
        source_token_2 = SourceToken.copy(source_token_1)

        self.assertEquals(source_token_1, source_token_2)

    def test_non_equality(self): 
        source_token_1 = SourceToken.create(None, None, "value_1", None)
        source_token_2 = SourceToken.create(None, None, "value_2", None)

        self.assertNotEquals(source_token_1, source_token_2)

    def test_to_string(self): 
        source_token = SourceToken.create(None, None, "value", None)

        self.assertEquals(f"{source_token}", "value")

class SourceNodeTests(unittest.TestCase):
    def test_create_function(self):
        token_1 = SourceToken.create(1, 3, "value_1", None)
        token_2 = SourceToken.create(5, 8, "value_2", None)
        node = SourceNode.create(dict(), [token_1, token_2])

        self.assertIsNotNone(node.id)
        self.assertEqual(node.start_index, 1)
        self.assertEqual(node.end_index, 8)
        self.assertEqual(type(node.node), dict)

    def test_create_from_template_function_1(self):
        node = SourceNode.create_from_template(
            "{0}",
            [SourceText.create(None, None, "a")]
        )
        self.assertEquals(f"{node}", "a")

    def test_create_from_template_function_2(self):
        node = SourceNode.create_from_template(
            "{1} + {0}", 
            [
                SourceText.create(None, None, "a"),
                SourceText.create(None, None, "b")
            ]
        )
        self.assertEquals(f"{node}", "b + a") 

    def test_create_from_template_function_3(self):
        node = SourceNode.create_from_template(
            "{2}, {1}, {0}", 
            [
                SourceText.create(None, None, "a"),
                SourceText.create(None, None, "b"),
                SourceText.create(None, None, "c")
            ]
        )
        self.assertEquals(f"{node}", "c, b, a") 

    def test_copy_function(self): 
        token_1 = SourceToken.create(1, 3, "value_1", None)
        token_2 = SourceToken.create(5, 8, "value_2", None)
        node_1 = SourceNode.create(dict(), [token_1, token_2])
        node_2 = SourceNode.copy(node_1)

        self.assertIsNotNone(node_2.id)
        self.assertEqual(node_2.start_index, 1)
        self.assertEqual(node_2.end_index, 8)
        self.assertEqual(type(node_2.node), dict)

    def test_get_children(self):
        child_1 = SourceNode.create(None, [])
        token_1 = SourceToken.create(None, None, "value_1", None)
        token_2 = SourceToken.create(None, None, "value_2", None)
        child_2 = SourceNode.create(None, [])
        parent = SourceNode.create(None, [child_1, token_1, token_2, child_2])

        self.assertListEqual(parent.get_children(), [child_1, child_2])

    def test_get_tokens(self):
        child_1 = SourceNode.create(None, [])
        token_1 = SourceToken.create(None, None, "value_1", None)
        token_2 = SourceToken.create(None, None, "value_2", None)
        child_2 = SourceNode.create(None, [])
        parent = SourceNode.create(None, [child_1, token_1, token_2, child_2])

        self.assertListEqual(parent.get_tokens(), [token_1, token_2])

    def test_create_increments_id(self):
        source_token_1 = SourceNode.create(None, [])
        source_token_2 = SourceNode.create(None, [])

        self.assertEquals(source_token_1.id + 1, source_token_2.id)
    
    def test_copy_copies_id(self):
        source_token_1 = SourceNode.create(None, [])
        source_token_2 = SourceNode.copy(source_token_1)

        self.assertEquals(source_token_1.id, source_token_2.id)

    def test_equality(self): 
        source_token_1 = SourceNode.create(None, [])
        source_token_2 = SourceNode.copy(source_token_1)

        self.assertEquals(source_token_1, source_token_2)

    def test_non_equality(self): 
        source_token_1 = SourceNode.create(None, [])
        source_token_2 = SourceNode.create(None, [])

        self.assertNotEquals(source_token_1, source_token_2)

    def test_to_string(self): 
        source_node = SourceNode.create(
            None, 
            [
                SourceText.create(None, None, "i"), 
                SourceText.create(None, None, "++")
            ]
        )
        self.assertEquals(f"{source_node}", "i++")

    def test_recursive_to_string(self): 
        source_node = SourceNode.create(
            None, 
            [
                SourceNode.create(None, [SourceText.create(None, None, "a")]),
                SourceText.create(None, None, " + "), 
                SourceNode.create(None, [SourceText.create(None, None, "b")]),
            ]
        )
        self.assertEquals(f"{source_node}", "a + b")


