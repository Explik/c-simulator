
# Based on pycparser's NodeVisitor
from typing import Callable
from modification_nodes import CompoundReplaceNode, ConstantNode, CopyNode, CopyReplaceNode, InsertAfterTokenKindNode, InsertIntializerNode, InsertModificationNode, ModificationNode, ReplaceChildrenNode, ReplaceModificationNode, ReplaceNode, ReplaceTokenKindNode, TemplatedNode, TemplatedReplaceNode, assert_list_type, assert_type, assignment_node, comma_node, comma_node_with_parentheses, comma_replace_node, comma_stmt_replace_node, compound_replace_node, copy_replace_node
from notify_nodes import AssignNotifyData, BaseNotify, CompoundVoidNotifyReplaceNode, CompoundExprNotifyReplaceNode, DeclNotifyData, EvalNotifyData, ExprNotifyReplaceNode
from source_nodes import SourceNode, SourceNodeResolver

# Based on https://stackoverflow.com/questions/952914/how-do-i-make-a-flat-list-out-of-a-list-of-lists
def flatten(l):
    return [item for sublist in l for item in sublist]

def is_first_expression(source_node: SourceNode):
    return source_node.parent is not None and SourceNodeResolver.get_type(source_node.parent) in ["CompoundStmt", "ForStmt", "ReturnStmt", "IfStmt", "WhileStmt"]

def is_statement(source_node: SourceNode):
    if source_node is None: 
        return False 
    
    parent_type = SourceNodeResolver.get_type(source_node.parent)
    if parent_type in ["CompoundStmt", "ReturnStmt"]:
        return True
    
    parent_children = source_node.parent.get_children()
    return parent_type in ["ForStmt", "IfStmt", "WhileStmt"] and parent_children[-1] == source_node

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
            return CompoundReplaceNode(source_node, source_node_modifications_filtered)

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

# Transformation visitors 
class PartialTreeVisitor():
    def __init__(self) -> None:     
        self.callback: Callable[[SourceNode], ModificationNode]|None = None
        self.register: Callable[[BaseNotify|list[BaseNotify]], BaseNotify|list[BaseNotify]]|None = None
        self.deregister: Callable[[], list[BaseNotify]]|None = None

    def can_visit(self, source_node: SourceNode):
        raise Exception("Not implemented")
    
    def visit(self, source_node: SourceNode): 
        raise Exception("Not implemented")

class CompositeTreeVisitor(SourceTreeVisitor):
    def __init__(self, partial_visitors: list[PartialTreeVisitor]) -> None:
        super().__init__() 
        self.notifies = []
        self.function_notifies = []
        self.partial_visitors = partial_visitors

        for visitor in partial_visitors: 
            visitor.callback = self.generic_visit
            visitor.register = self.register_function_notify
            visitor.deregister = self.deregister_function_notify

    def generic_visit(self, source_node: SourceNode) -> ModificationNode | None:
        partial_visitor = next((v for v in self.partial_visitors if v.can_visit(source_node)), None)
        if partial_visitor is not None: 
            return partial_visitor.visit(source_node)
        else: 
            return super().generic_visit(source_node)
    
    def get_notifies(self): 
        return self.notifies

    def register_function_notify(self, data: BaseNotify|list[BaseNotify]) -> BaseNotify|list[BaseNotify]: 
        data_list = data if isinstance(data, list) else [data]
        self.function_notifies.extend(data_list)
        self.notifies.extend(data_list)
        return data

    def deregister_function_notify(self): 
        temp = self.function_notifies
        self.function_notifies = []
        return temp

class PartialTreeVisitor_GenericLiteral(PartialTreeVisitor):
    def can_visit(self, source_node: SourceNode):
        node_type = SourceNodeResolver.get_type(source_node)
        return node_type in ["IntegerLiteral", "StringLiteral"]
    
    def visit(self, target_node: SourceNode):
        return ExprNotifyReplaceNode(target_node)

class PartialTreeVisitor_DeclRefExpr(PartialTreeVisitor):
    def can_visit(self, source_node: SourceNode):
        return SourceNodeResolver.get_type(source_node) == "DeclRefExpr"

    def visit(self, source_node: SourceNode):
        notify_data = self.register(EvalNotifyData(source_node))
        return ExprNotifyReplaceNode(source_node).with_end_notify(notify_data)
    
class PartialTreeVisitor_UnaryOperator(PartialTreeVisitor):
    def can_visit(self, source_node: SourceNode):
        return SourceNodeResolver.get_type(source_node) == "UnaryOperator"

    def visit(self, source_node: SourceNode):
        notify_data = self.register(EvalNotifyData(source_node))
        child_results = [self.callback(c) for c in source_node.get_children()]
        return CompoundExprNotifyReplaceNode(source_node, child_results).with_end_notify(notify_data)

