import re
from source_nodes import SourceNode, SourceToken

def assert_type(obj, type): 
    assert isinstance(obj, type), f"{obj} is not of type {type}"

def assert_list_type(obj, item_type):
    is_list = isinstance(obj, tuple) or isinstance(obj, list)
    assert is_list and all([isinstance(i, item_type) for i in obj]), f"{obj} is not of type {item_type}"

# Based on https://stackoverflow.com/questions/952914/how-do-i-make-a-flat-list-out-of-a-list-of-lists
def flatten(l):
    return [item for sublist in l for item in sublist]

def get_token_kind(token):
    return token.kind.name.lower()

def get_token_equals(token1, token2): 
    """Verifies that token has same spelling and location"""
    (start1, end1) = token1.extent
    (start2, end2) = token2.extent
    isEqualExtent = start1.line == start2.line and start1.column == start2.column and end1.line == end2.line and end1.column == end2.line
    return token1.spelling == token2 and isEqualExtent
        
# Basic nodes
class ModificationNode():
    def get_children(self) -> list['ModificationNode']:
        return []

class InsertModificationNode(ModificationNode):
    def apply(self) -> SourceNode:
        raise Exception("Not implemented")
    
class ReplaceModificationNode(ModificationNode):
    def is_applicable(self, node: SourceNode) -> bool:
        return False
    def apply(self, node: SourceNode) -> SourceNode:
        raise Exception("Not implemented")

# Insert nodes
class ConstantNode(InsertModificationNode):
    def __init__(self, value: str) -> None:
        assert isinstance(value, str)

        super().__init__()
        self.value = value
    
    def apply(self) -> SourceNode:
        return SourceNode.create(None, self.value, [], [])

class CopyNode(InsertModificationNode):
    def __init__(self, source: SourceNode) -> None:
        assert isinstance(source, SourceNode)

        super().__init__()
        self.source = source
    
    def apply(self) -> SourceNode:
        return SourceNode.copy(self.source)

class CopyReplaceNode(InsertModificationNode):
    def __init__(self, source: SourceNode, replacements: list[ReplaceModificationNode]) -> None:
        assert_type(source, SourceNode)
        assert_list_type(replacements, ReplaceModificationNode)

        super().__init__()
        self.source = source
        self.replacements = replacements

    def apply(self) -> SourceNode:
        return self.apply_to(self.source)
    
    def apply_to(self, source_node: SourceNode):
        # Depth first replacement
        new_children = [self.apply_to(c) for c in source_node.get_children()]
        new_source_node = SourceNode.copy(source_node)
        new_source_node.children = new_children

        replacement_node = next((r for r in self.replacements if r.is_applicable(source_node)), None)

        # Apply modification if found
        if replacement_node is not None:
            return replacement_node.apply(new_source_node) 
        else: 
            return new_source_node

    def get_children(self) -> list[ModificationNode]:
        return self.replacements

class TemplatedNode(InsertModificationNode):
    def __init__(self, template: str, insertions: list[InsertModificationNode]) -> None:
        assert_type(template, str)
        assert_list_type(insertions, InsertModificationNode)

        super().__init__()
        self.template = template
        self.insertions = insertions

    def apply(self) -> SourceNode:
        template_values = [n.apply() for n in self.insertions]
        return SourceNode.create(None, self.template, [], template_values)
    
    def get_children(self) -> list[ModificationNode]:
        return self.insertions

# Replace nodes
class ReplaceNode(ReplaceModificationNode):
    def __init__(self, target: SourceNode, insertion: InsertModificationNode) -> None:
        assert_type(target, SourceNode)
        assert_type(insertion, InsertModificationNode)

        super().__init__() 
        self.target = target
        self.replacement = insertion

    def is_applicable(self, node: SourceNode) -> bool:
        return SourceNode.equals(node, self.target)
    
    def apply(self, node: SourceNode) -> SourceNode:
        return self.replacement.apply(node)
    
    def get_children(self) -> list[ModificationNode]:
        return [self.replacement]

