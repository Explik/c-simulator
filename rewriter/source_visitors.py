
# Based on pycparser's NodeVisitor
from typing import Callable
from modification_nodes import CompoundReplaceNode, ConstantNode, CopyNode, CopyReplaceNode, InsertIntializerNode, InsertModificationNode, ModificationNode, ReplaceChildrenNode, ReplaceNode, ReplaceTokenKindNode, TemplatedNode, TemplatedReplaceNode, assignment_node, comma_node, comma_node_with_parentheses, comma_replace_node, comma_stmt_replace_node, compound_replace_node, copy_replace_node
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

class PartialTreeVisitor_GenericLiteral(PartialTreeVisitor):
    def can_visit(self, source_node: SourceNode):
        if source_node.parent is None:
            return False 
        
        node_type = SourceNodeResolver.get_type(source_node)
        return is_first_expression(source_node) and node_type in ["IntegerLiteral", "StringLiteral"]
    
    def visit(self, source_node: SourceNode):
        notify_data = NotifyData.create_stat(source_node.parent)
        replace_node = comma_stmt_replace_node if is_statement(source_node) else comma_replace_node
        return replace_node(
            source_node, 
            self.create_notify(notify_data),
            CopyNode(source_node)
        )

class PartialTreeVisitor_DeclRefExpr(PartialTreeVisitor):
    def can_visit(self, source_node: SourceNode):
        return SourceNodeResolver.get_type(source_node) == "DeclRefExpr"

    def visit(self, source_node: SourceNode):
        buffer = []

        if is_first_expression(source_node):
            notify_stat = NotifyData.create_stat(source_node)
            buffer.append(self.create_notify(notify_stat))

        temp_variable = self.push_variable(source_node)
        notify_data = NotifyData.create_eval(source_node, temp_variable)
        buffer.extend([
            assignment_node(temp_variable, CopyNode(source_node)),
            self.create_notify(notify_data),
            temp_variable
        ])

        replace_node = comma_stmt_replace_node if is_statement(source_node) else comma_replace_node
        return replace_node(
            source_node, 
            *buffer
        )
    
class PartialTreeVisitor_UnaryOperator(PartialTreeVisitor):
    def can_visit(self, source_node: SourceNode):
        return SourceNodeResolver.get_type(source_node) == "UnaryOperator"

    def visit(self, source_node: SourceNode):
        buffer = []

        if is_first_expression(source_node):
            notify_stat = NotifyData.create_stat(source_node)
            buffer.append(self.create_notify(notify_stat))

        children = source_node.get_children()
        transformed_operand = self.transform_left(children[0]) 
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
        buffer.extend(self.create_notify_nodes(source_node, temp_variable, children[0]))
        buffer.append(temp_variable)
        
        replace_node = comma_stmt_replace_node if is_statement(source_node) else comma_replace_node
        return replace_node(
            source_node, 
            *buffer
        )
    
    def transform_left(self, source_node: SourceNode): 
        return self.callback(source_node)

    def create_notify_nodes(self, source_node: SourceNode, value_node: SourceNode, identifier_node: SourceNode) -> list[InsertModificationNode]:
        notify_data = NotifyData.create_eval(source_node, value_node)
        return [self.create_notify(notify_data)]

class PartialTreeVisitor_UnaryOperator_Assignment(PartialTreeVisitor_UnaryOperator):
    def can_visit(self, source_node: SourceNode):
        if (SourceNodeResolver.get_type(source_node) != "UnaryOperator"):
            return False
        
        operator = SourceNodeResolver.get_unary_operator(source_node) 
        return operator == "++" or operator == "--"
    
    def transform_left(self, source_node: SourceNode):
        return None

    def create_notify_nodes(self, source_nodes: SourceNode, value_node: SourceNode, identifier_node: SourceNode) -> list[InsertModificationNode]:
        notify_data_eval = NotifyData.create_eval(source_nodes, value_node)
        notify_data_assign = NotifyData.create_assign(source_nodes, identifier_node)

        return [
            self.create_notify(notify_data_eval),
            self.create_notify(notify_data_assign)
        ]
    
class PartialTreeVisitor_BinaryOperator(PartialTreeVisitor):
    def can_visit(self, source_node: SourceNode):
        return SourceNodeResolver.get_type(source_node) == "BinaryOperator"

    def visit(self, source_node: SourceNode):
        buffer = []

        if is_first_expression(source_node):
            notify_stat = NotifyData.create_stat(source_node)
            buffer.append(self.create_notify(notify_stat))

        children = source_node.get_children()
        transformed_left = self.transform_left(children[0])
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
        buffer.extend(self.create_notify_nodes(source_node, temp_variable, children[0]))
        buffer.append(temp_variable)
        
        replace_node = comma_stmt_replace_node if is_statement(source_node) else comma_replace_node
        return replace_node(
            source_node, 
            *buffer
        )
    
    def transform_left(self, source_node: SourceNode):
        return self.callback(source_node)

    def create_notify_nodes(self, source_nodes: SourceNode, value_node: SourceNode, identifier_node: SourceNode) -> list[InsertModificationNode]:
        notify_data_eval = NotifyData.create_eval(source_nodes, value_node)
        return [self.create_notify(notify_data_eval)]

