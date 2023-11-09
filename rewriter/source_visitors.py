
# Based on pycparser's NodeVisitor
from typing import Callable
from modification_nodes import CompoundReplaceNode, ConstantNode, CopyNode, CopyReplaceNode, InsertModificationNode, ModificationNode, ReplaceChildrenNode, ReplaceNode, ReplaceTokenKindNode, TemplatedNode, TemplatedReplaceNode, assignment_node, comma_replace_node, compound_replace_node, copy_replace_node
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
            return CompoundReplaceNode(None, source_node_modifications_filtered)

class SourceTreeModifier: 
    def __init__(self, modification_nodes: ModificationNode) -> None:
        self.modification_nodes = modification_nodes

    def visit(self, source_node: SourceNode): 
        # Depth first replacement
        new_children = [self.visit(c) for c in source_node.children]
        new_source_node = SourceNode.copy(source_node)
        new_source_node.children = new_children

        modification_node = next((m for m in self.modification_nodes if m.is_applicable(source_node)), None)

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

# Composite visitors 
class PartialTreeVisitor():
    def __init__(self) -> None:
        self.push_variable: Callable[[SourceNode], InsertModificationNode]|None = None
        self.pop_variables: Callable[[], list[InsertModificationNode]]|None = None
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
    
    def push_variable(self, source_node: SourceNode) -> ModificationNode:
        variable_type = source_node.node.type.spelling
        variable_name = f"temp{len(self.variables)}"
        variable = ConstantNode(f"{variable_type} {variable_name};")
        self.variables.append(variable)
        return ConstantNode(variable_name)
    
    def pop_variable(self) -> list[ModificationNode]:
        return self.variables
    
class PartialTreeVisitor_DeclRefExpr(PartialTreeVisitor):
    def can_visit(self, source_node: SourceNode):
        return SourceNodeResolver.get_type(source_node) == "DeclRefExpr"

    def visit(self, source_node: SourceNode):
        temp_variable = self.push_variable(source_node)

        return comma_replace_node(
            source_node, 
            assignment_node(temp_variable, CopyNode(source_node)),
            ConstantNode("notify(\"a=eval\")"),
            temp_variable
        )
    
class PartialTreeVisitor_UnaryOperator(PartialTreeVisitor):
    def can_visit(self, source_node: SourceNode):
        return SourceNodeResolver.get_type(source_node) == "UnaryOperator"

    def visit(self, source_node: SourceNode):
        buffer = []
        children = source_node.get_children()
        transformed_operand = self.callback(children[0]) 
        
        if transformed_operand is not None: 
            buffer.append(transformed_operand.get_children()[0])
            lvalue = transformed_operand.get_children()[1]
        else: 
            lvalue = CopyNode(children[0])

        temp_variable = self.push_variable(source_node)
        buffer.append(assignment_node(
            temp_variable, 
            copy_replace_node(
                source_node, 
                ReplaceChildrenNode(source_node, [lvalue])
            )
        ))
        buffer.extend(self.create_notify_nodes(source_node))
        buffer.append(temp_variable)
        
        return comma_replace_node(
            source_node, 
            *buffer
        )
    
    def create_notify_nodes(self, source_nodes: SourceNode) -> list[InsertModificationNode]:
        return [ConstantNode("notify(\"a=eval\")")]

class PartialTreeVisitor_UnaryOperator_Assignment(PartialTreeVisitor_UnaryOperator):
    def can_visit(self, source_node: SourceNode):
        if (SourceNodeResolver.get_type(source_node) != "UnaryOperator"):
            return False
        
        operator = SourceNodeResolver.get_unary_operator(source_node) 
        return operator == "++" or operator == "--"
    
    def create_notify_nodes(self, source_nodes: SourceNode) -> list[InsertModificationNode]:
        return [
            ConstantNode("notify(\"a=eval\")"),
            ConstantNode("notify(\"a=assign\")")
        ]
    
class PartialTreeVisitor_BinaryOperator(PartialTreeVisitor):
    def can_visit(self, source_node: SourceNode):
        return SourceNodeResolver.get_type(source_node) == "BinaryOperator"

    def visit(self, source_node: SourceNode):
        buffer = []
        children = source_node.get_children()
        transformed_left = self.callback(children[0]) 
        transformed_right = self.callback(children[1])
        
        if transformed_left is not None: 
            buffer.append(transformed_left.get_children()[0])
            lvalue = transformed_left.get_children()[1]
        else: 
            lvalue = CopyNode(children[0])

        if  transformed_right is not None: 
            buffer.append(transformed_right.get_children()[0])
            rvalue = transformed_right.get_children()[1]
        else:
            rvalue = CopyNode(children[1])

        temp_variable = self.push_variable(source_node)
        buffer.append(assignment_node(
            temp_variable, 
            copy_replace_node(source_node, 
                ReplaceChildrenNode(
                    source_node,
                    [lvalue, rvalue]
                )
            )
        ))
        buffer.extend(self.create_notify_nodes(source_node))
        buffer.append(temp_variable)
        
        return comma_replace_node(
            source_node, 
            *buffer
        )
    
    def create_notify_nodes(self, source_nodes: SourceNode) -> list[InsertModificationNode]:
        return [ConstantNode("notify(\"a=eval\")")]

class PartialTreeVisitor_BinaryOperator_Assignment(PartialTreeVisitor_BinaryOperator):
    def can_visit(self, source_node: SourceNode):
        return SourceNodeResolver.get_type(source_node) == "BinaryOperator" and "=" in SourceNodeResolver.get_binary_operator(source_node) 
    
    def create_notify_nodes(self, source_nodes: SourceNode) -> list[InsertModificationNode]:
        return [
            ConstantNode("notify(\"a=eval\")"),
            ConstantNode("notify(\"a=assign\")")
        ]
    
class PartialTreeVisitor_CallExpr(PartialTreeVisitor):
    def can_visit(self, source_node: SourceNode):
        return SourceNodeResolver.get_type(source_node) == "CallExpr" and source_node.node.type.spelling != "void"

    def visit(self, source_node: SourceNode):
        temp_variable = self.push_variable(source_node)

        return comma_replace_node(
            source_node, 
            assignment_node(temp_variable, CopyNode(source_node)),
            ConstantNode("notify(\"a=eval\")"),
            temp_variable
        )

class PartialTreeVisitor_FunctionDecl(PartialTreeVisitor): 
    def can_visit(self, source_node: SourceNode):
        if (SourceNodeResolver.get_type(source_node) != "FunctionDecl"):
            return False
        
        children = source_node.get_children()
        return any(children) and SourceNodeResolver.get_type(children[0]) == "CompoundStmt"

    def visit(self, source_node: SourceNode):
        function_body_node = source_node.get_children()[0]
        variables = self.pop_variables()
        transformed_children = [(c, self.callback(c)) for c in function_body_node.get_children()]
        statements = [copy_replace_node(c[0], c[1]) if c[1] is not None else CopyNode(c[0]) for c in transformed_children]
        
        return compound_replace_node(
            function_body_node, 
            *(variables + statements)
        )