
# Based on pycparser's NodeVisitor
from typing import Callable
from modification_nodes import CompoundReplaceNode, ConstantNode, CopyNode, CopyReplaceNode, InsertIntializerNode, InsertModificationNode, ModificationNode, ReplaceChildrenNode, ReplaceModificationNode, ReplaceNode, ReplaceTokenKindNode, TemplatedNode, TemplatedReplaceNode, assert_list_type, assert_type, assignment_node, comma_node, comma_node_with_parentheses, comma_replace_node, comma_stmt_replace_node, compound_replace_node, copy_replace_node
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

# Composite visitors 
class NotifyData(): 
    counter = -1

    def __init__(self, id: int, value: str) -> None:
        self.id = id
        self.value = value
        self.action: str|None = None
        self.type:str|None = None
        self.identifier:str|None = None
        self.location:str|None = None

    @staticmethod 
    def create_assign(source_node: SourceNode, identifier_node: SourceNode): 
        extent = source_node.node.extent
        
        NotifyData.counter += 1
        n = NotifyData(NotifyData.counter, f"&{identifier_node}")
        n.action = "assign" 
        n.identifier = f"{identifier_node}"
        n.location = [
            extent.start.line, 
            extent.start.column,
            extent.end.line,
            extent.end.column - 1
        ]
        n.type = identifier_node.node.type.spelling
        return n

    @staticmethod
    def create_decl(source_node: SourceNode, value_node: ConstantNode): 
        NotifyData.counter += 1
        n = NotifyData(NotifyData.counter, f"&{value_node.value}")
        n.action = "decl" 
        n.type = source_node.node.type.spelling
        n.identifier = source_node.node.spelling
        return n

    @staticmethod
    def create_eval(source_node: SourceNode, value_node: ConstantNode): 
        extent = source_node.node.extent
        
        NotifyData.counter += 1
        n = NotifyData(NotifyData.counter, f"&{value_node.value}")
        n.action = "eval" 
        n.location = [
            extent.start.line, 
            extent.start.column,
            extent.end.line,
            extent.end.column - 1
        ]
        n.type = source_node.node.type.spelling
        return n 
    
    @staticmethod
    def create_stat(source_node: SourceNode):
        extent = source_node.node.extent
        
        NotifyData.counter += 1
        n = NotifyData(NotifyData.counter, "(void*)0")
        n.action = "stat" 
        n.location = [
            extent.start.line, 
            extent.start.column,
            extent.end.line,
            extent.end.column - 1
        ]
        return n 

class NotifyDataSerializer():
    def serialize_list(self, notifications: list[NotifyData]):
        items = [self.serialize(n) for n in notifications]
        serialized_items = ",".join(items)
        return "[" + serialized_items + "]"
    
    def serialize(self, notification: NotifyData):
        buffer = dict()
        buffer["action"] = f"\"{notification.action}\""

        if (notification.action in ["assign", "eval", "decl"]):
            buffer["dataType"] = f"\"{notification.type}\""
        
        if (notification.action in ["assign", "eval", "stat"]):
            buffer["location"] = f"{notification.location}"

        if (notification.action in ["assign", "decl"]):
            buffer["identifier"] = f"\"{notification.identifier}\""

        items = [f"\"{key}\":{buffer[key]}" for key in buffer]
        serialized_items = ",".join(items)
        return "{" + serialized_items + "}"

# Transformation nodes 
class NotifyTemplateNode(ReplaceModificationNode): 
    def __init__(self, target: SourceNode, node: InsertModificationNode, variable_node: InsertModificationNode|None = None, start_notifies: list[NotifyData] = [], end_notifies: list[NotifyData] = []) -> None:
        assert_type(target, SourceNode)
        assert_type(node, InsertModificationNode)
        assert_list_type(start_notifies, NotifyData)
        assert_list_type(end_notifies, NotifyData)

        super().__init__()
        self.target = target
        self.node = node
        self.variable_node = variable_node
        self.start_notfies = start_notifies
        self.end_notifies = end_notifies

    def is_applicable(self, node: SourceNode) -> bool:
       return SourceNode.equals(node, self.target)

    def apply(self, target: SourceNode) -> SourceNode:
        # Generate children
        variable_name = self.variable_node and f"{self.variable_node.apply()}"
        children_buffer = []
        if any(self.start_notfies): 
            children_buffer.append(SourceNode.create(None, f"notify({target.id + 1000})", [], [])) 
        
        if (self.variable_node is None): 
            children_buffer.append(self.node.apply())
        else:
            children_buffer.append(SourceNode.create(
                None,
                f"{variable_name} = {{0}}",
                [],
                [self.node.apply()]
            ))

        if any(self.end_notifies): 
            child_buffer = [f"{target.id + 2000}"]
            if any(n.action == "eval" for n in self.end_notifies):
                child_buffer.append(f"&{variable_name}")
            child_buffer.extend(["&" + n.identifier for n in self.end_notifies if n.action == "assign"])
            child_value = "notify(" + ", ".join(child_buffer) + ")"

            children_buffer.append(SourceNode.create(None, child_value, [], []))

        if (self.variable_node is not None):
            children_buffer.append(SourceNode.create(None, f"{variable_name}", [], []))

        # Generate template 
        template_placeholders = ["{" + f"{i}" + "}" for i in range(0, len(children_buffer))]
        template = "(" + ", ".join(template_placeholders) + ")"
        return SourceNode.create(None, template, [], children_buffer)
    
    def get_children(self) -> list[ModificationNode]:
        return []
    
    def with_start_notify(self, notify_data: NotifyData):
        return NotifyTemplateNode(
            self.target, 
            self.node,
            self.variable_node,
            self.start_notfies + [notify_data], 
            self.end_notifies) 

    def with_end_notify(self, notify_data: NotifyData): 
         return NotifyTemplateNode(
            self.target, 
            self.node,
            self.variable_node,
            self.start_notfies, 
            self.end_notifies + [notify_data]
        ) 

