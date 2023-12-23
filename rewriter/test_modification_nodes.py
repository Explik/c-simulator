import unittest
from modification_nodes import ConstantNode, TemplatedNode, TemplatedReplaceNode, template_replace_node
from source_nodes import SourceNode

class TestFunctions(unittest.TestCase):
    def test_template_replace_node_1_args(self):
        # f(1) -> Exception
        input = [
            ConstantNode("1")
        ]
        with self.assertRaises(Exception):
            template_replace_node(
                "{0}, {1}", 
                "{0}, {1}",
                SourceNode(), 
                *input
            )

    def test_template_replace_node_2_args(self):
        # f(1, 2) -> (1, 2)
        input = [
            ConstantNode("1"),
            ConstantNode("2"),
        ]
        output = template_replace_node(
            "{0}, {1}", 
            "{0}, {1}",
            SourceNode(), 
            *input
        )
        output_children = output.get_children()
        
        self.assertEqual(type(output), TemplatedReplaceNode)
        self.assertEqual(output.template, "{0}, {1}")
        self.assertEqual(output_children[0], input[0])
        self.assertEqual(output_children[1], input[1])

    def test_template_replace_node_3_args(self):
        # f(1, 2, 3) -> ((1, 2), 3)
        input = [
            ConstantNode("1"),
            ConstantNode("2"),
            ConstantNode("3")
        ]
        output = template_replace_node(
            "{0}, {1}", 
            "{0}, {1}",
            SourceNode(), 
            *input
        )
        output_children = output.get_children()
        output_grandchildren = output_children[0].get_children()
        
        self.assertEqual(type(output), TemplatedReplaceNode)
        self.assertEqual(type(output_children[0]), TemplatedNode)

        self.assertEqual(output.template, "{0}, {1}")
        self.assertEqual(output_children[0].template, "{0}, {1}")

        self.assertEqual(output_grandchildren[0], input[0])
        self.assertEqual(output_grandchildren[1], input[1])
        self.assertEqual(output_children[1], input[2])
    
    def test_template_replace_node_4_args(self):
        # f(1, 2, 3, 4) -> (((1, 2), 3), 4)
        input = [
            ConstantNode("1"),
            ConstantNode("2"),
            ConstantNode("3"),
            ConstantNode("4"),
        ]
        output = template_replace_node(
            "{0}, {1}", 
            "{0}, {1}", 
            SourceNode(), 
            *input
        )
        output_children = output.get_children()
        output_grandchildren = output_children[0].get_children()
        output_greatgrandchildren = output_grandchildren[0].get_children()
        
        self.assertEqual(type(output), TemplatedReplaceNode)
        self.assertEqual(type(output_children[0]), TemplatedNode)
        self.assertEqual(type(output_grandchildren[0]), TemplatedNode)

        self.assertEqual(output.template, "{0}, {1}")
        self.assertEqual(output_children[0].template, "{0}, {1}")
        self.assertEqual(output_grandchildren[0].template, "{0}, {1}")

        self.assertEqual(output_greatgrandchildren[0], input[0])
        self.assertEqual(output_greatgrandchildren[1], input[1])
        self.assertEqual(output_grandchildren[1], input[2])
        self.assertEqual(output_children[1], input[3])