class PartialTreeVisitor_UnaryOperator_Assignment(PartialTreeVisitor_UnaryOperator):
    def can_visit(self, source_node: SourceNode):
        if (SourceNodeResolver.get_type(source_node) != "UnaryOperator"):
            return False
        
        operator = SourceNodeResolver.get_unary_operator(source_node) 
        return operator == "++" or operator == "--"
    
    def visit(self, source_node: SourceNode):
        notify_list = self.register([
            EvalNotifyData(source_node),
            AssignNotifyData(source_node, source_node.get_children()[0])
        ])
        return CompoundExprNotifyReplaceNode(source_node, []).with_end_notifies(notify_list)

class PartialTreeVisitor_BinaryOperator(PartialTreeVisitor):
    def can_visit(self, source_node: SourceNode):
        return SourceNodeResolver.get_type(source_node) == "BinaryOperator"

    def visit(self, source_node: SourceNode):
        notify_data = self.register(EvalNotifyData(source_node))
        child_results = [self.visit(c) for c in source_node.get_children()]
        return CompoundExprNotifyReplaceNode(source_node, child_results).with_end_notify(notify_data)

class PartialTreeVisitor_BinaryOperator_Assignment(PartialTreeVisitor):
    def can_visit(self, source_node: SourceNode):
        if SourceNodeResolver.get_type(source_node) not in ["BinaryOperator", "CompoundAssignmentOperator"]:
            return False 
        
        binary_operator = SourceNodeResolver.get_binary_operator(source_node)
        return binary_operator in ["=", "+=", "-=", "*=", "/=", "%=", "<<=", ">>=", "&=", "^=", "|="]
    
    def visit(self, source_node: SourceNode):
        notify_list = self.register([
            EvalNotifyData(source_node),
            AssignNotifyData(source_node, source_node.get_children()[0])
        ])
        child_results = [self.callback(c) for c in source_node.get_children()[1:]]
        return CompoundExprNotifyReplaceNode(source_node, child_results).with_end_notifies(notify_list)
    
class PartialTreeVisitor_CallExpr(PartialTreeVisitor):
    def can_visit(self, source_node: SourceNode):
        return SourceNodeResolver.get_type(source_node) == "CallExpr"
    
    def visit(self, source_node: SourceNode):
        if source_node.node.type.spelling == "void":
            return None

        eval_notify = self.register(EvalNotifyData(source_node))
        child_results = [self.callback(c) for c in source_node.get_children()[1:]]
        return CompoundExprNotifyReplaceNode(source_node, child_results).with_end_notify(eval_notify)

class PartialTreeVisitor_VarDecl(PartialTreeVisitor):
    def can_visit(self, source_node: SourceNode):
        return SourceNodeResolver.get_type(source_node) == "VarDecl"

    def visit(self, source_node: SourceNode):
        decl_notify = self.register(DeclNotifyData(source_node))
        return self.callback(source_node.get_children()[0]).with_end_notify(decl_notify)

class PartialTreeVisitor_FunctionDecl(PartialTreeVisitor): 
    def can_visit(self, source_node: SourceNode):
        if (SourceNodeResolver.get_type(source_node) != "FunctionDecl"):
            return False
        
        children = source_node.get_children()
        return any(children) and SourceNodeResolver.get_type(children[-1]) == "CompoundStmt"

    def visit(self, source_node: SourceNode):
        function_body_node = source_node.get_children()[-1]
        results = [self.callback(c) for c in function_body_node.get_children()]
        filtered_result = [r for r in results if r is not None]

        notifies = self.deregister()
        filtered_notifies = [n for n in notifies if isinstance(n, DeclNotifyData) or isinstance(n, EvalNotifyData)]
        unique_notifies = filtered_notifies
        declarations = [f"{n.type} {n.eval_identifier};" for n in unique_notifies]
        declaration_block = ConstantNode("\n".join(declarations))
        filtered_result.append(InsertAfterTokenKindNode(function_body_node, 'punctuation', declaration_block))

        return CompoundReplaceNode(function_body_node, filtered_result)
    
    def push_variable(self, source_node: SourceNode) -> InsertModificationNode:
        variable_type = source_node.node.type.spelling
        variable_name = f"temp{len(self.variables)}"
        variable = ConstantNode(f"{variable_type} {variable_name};")
        self.variables.append(variable)
        return ConstantNode(variable_name)
    
    def pop_variable(self) -> list[InsertModificationNode]:
        temp = self.variables
        self.variables = []
        return temp