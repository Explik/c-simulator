
# Based on pycparser's NodeVisitor
from modification_nodes import ConstantNode, CopyNode, InsertBeforeStatementsNode, ModificationNode, ReplaceNode, ReplaceTokenKindNode, TemplatedNode, TemplatedReplaceNode, assignment_node, comma_replace_node
from source_nodes import SourceNode, SourceNodeResolver

# Based on https://stackoverflow.com/questions/952914/how-do-i-make-a-flat-list-out-of-a-list-of-lists
def flatten(l):
    return [item for sublist in l for item in sublist]

class SourceTreeVisitor:
    def visit(self, source_node: SourceNode): 
        node_type = SourceNodeResolver.get_type(source_node)
        node_method_name = 'visit_' + node_type
        node_method = getattr(self, node_method_name, self.generic_visit)
        node_result = node_method(source_node)
        return node_result

    def generic_visit(self, source_node: SourceNode) -> list[ModificationNode]: 
        source_node_modification_lists = [self.visit(c) for c in source_node.children]
        source_node_modifications = flatten(source_node_modification_lists)
        return source_node_modifications

class SourceTreeModifier: 
    def __init__(self, modification_nodes: ModificationNode) -> None:
        self.modification_nodes = modification_nodes

    def visit(self, source_node: SourceNode): 
        # Depth first replacement
        new_children = [self.visit(c) for c in source_node.children]
        new_source_node = SourceNode.copy(source_node)
        new_source_node.children = new_children

        modification_node = next((m for m in self.modification_nodes if m.isApplicable(source_node)), None)

        # Apply modification if found
        if modification_node is not None:
            return modification_node.apply(new_source_node) 
        else: 
            return new_source_node

class ReplaceAdditionSourceTreeVisitor(SourceTreeVisitor):
    def visit_BinaryOperator(self, source_node: SourceNode) -> list[ModificationNode]:
        if SourceNodeResolver.get_binary_operator(source_node) != '+':
            return []
        
        lvalue = self.visit(source_node.children[0])
        if len(lvalue) == 0: 
            lvalue = [CopyNode(source_node.children[0])]
        rvalue = self.visit(source_node.children[1])
        if len(rvalue) == 0: 
            rvalue = [CopyNode(source_node.children[1])]
        
        return [TemplatedReplaceNode(
            source_node, 
            "add({0}, {1})",
            lvalue + rvalue
        )]

class ReplaceIdentifierSourceTreeVisitor(SourceTreeVisitor):
    def __init__(self, target: str, replacement: str) -> None:
        super().__init__()

        self.target = target
        self.replacement = replacement

    def visit_VarDecl(self, source_node) -> list[ModificationNode]: 
        if (source_node.node.spelling == self.target):
            return [ReplaceTokenKindNode(source_node, 'identifier', ConstantNode(self.replacement))]
        else: 
            return []

    def visit_DeclRefExpr(self, source_node) -> list[ModificationNode]:
        if (source_node.node.spelling == self.target):
            return [ReplaceNode(source_node, ConstantNode(self.replacement))]
        else: 
            return []
        
class NotifySourceTreeVisitor(SourceTreeVisitor):
    def __init__(self) -> None:
        super().__init__()
        self.declarations: list[ModificationNode] = []

    def visit_FunctionDecl(self, source_node: SourceNode) -> list[ModificationNode]:
        modifications = flatten([self.visit(c) for c in source_node.children])
        function_body_node = source_node.children[0]

        return [InsertBeforeStatementsNode(
            function_body_node,
            self.declarations
        )] + modifications

    def visit_DeclRefExpr(self, source_node) -> list[ModificationNode]:
        temp = f"temp{len(self.declarations)}"
        self.declarations.append(ConstantNode(f"int {temp};"))

        value = comma_replace_node(
            source_node,
            assignment_node(
                ConstantNode(temp), 
                CopyNode(source_node)
            ),
            ConstantNode("notify()"),
            ConstantNode(temp)
        )
        return [value]