class ReplaceTokenNode(ReplaceModificationNode): 
    """Replaces identififer token that is part of target node"""
    def __init__(self, targetNode: SourceNode, targetToken, insertion: InsertModificationNode) -> None:
        assert_type(targetNode, SourceNode)
        assert_type(insertion, InsertModificationNode)
        
        super().__init__()
        self.targetNode = targetNode
        self.targetToken = targetToken
        self.insertion = insertion

        if not any(t for t in targetNode.node_tokens if t == targetToken):
            raise Exception(f"Target node {targetNode.id} does not contain target token")
        
    def is_applicable(self, node: SourceNode) -> bool:
        return SourceNode.equals(node, self.targetNode)
    
    def apply(self, target: SourceNode) -> SourceNode:
        return SourceNode.replace_token(target, self.targetToken, self.insertion)
    
    def get_children(self) -> list[ModificationNode]:
        return [self.insertion]

class ReplaceTokenKindNode(ReplaceTokenNode):
    def __init__(self, targetNode: SourceNode, targetTokenKind: str, replacement: ModificationNode) -> None:
        targetToken = next((t for t in targetNode.node_tokens if get_token_kind(t) == targetTokenKind), None)
        if targetNode is None: 
            raise Exception(f"Target node {targetNode.id} does not contain token of kind {targetTokenKind}")
        super().__init__(targetNode, targetToken, replacement)

class ReplaceChildrenNode(ReplaceModificationNode): 
    def __init__(self, target: SourceNode, insertions: list[InsertModificationNode]) -> None:
        assert_type(target, SourceNode)
        assert_list_type(insertions, InsertModificationNode)
        
        super().__init__()
        self.target = target
        self.insertions = insertions

        number_of_children = len(target.children)
        if number_of_children != len(insertions):
            raise Exception(f"Expected {number_of_children} number of replacements")
        
    def is_applicable(self, node: SourceNode) -> bool:
        return SourceNode.equals(node, self.target)
    
    def apply(self, node: SourceNode) -> SourceNode:
        new_children = []
        for i in range(0, len(node.children)): 
            new_child = self.insertions[i].apply()
            new_children.append(new_child)

        new_node = SourceNode.copy(node)
        new_node.children = new_children
        return new_node
    
    def get_children(self) -> list[ModificationNode]:
        return self.insertions

class CompoundReplaceNode(ReplaceModificationNode):
    def __init__(self, target: SourceNode|None, modifications: list[ReplaceModificationNode]) -> None:
        assert_type(target, SourceNode)
        assert_list_type(modifications, ReplaceModificationNode)

        super().__init__()
        self.target = target
        self.modifications = modifications

    def is_applicable(self, node: SourceNode) -> bool:
        """If no target is specified, finds last common ancestor of modification-applicable nodes"""
        if self.target is not None:
            return SourceNode.equals(node, self.target)
        
        # Verifies that all modifications are applicable to current node
        if not CompoundReplaceNode.isApplicableCommonAncestor(node, self.modifications): 
            return False
        
        # Verifies that all modifications are not applicable to any children 
        for child in node.children: 
            if CompoundReplaceNode.isApplicableCommonAncestor(child, self.modifications):
                return False
        
        self.target = node
        return True

    def apply(self, node: SourceNode) -> SourceNode:
        new_children = [self.apply(c) for c in node.children]
        new_source_node = SourceNode.copy(node)
        new_source_node.children = new_children

        modification = next((m for m in self.modifications if m.is_applicable(node)), None)
        if modification is not None:
            return modification.apply(new_source_node) 
        else: 
            return node

    @staticmethod
    def isApplicableCommonAncestor(node, modifications: list[ModificationNode]):
        for modifications in modifications:
            if not CompoundReplaceNode.isAnyDescendantApplicable(node, modifications):
                return False
            
        return True

    @staticmethod
    def isAnyDescendantApplicable(node: SourceNode, modification: ModificationNode):
        if modification.is_applicable(node):
            return True

        for child in node.children:
            if CompoundReplaceNode.isAnyDescendantApplicable(child, modification):
                return True
            
        return False

