from copy import copy
from modification_nodes import CompoundReplaceNode, ConstantNode, CopyNode, CopyReplaceNode, InsertModificationNode, ReplaceModificationNode, TemplatedNode, TemplatedReplaceNode, assert_list_type, assert_type, assignment_node, comma_node, comma_node_with_parentheses
from modification_nodes import ModificationNode
from assertions import assert_type_or_none
from source_nodes import SourceNode
from source_nodes import SourceNode, SourceNodeResolver

# See https://stackoverflow.com/questions/952914/how-do-i-make-a-flat-list-out-of-a-list-of-lists
def flatten(l):
    return [item for sublist in l for item in sublist]

class VariableDeclaration: 
    def __init__(self, type: str, name: str, init: str|None = None) -> None:
        assert_type(type, str)
        assert_type(name, str)
        assert_type_or_none(init, str)

        self.type = type
        self.name = name
        self.init = init

    def get_declaration(self) -> str:
        """Creates int * t = 5; style declaration"""
        if "(*)(" not in self.type:
            type_parts = self.type.split("[")
            type_name = type_parts[0] + '*' * (len(type_parts) - 1)
            
            buffer = []
            buffer.append(type_name + " ")
            buffer.append(self.name)
            if self.init is not None: 
                buffer.append(" = " + self.init)
            buffer.append(";")

            return "".join(buffer)
        else: 
            # Splitting the input string to get the return type and parameters
            parts = self.type.split("(*")
            return_type = parts[0].strip()
            parameters = parts[1].split(")")[0].strip()

            # Forming the new function signature
            new_signature = f"{return_type} (*{self.name})({parameters})"

            return f"{new_signature} = {self.init};" if self.init is not None else f"{new_signature};"
    
    def get_declaration_part(self) -> str: 
        """Creates *t = 5 style declaration"""
        type_stars = len(self.type.split("*")) + len(self.type.split("[")) - 2
        type_name = '*' * type_stars

        buffer = []
        buffer.append(type_name)
        buffer.append(self.name)
        if self.init is not None: 
            buffer.append(" = " + self.init)

        return "".join(buffer)

    def __eq__(self, __value: object) -> bool:
        if type(__value) != VariableDeclaration:
            return False
        return self.name == __value.name

# Notify data
class BaseNotify():
    counter = 0

    def __init__(self, node: SourceNode|None) -> None:
        BaseNotify.counter += 1
        self.id = BaseNotify.counter
        self.node_id = node and node.id
        self.notify_id: str| None = None
        
        self.action: str|None = None
        self.scope: tuple|None = None
        self.type:str|None = None
        self.identifier:str|None = None
        self.parameters: list[str]|None = None
        self.eval_identifier: str|None = None

    def get_notify_id(self) -> str|None: 
        return self.notify_id
    
    def set_notify_id(self, id) -> str|None: 
        self.notify_id = id

    def get_statement_variables(self) -> list[VariableDeclaration]:
        return []

    def get_block_variables(self) -> list[VariableDeclaration]: 
        return []

    def get_notify_parameters(self) -> list[str]: 
        return []
    
    def serialize(self, code):
        buffer = dict()

        if self.id is not None: 
            buffer["id"] = f"{self.id}"
        else: raise Exception("Property id is None")
        
        if self.action is not None: 
            buffer["action"] = f"\"{self.action}\""
        else: raise Exception("Property action is None")
        
        if self.notify_id is not None: 
            buffer["notifyId"] = f"{self.notify_id}"
        else: raise Exception("Property notify_id is None")

        if self.action not in ["type"]:
            if self.node_id is not None: 
                buffer["nodeId"] = f"{self.node_id}"
            else: raise Exception("Property node_id is None")

        if (self.action in ["assign", "eval", "decl", "return", "invocation", "par"]):
            if self.type is not None:
                buffer["dataType"] = f"\"{self.type}\""
            else: raise Exception("Property type is None")
        
        if (self.action in ["decl", "par"]):
            if self.scope is not None: 
                (start_index, end_index) = self.scope
                buffer["scope"] = "{ \"startIndex\": " + f"{start_index}" + ", \"endIndex\": " + f"{end_index}" +  " }"
            else: raise Exception("Property scope is None")

        if (self.action in ["assign", "decl", "invocation", "par", "type"]):
            if self.identifier is not None: 
                buffer["identifier"] = f"\"{self.identifier}\""
            else: raise Exception("Property identifier is None")

        return self.serialize_dict(buffer)

    def serialize_dict(self, dict): 
        items = [f"\"{key}\":{dict[key]}" for key in dict]
        serialized_items = ",".join(items)
        return "{" + serialized_items + "}"

