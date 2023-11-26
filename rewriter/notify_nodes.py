from copy import copy
from modification_nodes import ConstantNode, CopyNode, CopyReplaceNode, InsertModificationNode, ReplaceModificationNode, TemplatedNode, TemplatedReplaceNode, assert_list_type, assert_type, assignment_node, comma_node_with_parentheses
from source_nodes import SourceNode

# See https://stackoverflow.com/questions/952914/how-do-i-make-a-flat-list-out-of-a-list-of-lists
def flatten(l):
    return [item for sublist in l for item in sublist]

# Notify data
class BaseNotify():
    def __init__(self, node: SourceNode) -> None:
        self.node = node

        self.action: str|None = None
        self.type:str|None = None
        self.identifier:str|None = None
        self.location:str|None = None
        self.eval_identifier: str|None = None
        self.reference = "$ref"

    def get_identifiers(self) -> list[str]: 
        return []

    def get_reference(self): 
        return self.reference

    def set_reference(self, reference: str): 
        self.reference = reference

    def serialize(self):
        buffer = dict()
        buffer["ref"] = f"{self.reference}"
        buffer["action"] = f"\"{self.action}\""

        if (self.action in ["assign", "eval", "decl"]):
            buffer["dataType"] = f"\"{self.type}\""
        
        if (self.action in ["assign", "eval", "stat"]):
            buffer["location"] = f"{self.location}"

        if (self.action in ["assign", "decl"]):
            buffer["identifier"] = f"\"{self.identifier}\""

        items = [f"\"{key}\":{buffer[key]}" for key in buffer]
        serialized_items = ",".join(items)
        return "{" + serialized_items + "}"

class AssignNotifyData(BaseNotify):
    def __init__(self, node: SourceNode, identifier_node: SourceNode) -> None:
        super().__init__(node)
        self.action = "assign"
        self.identifier = f"{identifier_node}"
        self.location = [
            node.node.extent.start.line, 
            node.node.extent.start.column,
            node.node.extent.end.line,
            node.node.extent.end.column - 1
        ]
        self.type = node.node.type.spelling

    def get_identifiers(self) -> list[str]:
        return [self.identifier]

class DeclNotifyData(BaseNotify):
    def __init__(self, node: SourceNode) -> None:
        super().__init__(node)
        self.action = "decl"
        self.type = node.node.type.spelling
        self.identifier = node.node.spelling
        self.eval_identifier = f"temp{node.id}"

    def get_identifiers(self) -> list[str]:
        return [self.eval_identifier]

class EvalNotifyData(BaseNotify):
    def __init__(self, node: SourceNode) -> None:
        super().__init__(node)
        self.action = "eval"
        self.location = [
            node.node.extent.start.line, 
            node.node.extent.start.column,
            node.node.extent.end.line,
            node.node.extent.end.column - 1
        ]
        self.type = node.node.type.spelling
        self.eval_identifier = f"temp{node.id}"

    def get_identifiers(self) -> list[str]:
        return [self.eval_identifier]

class StatNotifyData(BaseNotify): 
    def __init__(self, node: SourceNode) -> None:
        super().__init__(node)
        self.action = "stat"
        self.location = [
            node.node.extent.start.line, 
            node.node.extent.start.column,
            node.node.extent.end.line,
            node.node.extent.end.column - 1
        ]

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
    
    def apply(self, node: SourceNode, middle_node: InsertModificationNode, end_node: InsertModificationNode|None = None): 
        # Update notify data 
        start_reference = f"{1000 + node.id}"
        for notify in self.start_notifies:
            notify.set_reference(start_reference)

        end_reference = f"{2000 + node.id}"
        for notify in self.end_notifies:
            notify.set_reference(end_reference)
        
        # Generate statement expression
        placeholders = []
        identifiers = flatten([n.get_identifiers() for n in self.end_notifies])

        if any(self.start_notifies): 
            placeholders.append(ConstantNode(f"notify_0({start_reference})"))
        
        placeholders.append(middle_node)
        
        if any(self.end_notifies):
            list_1 = [f"&{i}" for i in identifiers]
            list_2 = [f"{end_reference}"] + list_1
            placeholders.append(ConstantNode(f"notify_{len(identifiers)}({', '.join(list_2)})"))
        
        if end_node is not None:  
            placeholders.append(end_node)

        if len(placeholders) > 1: 
            return comma_node_with_parentheses(*placeholders).apply()
        else: 
            return placeholders[0].apply()
        
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

# Transforms void_expr to notify(), void_expr, notify()
class NotifyVoidReplaceNode(NotifyBaseReplaceNode):
    def __init__(self, target: SourceNode) -> None:
        super().__init__(target)

    def apply(self, node: SourceNode) -> SourceNode:
        return super().apply(node, CopyNode(node))

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
        
        return super().apply(node, value_node, variable_node)

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
        return super().apply(node, value_node)

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
        return super().apply(node, value_node, variable_node)
        