class TemplatedReplaceNode(ReplaceModificationNode): 
    def __init__(self, target: SourceNode, template: str, insertions: list[InsertModificationNode]) -> None:
        assert_type(target, SourceNode)
        assert_type(template, str)
        assert_list_type(insertions, InsertModificationNode)

        super().__init__()
        self.target = target
        self.template = template
        self.insertions = insertions

    def is_applicable(self, node: SourceNode) -> bool:
        return SourceNode.equals(node, self.target)
    
    def apply(self, node: SourceNode) -> SourceNode:
        new_children = [r.apply() for r in self.insertions]
        return SourceNode.create(None, self.template, [], new_children)
    
    def get_children(self) -> list[ModificationNode]:
        return self.insertions

class InsertAfterTokenNode(ReplaceModificationNode): 
    """Replaces identififer token that is part of target node"""
    def __init__(self, targetNode: SourceNode, targetToken, insertions: ModificationNode|list[ModificationNode]) -> None:
        assert_type(targetNode, SourceNode)
        
        super().__init__()
        self.targetNode = targetNode
        self.targetToken = targetToken
        self.insertions = insertions

        if not any(t for t in targetNode.get_tokens() if t == targetToken):
            raise Exception(f"Target node {targetNode.id} does not contain target token")
        
    def is_applicable(self, node: SourceNode) -> bool:
        return SourceNode.equals(node, self.targetNode)
    
    def apply(self, target: SourceNode) -> SourceNode:
        insertion_texts = [f"{i.apply(target)}" for i in self.insertions]
        insertion_nodes = [SourceToken.create(None, t) for t in insertion_texts]
        insertion_nodes.reverse()

        buffer = target
        for insertion_node in insertion_nodes: 
            buffer = SourceNode.insert_after_token(buffer, self.targetToken, insertion_node)
        return buffer
    
    def get_children(self) -> list[ModificationNode]:
        return [self.replacement]

class InsertAfterTokenKindNode(InsertAfterTokenNode):
    def __init__(self, targetNode: SourceNode, targetTokenKind: str, insertion: ModificationNode) -> None:
        targetToken = next((t for t in targetNode.node_tokens if get_token_kind(t) == targetTokenKind), None)
        if targetNode is None: 
            raise Exception(f"Target node {targetNode.id} does not contain token of kind {targetTokenKind}")
        
        super().__init__(targetNode, targetToken, insertion)

# Node creation functions 
# Template functions are recursive by default
def copy_replace_node(source: SourceNode, *args: list[ReplaceModificationNode]): 
    return CopyReplaceNode(source, args)

def template_node(template, *args): 
    if len(args) == 1: 
        raise Exception("Unexpected number of arguments")
    elif len(args) == 2:
        return TemplatedNode(
            template,
            args
        )
    else: 
        return template_node(
            template,
            template_node(template, *args[:-1]),
            args[-1]
        )

def template_replace_node(template, target, *args):
    if len(args) == 1: 
        raise Exception("Unexpected number of arguments")
    elif len(args) == 2:
        return TemplatedReplaceNode(
            target,
            template,
            args
        )
    else: 
        return template_replace_node(
            template,
            target, 
            template_node(template, *args[:-1]),
            args[-1],
        )
    
def assignment_node(*args):
    return template_node("{0} = {1}", *args)

def assignment_replace_node(target, *args):
    return template_replace_node("{0} = {1}", target, *args)

def comma_node(*args): 
    return template_node("{0}, {1}", *args)

def comma_replace_node(target, *args): 
    return template_replace_node("{0}, {1}", target, *args)

def compound_replace_node(target, *args):
    template = "{\n"
    for i in range(0, len(args)):
        template += "  {" + f"{i}" + "}\n" 
    template += "}"

    return TemplatedReplaceNode(
        target,
        template,
        args
    )