class AssignNotifyData(BaseNotify):
    def __init__(self, node: SourceNode, identifier_node: SourceNode) -> None:
        node_type = node.node.type.spelling
        if not node_type: raise Exception("Type is empty")
        
        super().__init__(node)
        self.action = "assign"
        self.identifier = f"{identifier_node}"
        self.type = node_type

    def get_notify_parameters(self) -> list[str]:
        return ["&" + self.identifier]

class DeclNotifyData(BaseNotify):
    def __init__(self, node: SourceNode) -> None:
        node_type = node.node.type.spelling
        if not node_type: raise Exception("Type is empty")

        super().__init__(node)
        self.action = "decl"
        self.type = node_type
        self.identifier = node.node.spelling
        self.scope = SourceNodeResolver.get_scope(node)
        self.eval_identifier = f"temp{node.id}"

    def get_statement_variables(self) -> list[tuple]: 
        return [VariableDeclaration(self.type, self.eval_identifier)]

    def get_notify_parameters(self) -> list[str]:
        return ["&" + self.identifier]

class EvalNotifyData(BaseNotify):
    def __init__(self, node: SourceNode) -> None:
        node_type = node.node.type.spelling
        if not node_type: raise Exception("Type is empty")

        super().__init__(node)
        self.action = "eval"
        self.type = node_type
        self.eval_identifier = f"temp{node.id}"

    def get_block_variables(self) -> list[tuple]: 
        return [VariableDeclaration(self.type, self.eval_identifier)]

    def get_notify_parameters(self) -> list[str]:
        return ["&" + self.eval_identifier]

class InvocationNotifyData(BaseNotify):
    def __init__(self, node: SourceNode) -> None:
        node_type = node.node.type.spelling
        if not node_type: raise Exception("Type is empty")

        super().__init__(node)
        self.action = "invocation"
        self.type = node_type
        self.identifier = node.node.spelling

class ParameterNotifyData(BaseNotify):
    def __init__(self, node: SourceNode) -> None:
        node_type = node.node.type.spelling
        if not node_type: raise Exception("Type is empty")

        super().__init__(node)
        self.action = "par"
        self.type = node_type
        self.identifier = node.node.spelling
        self.scope = SourceNodeResolver.get_scope(node)

    def get_block_variables(self) -> list[tuple]: 
        return []

    def get_notify_parameters(self) -> list[str]:
        return ["&" + self.identifier]

class ReturnNotifyData(BaseNotify):
    def __init__(self, node: SourceNode) -> None:
        node_type = node.node.type.spelling
        if not node_type: raise Exception("Type is empty")

        super().__init__(node)
        self.action = "return"
        self.type = node_type
        self.eval_identifier = f"temp{node.id}"

    def get_block_variables(self) -> list[tuple]: 
        return [VariableDeclaration(self.type, self.eval_identifier)]

    def get_notify_parameters(self) -> list[str]:
        return ["&" + self.eval_identifier]

class StatNotifyData(BaseNotify): 
    def __init__(self, node: SourceNode) -> None:
        super().__init__(node)
        self.action = "stat"
        self.statement_id = node.id

class TypeNotifyData(BaseNotify):
    def __init__(self, type_identifier: str, temp_identifier) -> None:
        super().__init__(None)
        self.action = "type"
        self.identifier = type_identifier
        self.eval_identifier = temp_identifier

    def get_block_variables(self) -> list[tuple]: 
        return [VariableDeclaration("size_t", self.eval_identifier, "sizeof(" + self.identifier + ")")]

    def get_notify_parameters(self) -> list[str]:
        return ["&" + self.eval_identifier]