class PartialTreeVisitor_BinaryOperator_Assignment(PartialTreeVisitor_BinaryOperator):
    def can_visit(self, source_node: SourceNode):
        if SourceNodeResolver.get_type(source_node) not in ["BinaryOperator", "CompoundAssignmentOperator"]:
            return False 
        
        binary_operator = SourceNodeResolver.get_binary_operator(source_node)
        return binary_operator in ["=", "+=", "-=", "*=", "/=", "%=", "<<=", ">>=", "&=", "^=", "|="]
    
    def transform_left(self, source_nodes: SourceNode): 
        return None

    def create_notify_nodes(self, source_nodes: SourceNode, value_node: SourceNode, identifier_node: SourceNode) -> list[InsertModificationNode]:
        notify_data_eval = NotifyData.create_eval(source_nodes, value_node)
        notify_data_assign = NotifyData.create_assign(source_nodes, identifier_node)

        return [
            self.create_notify(notify_data_eval),
            self.create_notify(notify_data_assign)
        ]
    
class PartialTreeVisitor_CallExpr(PartialTreeVisitor):
    def can_visit(self, source_node: SourceNode):
        return SourceNodeResolver.get_type(source_node) == "CallExpr"

    def visit(self, source_node: SourceNode):
        buffer_comma = []
        buffer_parameters = []
        identifier = source_node.get_children()[0]
        parameters = source_node.get_children()[1:]
        
        if is_first_expression(source_node):
            notify_stat = NotifyData.create_stat(source_node)
            buffer_comma.append(self.create_notify(notify_stat))
        
        # Capture parameter values 
        transformed_parameters = [(p, self.callback(p)) for p in parameters]
        for transformed_parameter in transformed_parameters:
            if transformed_parameter[1] is None: 
                buffer_parameters.append(CopyNode(transformed_parameter[0]))
            else: 
                parameter_children = transformed_parameter[1].get_children()
                buffer_comma.append(parameter_children[0])
                buffer_parameters.append(parameter_children[1])

        transformed_children = [CopyNode(identifier)] + buffer_parameters
        transformed_node = copy_replace_node(
            source_node, 
            ReplaceChildrenNode(source_node, transformed_children)
        )

        # Capture return value
        if (source_node.node.type.spelling != "void"):
            temp_variable = self.push_variable(source_node)
            notify_data = NotifyData.create_eval(source_node, temp_variable)
            buffer_comma.append(assignment_node(temp_variable, transformed_node))
            buffer_comma.append(self.create_notify(notify_data))
            buffer_comma.append(temp_variable)
        else: 
            buffer_comma.append(transformed_node)

        if len(buffer_comma) < 2:
            return None 
        
        replace_node = comma_stmt_replace_node if is_statement(source_node) else comma_replace_node
        return replace_node(
            source_node, 
            *buffer_comma
        )

class PartialTreeVisitor_VarDecl(PartialTreeVisitor):
    def can_visit(self, source_node: SourceNode):
        return SourceNodeResolver.get_type(source_node) == "VarDecl"

    def visit(self, source_node: SourceNode):
        child_buffer = []
        
        if (source_node.parent is None or source_node.parent.get_children()[0] == source_node):
            notify_stat = NotifyData.create_stat(source_node)
            child_buffer.append(self.create_notify(notify_stat))
        
        children = source_node.get_children()
        if (len(children) == 0):
            temp_value = self.push_variable(source_node)
            notify_decl = NotifyData.create_decl(source_node, temp_value)
            child_buffer.append(self.create_notify(notify_decl))
            child_buffer.append(temp_value)
            initalizer = comma_node_with_parentheses(*child_buffer)

            return InsertIntializerNode(source_node, initalizer)

        transformed_operand = self.callback(children[0]) 
        if transformed_operand is not None: 
            child_buffer.append(transformed_operand.get_children()[0])
            lvalue = transformed_operand.get_children()[1]

            notify_decl = NotifyData.create_decl(source_node, lvalue)
            child_buffer.append(self.create_notify(notify_decl))
            child_buffer.append(lvalue)
        else: 
            temp_value = self.push_variable(source_node)
            notify_decl = NotifyData.create_decl(source_node, temp_value)
            child_buffer.append(assignment_node(temp_value, CopyNode(children[0])))
            child_buffer.append(self.create_notify(notify_decl))
            child_buffer.append(temp_value)

        return ReplaceChildrenNode(
            source_node,
            [comma_node_with_parentheses(*child_buffer)]
        )

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