class PartialTreeVisitor():
    def __init__(self) -> None:
        self.create_notify: Callable[[NotifyData], InsertModificationNode]|None = None
        self.push_variable: Callable[[SourceNode], InsertModificationNode]|None = None
        self.pop_variables: Callable[[], list[InsertModificationNode]]|None = None
        self.callback: Callable[[SourceNode], ModificationNode]|None = None

    def can_visit(self, source_node: SourceNode):
        raise Exception("Not implemented")
    
    def visit(self, source_node: SourceNode): 
        raise Exception("Not implemented")

class PartialTreeVisitor_SimpleExpression(PartialTreeVisitor): 
    def visit(self, target_node: SourceNode):
        value_node = CopyNode(target_node)
        variable_node = self.push_variable(target_node)
        return NotifyTemplateNode(target_node, value_node, variable_node)
    
class PartialTreeVisitor_CompoundExpression(PartialTreeVisitor):
    def visit(self, source_node: SourceNode, children_nodes: list[SourceNode]|None = None, variable_node: SourceNode|None = None):
        children = children_nodes if children_nodes is not None else source_node.get_children()
        transformed_children = []

        for child in children: 
            child_result = self.callback(child)

            if child_result is not None: 
                transformed_children.append(child_result)

        value_node = CopyReplaceNode(
            source_node,
            transformed_children
        )
        
        return NotifyTemplateNode(
            source_node,
            value_node,
            variable_node
        )
    
class PartialTreeVisitor_StatementExpression(PartialTreeVisitor): 
    def visit(self, source_node: SourceNode):
        return super().visit(source_node)

class CompositeTreeVisitor(SourceTreeVisitor):
    def __init__(self, partial_visitors: list[PartialTreeVisitor]) -> None:
        super().__init__() 
        self.notifies = []
        self.variables = []
        self.partial_visitors = partial_visitors

        for visitor in partial_visitors: 
            visitor.create_notify = self.create_notify
            visitor.push_variable = self.push_variable
            visitor.pop_variables = self.pop_variable
            visitor.callback = self.generic_visit

    def generic_visit(self, source_node: SourceNode) -> ModificationNode | None:
        partial_visitor = next((v for v in self.partial_visitors if v.can_visit(source_node)), None)
        if partial_visitor is not None: 
            return partial_visitor.visit(source_node)
        else: 
            return super().generic_visit(source_node)
    
    def create_notify(self, data: NotifyData) -> InsertModificationNode: 
        self.notifies.append(data)
        return ConstantNode(f"notify({data.id}, {data.value})")

    def get_notifies(self) -> list[NotifyData]:
        return self.notifies

    def push_variable(self, source_node: SourceNode) -> InsertModificationNode:
        variable_type = source_node.node.type.spelling
        variable_name = f"temp{len(self.variables)}"
        variable = ConstantNode(f"{variable_type} {variable_name};")
        self.variables.append(variable)
        return ConstantNode(variable_name)
    
    def pop_variable(self) -> list[InsertModificationNode]:
        return self.variables

class PartialTreeVisitor_GenericLiteral(PartialTreeVisitor_SimpleExpression):
    def can_visit(self, source_node: SourceNode):
        node_type = SourceNodeResolver.get_type(source_node)
        return node_type in ["IntegerLiteral", "StringLiteral"]
    
    def visit(self, target_node: SourceNode):
        return super().visit(target_node)

class PartialTreeVisitor_DeclRefExpr(PartialTreeVisitor_SimpleExpression):
    def can_visit(self, source_node: SourceNode):
        return SourceNodeResolver.get_type(source_node) == "DeclRefExpr"

    def visit(self, source_node: SourceNode):
        eval_notify = NotifyData.create_eval(source_node, ConstantNode("temp"))

        transformed_node = super().visit(source_node)
        return transformed_node.with_end_notify(eval_notify)
    