# Notify nodes
class NotifyBaseReplaceNode(ReplaceModificationNode):
    def __init__(self, target: SourceNode) -> None:
        assert_type(target, SourceNode)

        super().__init__()
        self.target = target
        self.start_notifies: list[BaseNotify] = []
        self.end_notifies: list[BaseNotify] = []
  
    def is_applicable(self, node: SourceNode) -> bool:
        return node == self.target
    
    def apply(self, node: SourceNode, before_node: InsertModificationNode|None = None,  middle_node: InsertModificationNode|None = None, end_node: InsertModificationNode|None = None): 
        self.update_notify_ids(node)

        # Generate statement expression
        placeholders = []
        
        if before_node is not None: 
            placeholders.append(before_node)

        if any(self.start_notifies):
            placeholders.append(self.get_start_notify())

        if middle_node is not None: 
            placeholders.append(middle_node)
        
        if any(self.end_notifies):
            placeholders.append(self.get_end_notify())
        
        if end_node is not None:  
            placeholders.append(end_node)

        if len(placeholders) > 1: 
            return comma_node_with_parentheses(*placeholders).apply() 
        else: 
            return placeholders[0].apply()

    def update_notify_ids(self, node: SourceNode):
        # Update notify data 
        start_notify_id = f"{node.id * 100 + 1}"
        for notify in self.start_notifies:
            notify.set_notify_id(start_notify_id)

        end_notify_id = f"{node.id * 100 + 2}"
        for notify in self.end_notifies:
            notify.set_notify_id(end_notify_id)

    def get_start_notify(self) -> ConstantNode:
        if not any(self.start_notifies): 
            raise Exception()
        
        start_reference = self.start_notifies[0].notify_id
        start_identifiers = flatten([n.get_notify_parameters() for n in self.start_notifies])
        if start_reference is None: raise Exception(f"notify_id is None on start_notifies")
        parameter_list = [f"{start_reference}"] + start_identifiers
        return ConstantNode(f"notify_{len(start_identifiers)}({', '.join(parameter_list)})")
        
    def get_end_notify(self) -> ConstantNode: 
        if not any(self.end_notifies):
            raise Exception()
        
        end_reference = self.end_notifies[0].notify_id
        end_identifiers = flatten([n.get_notify_parameters() for n in self.end_notifies])
        if end_reference is None: raise Exception(f"notify_id is None on end_notifies")
        parameter_list = [f"{end_reference}"] + end_identifiers
        return ConstantNode(f"notify_{len(end_identifiers)}({', '.join(parameter_list)})")
        
    def clone(self): 
        return copy(self)

    def with_start_notify(self, data: BaseNotify):
        assert_type(data, BaseNotify)
        return self.with_start_notifies([data])

    def with_start_notifies(self, data_list: list[BaseNotify]):
        assert_list_type(data_list, BaseNotify)

        instance = self.clone()
        instance.start_notifies = instance.start_notifies + data_list
        return instance

    def with_end_notify(self, data: BaseNotify):
        assert_type(data, BaseNotify)
        return self.with_end_notifies([data])
    
    def with_end_notifies(self, data_list: list[BaseNotify]):
        assert_list_type(data_list, BaseNotify)

        instance = self.clone()
        instance.end_notifies = instance.end_notifies + data_list
        return instance
    
    def __str__(self) -> str:
        return f"{type(self).__name__}(target = \"{self.target}\", start_notifies = [{len(self.start_notifies)} items], end_notifies = [{len(self.end_notifies)} items])"

# Transforms id = 5 to id = (notify(), 5), temp = (notify(), id)
class NestedExprNotifyReplaceNode(NotifyBaseReplaceNode):
    def __init__(self, target: SourceNode, value: InsertModificationNode) -> None:
        assert_type(target, SourceNode)
        assert_type(value, InsertModificationNode)

        super().__init__(target)
        self.value = value

    def apply(self, node: SourceNode) -> SourceNode:
        self.update_notify_ids(node)

        if any(self.start_notifies) or any(self.end_notifies):
            # Temp variable assignment
            variable = flatten(n.get_statement_variables() for n in self.end_notifies)[0]
            temp_declaration = variable.get_declaration_part()
            if any(self.end_notifies):
                temp_value = comma_node_with_parentheses(
                    self.get_end_notify(),
                    ConstantNode(node.node.spelling)
                )
                pass
            else: 
                temp_value = ConstantNode(node.node.spelling)

            return comma_node(
                CopyNode(node), 
                assignment_node(ConstantNode(temp_declaration), temp_value)
            ).apply()
        else: 
            return node

# Transforms void_expr to notify(), void_expr, notify()
class NotifyVoidReplaceNode(NotifyBaseReplaceNode):
    def __init__(self, target: SourceNode) -> None:
        super().__init__(target)

    def apply(self, node: SourceNode) -> SourceNode:
        return super().apply(node, middle_node=CopyNode(node))

