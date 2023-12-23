from copy import copy
from modification_nodes import CompoundReplaceNode, ConstantNode, CopyNode, CopyReplaceNode, InsertModificationNode, ReplaceModificationNode, TemplatedNode, TemplatedReplaceNode, assert_list_type, assert_type, assignment_node, comma_node_with_parentheses
from source_nodes import SourceNode, SourceNodeResolver

# See https://stackoverflow.com/questions/952914/how-do-i-make-a-flat-list-out-of-a-list-of-lists
def flatten(l):
    return [item for sublist in l for item in sublist]

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
        
    def get_identifiers(self) -> list[str]: 
        return []

    def serialize(self, code):
        buffer = dict()

        if self.id is not None: 
            buffer["id"] = f"{self.id}"
        else: raise Exception("Property id is None")
        
        if self.action is not None: 
            buffer["action"] = f"\"{self.action}\""
        else: raise Exception("Property action is None")

        if self.node_id is not None: 
            buffer["nodeId"] = f"{self.node_id}"
        else: raise Exception("Property node_id is None")
        
        if self.notify_id is not None: 
            buffer["notifyId"] = f"{self.notify_id}" if self.notify_id is not None else "undefined"
        else: raise Exception("Property notify_id is None")

        if (self.action in ["assign", "eval", "decl", "return", "invocation", "par"]):
            if self.type is not None:
                buffer["dataType"] = f"\"{self.type}\""
            else: raise Exception("Property type is None")
        
        if (self.action in ["decl", "par"]):
            if self.scope is not None: 
                (start_index, end_index) = self.scope
                buffer["scope"] = "{ \"startIndex\": " + f"{start_index}" + ", \"endIndex\": " + f"{end_index}" +  " }"
            else: raise Exception("Property scope is None")

        if (self.action in ["assign", "decl", "invocation", "par"]):
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

    def get_identifiers(self) -> list[str]:
        return [self.identifier]

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

    def get_identifiers(self) -> list[str]:
        return [self.eval_identifier]

class EvalNotifyData(BaseNotify):
    def __init__(self, node: SourceNode) -> None:
        node_type = node.node.type.spelling
        if not node_type: raise Exception("Type is empty")

        super().__init__(node)
        self.action = "eval"
        self.type = node_type
        self.eval_identifier = f"temp{node.id}"

    def get_identifiers(self) -> list[str]:
        return [self.eval_identifier]

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

    def get_identifiers(self) -> list[str]:
        return [self.identifier]

class ReturnNotifyData(BaseNotify):
    def __init__(self, node: SourceNode) -> None:
        node_type = node.node.type.spelling
        if not node_type: raise Exception("Type is empty")

        super().__init__(node)
        self.action = "return"
        self.type = node_type
        self.eval_identifier = f"temp{node.id}"

    def get_identifiers(self) -> list[str]:
        return [self.eval_identifier]

class StatNotifyData(BaseNotify): 
    def __init__(self, node: SourceNode) -> None:
        super().__init__(node)
        self.action = "stat"
        self.statement_id = node.id

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
        start_identifiers = flatten([n.get_identifiers() for n in self.start_notifies])
        end_identifiers = flatten([n.get_identifiers() for n in self.end_notifies])

        if before_node is not None: 
            placeholders.append(before_node)

        if any(self.start_notifies): 
            start_reference = self.start_notifies[0].notify_id
            if start_reference is None: raise Exception(f"notify_id is None on start_notifies")
            list_1 = [f"&{i}" for i in start_identifiers]
            list_2 = [f"{start_reference}"] + list_1
            placeholders.append(ConstantNode(f"notify_{len(start_identifiers)}({', '.join(list_2)})"))
        
        if middle_node is not None: 
            placeholders.append(middle_node)
        
        if any(self.end_notifies):
            end_reference = self.end_notifies[0].notify_id
            if end_reference is None: raise Exception(f"notify_id is None on end_notifies")
            list_1 = [f"&{i}" for i in end_identifiers]
            list_2 = [f"{end_reference}"] + list_1
            placeholders.append(ConstantNode(f"notify_{len(end_identifiers)}({', '.join(list_2)})"))
        
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

# Transforms expr to expr = notify(), temp, notify(), temp
class PreExprNotifyReplaceNode(NotifyBaseReplaceNode):
    def __init__(self, target: SourceNode) -> None:
        super().__init__(target)

    def with_start_notify(self, data: BaseNotify):
        return self.with_end_notify(data)
    
    def with_start_notifies(self, data_list: list[BaseNotify]):
        return self.with_end_notifies(data_list)

    def apply(self, node: SourceNode) -> SourceNode:
        if any(self.end_notifies):
            variable_name = next(n for n in self.end_notifies if n.eval_identifier is not None).eval_identifier
            expression_value = f"{super().apply(node, middle_node=ConstantNode(variable_name), end_node=ConstantNode(variable_name))}"
           
            return assignment_node(
                CopyNode(node),
                ConstantNode(expression_value)
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
            start_reference = self.start_notifies[0].get_reference()
            placeholders.append(ConstantNode(f"notify_0({start_reference})"))
        
        placeholders.append(CopyNode(node))

        if any(self.end_notifies):
            end_reference = self.end_notifies[0].get_reference()
            placeholders.append(ConstantNode(f"notify_0({end_reference})"))

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

# Transforms compound_expr to notify(), temp = compound_expr, notify(), temp
class CompoundExprNotifyReplaceNode(NotifyBaseReplaceNode):
    def __init__(self, target: SourceNode, children: list[NotifyBaseReplaceNode]) -> None:
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
        
# Transforms compound_1; compound_2; to notify(), compound_1; notify(), compound_2;
class CompoundNotifyReplaceNode(NotifyBaseReplaceNode):
    def __init__(self, target: SourceNode, children: list[NotifyBaseReplaceNode]) -> None:
        super().__init__(target)
        self.children = children

    def apply(self, node: SourceNode) -> SourceNode:
        if not any(self.start_notifies) and not any(self.end_notifies):
            return node
        
        new_children = []
        new_children.append(self.children[0].with_start_notifies(self.start_notifies) if any(self.start_notifies) else self.children[0])
        new_children.extend(self.children[1:-1])
        new_children.append(self.children[-1].with_end_notifies(self.end_notifies) if any(self.end_notifies) else self.children[-1])

        return CompoundReplaceNode(node, new_children).apply(node)
