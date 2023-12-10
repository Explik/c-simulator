from copy import copy
from modification_nodes import ConstantNode, CopyNode, CopyReplaceNode, InsertModificationNode, ReplaceModificationNode, TemplatedNode, TemplatedReplaceNode, assert_list_type, assert_type, assignment_node, comma_node_with_parentheses
from source_nodes import SourceNode, SourceNodeResolver, SourceRange, get_code_indexes

# See https://stackoverflow.com/questions/952914/how-do-i-make-a-flat-list-out-of-a-list-of-lists
def flatten(l):
    return [item for sublist in l for item in sublist]

# Notify data
class BaseNotify():
    def __init__(self, node: SourceNode) -> None:
        self.node = node
        
        self.action: str|None = None
        self.scope: SourceRange|None = None
        self.type:str|None = None
        self.identifier:str|None = None
        self.parameters: list[str]|None = None
        self.eval_identifier: str|None = None
        self.statement_id: str|None = None
        self.reference = "$ref"

    def get_identifiers(self) -> list[str]: 
        return []

    def get_reference(self): 
        return self.reference

    def set_reference(self, reference: str): 
        self.reference = reference

    def serialize(self, code):
        buffer = dict()
        buffer["ref"] = f"{self.reference}"
        buffer["nodeId"] = int(f"{self.reference}"[1:])
        buffer["action"] = f"\"{self.action}\""

        if self.action in ["stat"]: 
            buffer["statementId"] = f"{self.statement_id}"

        if (self.action in ["assign", "eval", "decl", "return", "invocation", "par"]):
            buffer["dataType"] = f"\"{self.type}\""
        
        if (self.action in ["decl", "par"]):
            buffer["scope"] = self.scope.serialize(code)

        if (self.action in ["assign", "decl", "invocation", "par"]):
            buffer["identifier"] = f"\"{self.identifier}\""

        return self.serialize_dict(buffer)

    def serialize_dict(self, dict): 
        items = [f"\"{key}\":{dict[key]}" for key in dict]
        serialized_items = ",".join(items)
        return "{" + serialized_items + "}"

class AssignNotifyData(BaseNotify):
    def __init__(self, node: SourceNode, identifier_node: SourceNode) -> None:
        super().__init__(node)
        self.action = "assign"
        self.identifier = f"{identifier_node}"
        self.type = node.node.type.spelling

    def get_identifiers(self) -> list[str]:
        return [self.identifier]

class DeclNotifyData(BaseNotify):
    def __init__(self, node: SourceNode) -> None:
        super().__init__(node)
        self.action = "decl"
        self.type = node.node.type.spelling
        self.identifier = node.node.spelling
        self.scope = SourceNodeResolver.get_scope(node)
        self.eval_identifier = f"temp{node.id}"

    def get_identifiers(self) -> list[str]:
        return [self.eval_identifier]

class EvalNotifyData(BaseNotify):
    def __init__(self, node: SourceNode) -> None:
        super().__init__(node)
        self.action = "eval"
        self.type = node.node.type.spelling
        self.eval_identifier = f"temp{node.id}"

    def get_identifiers(self) -> list[str]:
        return [self.eval_identifier]

class InvocationNotifyData(BaseNotify):
    def __init__(self, node: SourceNode) -> None:
        super().__init__(node)
        self.action = "invocation"
        self.type = node.node.type.spelling
        self.identifier = node.node.spelling

class ParameterNotifyData(BaseNotify):
    def __init__(self, node: SourceNode) -> None:
        super().__init__(node)
        self.action = "par"
        self.type = node.node.type.spelling
        self.identifier = node.node.spelling
        self.scope = SourceNodeResolver.get_scope(node)

    def get_identifiers(self) -> list[str]:
        return [self.identifier]

class ReturnNotifyData(BaseNotify):
    def __init__(self, node: SourceNode) -> None:
        super().__init__(node)
        self.action = "return"
        self.type = node.node.type.spelling
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
        self.update_notify(node)
        
        # Generate statement expression
        placeholders = []
        start_identifiers = flatten([n.get_identifiers() for n in self.start_notifies])
        end_identifiers = flatten([n.get_identifiers() for n in self.end_notifies])

        if before_node is not None: 
            placeholders.append(before_node)

        if any(self.start_notifies): 
            start_reference = self.start_notifies[0].get_reference()
            list_1 = [f"&{i}" for i in start_identifiers]
            list_2 = [f"{start_reference}"] + list_1
            placeholders.append(ConstantNode(f"notify_{len(start_identifiers)}({', '.join(list_2)})"))
        
        if middle_node is not None: 
            placeholders.append(middle_node)
        
        if any(self.end_notifies):
            end_reference = self.end_notifies[0].get_reference()
            list_1 = [f"&{i}" for i in end_identifiers]
            list_2 = [f"{end_reference}"] + list_1
            placeholders.append(ConstantNode(f"notify_{len(end_identifiers)}({', '.join(list_2)})"))
        
        if end_node is not None:  
            placeholders.append(end_node)

        if len(placeholders) > 1: 
            return comma_node_with_parentheses(*placeholders).apply() 
        else: 
            return placeholders[0].apply()
        
    def update_notify(self, node: SourceNode):
        # Update notify data 
        start_reference = f"{1000 + node.id}"
        for notify in self.start_notifies:
            notify.set_reference(start_reference)

        end_reference = f"{2000 + node.id}"
        for notify in self.end_notifies:
            notify.set_reference(end_reference)

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
        self.update_notify(node)

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
        