# Transforms expr to notify(), temp = expr, notify(), temp
class ExprNotifyReplaceNode(NotifyBaseReplaceNode):
    def __init__(self, target: SourceNode) -> None:
        super().__init__(target) 

    def apply(self, node: SourceNode) -> SourceNode:
        if any(self.end_notifies):
            variable_name = next(n for n in self.end_notifies if n.eval_identifier is not None).eval_identifier
            variable_node = ConstantNode(variable_name)
            value_node = assignment_node(
                ConstantNode(variable_name), 
                CopyNode(node)
            )
        else: 
            variable_node = None
            value_node = CopyNode(node)
        
        return super().apply(node, middle_node=value_node, end_node=variable_node)

# Transforms stmt; to { notify(); stmt; notify(); }
class StmtNotifyReplaceNode(NotifyBaseReplaceNode):
    def __init__(self, target: SourceNode) -> None:
        super().__init__(target)
    
    def apply(self, node: SourceNode) -> SourceNode:
        self.update_notify_ids(node)

        placeholders = []
        if any(self.start_notifies): 
            placeholders.append(self.get_start_notify())
        
        placeholders.append(CopyNode(node))

        if any(self.end_notifies):
            placeholders.append(self.get_end_notify())

        if len(placeholders) > 1: 
            templates = ["{ {0}; }", "{ {0}; {1}; }", "{ {0}; {1}; {2}; }"]
            return TemplatedNode(templates[len(placeholders) - 1], placeholders).apply() 
        else: 
            return placeholders[0].apply()
        
# Transforms compound_expr to notify(), compound_expr, notify() 
class CompoundVoidNotifyReplaceNode(NotifyBaseReplaceNode):
    def __init__(self, target: SourceNode, children: list[NotifyBaseReplaceNode]) -> None:
        super().__init__(target)
        self.children = children

    def apply(self, node: SourceNode) -> SourceNode:
        value_node = CopyReplaceNode(
            node, 
            self.children
        )
        return super().apply(node, middle_node=value_node)
    
    def get_children(self) -> list[ModificationNode]:
        return self.children

# Transforms compound_expr to notify(), temp = compound_expr, notify(), temp
class CompoundExprNotifyReplaceNode(NotifyBaseReplaceNode):
    def __init__(self, target: SourceNode, children: list[NotifyBaseReplaceNode]) -> None:
        assert_type(target, SourceNode)
        #assert_list_type(children, NotifyBaseReplaceNode)

        super().__init__(target)
        self.children = children

    def apply(self, node: SourceNode) -> SourceNode:
        if any(self.end_notifies):
            variable_name = next(n for n in self.end_notifies if n.eval_identifier is not None).eval_identifier
            variable_node = ConstantNode(variable_name)
            value_node = TemplatedNode(
                "{0} = {1}",
                [
                    ConstantNode(variable_name),
                    CopyReplaceNode(node, self.children)
                ]
            ) 
        else: 
            variable_node = None
            value_node = CopyReplaceNode(
                node, 
                self.children
            )
        return super().apply(node, middle_node=value_node, end_node=variable_node)
    
    def get_children(self) -> list[ModificationNode]:
        return self.children
        
# Transforms compound_1; compound_2; to notify(), compound_1; notify(), compound_2;
class CompoundNotifyReplaceNode(NotifyBaseReplaceNode):
    def __init__(self, target: SourceNode, children: list[NotifyBaseReplaceNode]) -> None:
        super().__init__(target)
        self.children = children

    def apply(self, node: SourceNode) -> SourceNode:
        new_children = []
        children = self.get_children()
        if len(children) == 0: 
            return node
        elif len(children) == 1:
            new_children.append(self.apply_to_end(self.apply_to_first(self.children[0])))
        else: 
            new_children.append(self.apply_to_first(self.children[0]))
            new_children.extend(self.children[1:-1])
            new_children.append(self.apply_to_end(self.children[-1]))

        return CompoundReplaceNode(node, new_children).apply(node)

    def apply_to_first(self, node): 
        return node.with_start_notifies(self.start_notifies) if any(self.start_notifies) else node
    
    def apply_to_end(self, node):
        return node.with_end_notifies(self.end_notifies) if any(self.end_notifies) else node

    def get_children(self) -> list[ModificationNode]:
        return self.children