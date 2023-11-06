
# Based on pycparser's NodeVisitor
from typing import Callable
from modification_nodes import CompoundNode, ConstantNode, CopyNode, InsertBeforeStatementsNode, ModificationNode, ReplaceChildrenNode, ReplaceNode, ReplaceTokenKindNode, TemplatedNode, TemplatedReplaceNode, assignment_node, comma_replace_node
from source_nodes import SourceNode, SourceNodeResolver

# Based on https://stackoverflow.com/questions/952914/how-do-i-make-a-flat-list-out-of-a-list-of-lists
def flatten(l):
    return [item for sublist in l for item in sublist]

# Basic visitors 
class SourceTreeVisitor:
    def visit(self, source_node: SourceNode): 
        node_type = SourceNodeResolver.get_type(source_node)
        node_method_name = 'visit_' + node_type
        node_method = getattr(self, node_method_name, self.generic_visit)
        node_result = node_method(source_node)
        return node_result

    def generic_visit(self, source_node: SourceNode) -> ModificationNode|None: 
        source_node_modifications = [self.visit(c) for c in source_node.children]
        source_node_modifications_filtered = [m for m in source_node_modifications if m is not None]

        if len(source_node_modifications_filtered) == 0: 
            return None
        elif len(source_node_modifications_filtered) == 1: 
            return source_node_modifications_filtered[0]
        else: 
            return CompoundNode(source_node_modifications_filtered)

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
    def visit_BinaryOperator(self, source_node: SourceNode) -> ModificationNode:
        if SourceNodeResolver.get_binary_operator(source_node) != '+':
            return []
        
        lvalue = self.visit(source_node.children[0])
        if len(lvalue) == 0: 
            lvalue = [CopyNode(source_node.children[0])]
        rvalue = self.visit(source_node.children[1])
        if len(rvalue) == 0: 
            rvalue = [CopyNode(source_node.children[1])]
        
        return TemplatedReplaceNode(
            source_node, 
            "add({0}, {1})",
            lvalue + rvalue
        )

class ReplaceIdentifierSourceTreeVisitor(SourceTreeVisitor):
    def __init__(self, target: str, replacement: str) -> None:
        super().__init__()

        self.target = target
        self.replacement = replacement

    def visit_VarDecl(self, source_node) -> ModificationNode: 
        if (source_node.node.spelling == self.target):
            return ReplaceTokenKindNode(source_node, 'identifier', ConstantNode(self.replacement))
        else: 
            return None

    def visit_DeclRefExpr(self, source_node) -> ModificationNode:
        if (source_node.node.spelling == self.target):
            return ReplaceNode(source_node, ConstantNode(self.replacement))
        else: 
            return None
        
class NotifySourceTreeVisitor(SourceTreeVisitor):
    def __init__(self) -> None:
        super().__init__()
        self.declarations: list[ModificationNode] = []

    def visit_FunctionDecl(self, source_node: SourceNode) -> list[ModificationNode]:
        modifications = flatten([self.visit(c) for c in source_node.children])
        function_body_node = source_node.children[0]

        return CompoundNode([InsertBeforeStatementsNode(
            function_body_node,
            self.declarations
        )] + modifications)

    def visit_DeclRefExpr(self, source_node) -> list[ModificationNode]:
        temp = f"temp{len(self.declarations)}"
        self.declarations.append(ConstantNode(f"int {temp};"))

        return comma_replace_node(
            source_node,
            assignment_node(
                ConstantNode(temp), 
                CopyNode(source_node)
            ),
            ConstantNode("notify()"),
            ConstantNode(temp)
        )
    
# Composite visitors 
class PartialTreeVisitor():
    def __init__(self) -> None:
        self.push_variable: Callable[[], ModificationNode]|None = None
        self.pop_variables: Callable[[], list[ModificationNode]]|None = None
        self.callback: Callable[[SourceNode], ModificationNode]|None = None

    def can_visit(self, source_node: SourceNode):
        raise Exception("Not implemented")
    def visit(self, source_node: SourceNode): 
        raise Exception("Not implemented")

class CompositeTreeVisitor(SourceTreeVisitor):
    def __init__(self, partial_visitors: list[PartialTreeVisitor]) -> None:
        super().__init__() 
        self.variables = []
        self.partial_visitors = partial_visitors

        for visitor in partial_visitors: 
            visitor.push_variable = self.push_variable
            visitor.pop_variables = self.pop_variable
            visitor.callback = self.generic_visit

    def generic_visit(self, source_node: SourceNode) -> ModificationNode | None:
        partial_visitor = next((v for v in self.partial_visitors if v.can_visit(source_node)), None)
        if partial_visitor is not None: 
            return partial_visitor.visit(source_node)
        else: 
            return super().generic_visit(source_node)
    
    def push_variable(self) -> ModificationNode:
        variable_name = f"temp{len(self.variables)}"
        variable = ConstantNode(f"int {variable_name}")
        self.variables.append(variable)
        return ConstantNode(variable_name)
    
    def pop_variable(self) -> list[ModificationNode]:
        return self.variables
    
class PartialTreeVisitor_DeclRefExpr(PartialTreeVisitor):
    def can_visit(self, source_node: SourceNode):
        return SourceNodeResolver.get_type(source_node) == "DeclRefExpr"

    def visit(self, source_node: SourceNode):
        temp_variable = self.push_variable()

        return comma_replace_node(
            source_node, 
            assignment_node(temp_variable, CopyNode(source_node)),
            ConstantNode("notify()"),
            temp_variable
        )
    
class PartialTreeVisitor_BinaryOperator(PartialTreeVisitor):
    def can_visit(self, source_node: SourceNode):
        return SourceNodeResolver.get_type(source_node) == "BinaryOperator"

    def visit(self, source_node: SourceNode):
        buffer = []
        children = source_node.get_children()
        transformed_left = self.callback(children[0]) 
        transformed_right = self.callback(children[1])
        
        if transformed_left is not None: 
            buffer.append(transformed_left.getChildren()[0])
            lvalue = transformed_left.getChildren()[1]
        else: 
            lvalue = CopyNode(children[0])

        if  transformed_right is not None: 
            buffer.append(transformed_right.getChildren()[0])
            rvalue = transformed_right.getChildren()[1]
        else:
            rvalue = CopyNode(children[1])

        temp_variable = self.push_variable()
        buffer.append(assignment_node(
            temp_variable, 
            ReplaceChildrenNode(
                source_node,
                [lvalue, rvalue]
            )
        ))
        buffer.append(ConstantNode("notify()"))
        buffer.append(temp_variable)
        
        return comma_replace_node(
            source_node, 
            *buffer
        )