class PartialTreeVisitor_UnaryOperator(PartialTreeVisitor_SimpleExpression):
    def can_visit(self, source_node: SourceNode):
        return SourceNodeResolver.get_type(source_node) == "UnaryOperator"

    def visit(self, source_node: SourceNode):
        eval_notify = NotifyData.create_eval(source_node, ConstantNode("temp"))
        
        transformed_node = super().visit(source_node)
        return transformed_node.with_end_notify(eval_notify)

class PartialTreeVisitor_UnaryOperator_Assignment(PartialTreeVisitor_UnaryOperator):
    def can_visit(self, source_node: SourceNode):
        if (SourceNodeResolver.get_type(source_node) != "UnaryOperator"):
            return False
        
        operator = SourceNodeResolver.get_unary_operator(source_node) 
        return operator == "++" or operator == "--"
    
    def visit(self, source_node: SourceNode):
        assign_notify = NotifyData.create_assign(source_node, source_node.get_children()[0])

        transformed_node = super().visit(source_node)
        return transformed_node.with_end_notify(assign_notify)

class PartialTreeVisitor_BinaryOperator(PartialTreeVisitor_CompoundExpression):
    def can_visit(self, source_node: SourceNode):
        return SourceNodeResolver.get_type(source_node) == "BinaryOperator"

    def visit(self, source_node: SourceNode):
        eval_notify = NotifyData.create_eval(source_node, ConstantNode("temp"))

        transformed_node = super().visit(source_node)
        return transformed_node.with_end_notify(eval_notify)

class PartialTreeVisitor_BinaryOperator_Assignment(PartialTreeVisitor_CompoundExpression):
    def can_visit(self, source_node: SourceNode):
        if SourceNodeResolver.get_type(source_node) not in ["BinaryOperator", "CompoundAssignmentOperator"]:
            return False 
        
        binary_operator = SourceNodeResolver.get_binary_operator(source_node)
        return binary_operator in ["=", "+=", "-=", "*=", "/=", "%=", "<<=", ">>=", "&=", "^=", "|="]
    
    def visit(self, source_node: SourceNode):
        eval_notify = NotifyData.create_eval(source_node, ConstantNode("temp"))
        
        variable_node = self.push_variable(source_node)
        child_nodes = [source_node.get_children()[1]]
        transformed_node = super().visit(source_node, child_nodes, variable_node)
        return transformed_node.with_end_notify(eval_notify)
    
class PartialTreeVisitor_CallExpr(PartialTreeVisitor_CompoundExpression):
    def can_visit(self, source_node: SourceNode):
        return SourceNodeResolver.get_type(source_node) == "CallExpr"
    
    def visit(self, source_node: SourceNode):
        eval_notify = NotifyData.create_eval(source_node, ConstantNode("temp"))

        variable_node = self.push_variable(source_node) if source_node.node.type.spelling != "void" else None
        child_nodes = source_node.get_children()[1:]
        transformed_node = super().visit(source_node, child_nodes, variable_node)
        return transformed_node.with_end_notify(eval_notify)

class PartialTreeVisitor_VarDecl(PartialTreeVisitor_SimpleExpression):
    def can_visit(self, source_node: SourceNode):
        return SourceNodeResolver.get_type(source_node) == "VarDecl"

    def visit(self, source_node: SourceNode):
        decl_notify = NotifyData.create_decl(source_node, ConstantNode("temp"))

        transformed_node = super().visit(source_node.get_children()[0])
        return transformed_node.with_end_notify(decl_notify)

class PartialTreeVisitor_FunctionDecl(PartialTreeVisitor): 
    def can_visit(self, source_node: SourceNode):
        if (SourceNodeResolver.get_type(source_node) != "FunctionDecl"):
            return False
        
        children = source_node.get_children()
        return any(children) and SourceNodeResolver.get_type(children[-1]) == "CompoundStmt"

    def visit(self, source_node: SourceNode):
        function_body_node = source_node.get_children()[-1]
        variables = self.pop_variables()
        transformed_children = [(c, self.callback(c)) for c in function_body_node.get_children()]
        statements = [copy_replace_node(c[0], c[1]) if c[1] is not None else CopyNode(c[0]) for c in transformed_children]
        
        return compound_replace_node(
            function_body_node, 
            *(variables + statements)
        )
    
class PartialTreeVisitor_TranslationUnit(PartialTreeVisitor): 
    def can_visit(self, source_node: SourceNode):
        return SourceNodeResolver.get_type(source_node) == "TranslationUnit"
    
    def visit(self, source_node: SourceNode):
        template = "void notify(char* metadata)" + source_node.value
        return None