import re
from source_nodes import SourceNode, SourceToken

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
    def isApplicable(self, node: SourceNode) -> bool:
        return False
    def apply(self, node: SourceNode) -> SourceNode:
        raise Exception("Not implemented")
    
    def getChildren(self) -> list['ModificationNode']:
        return []

class ConstantNode(ModificationNode):
    def __init__(self, value: str) -> None:
        super().__init__()
        self.value = value

    def isApplicable(self, node: SourceNode) -> bool:
        """Constant nodes are not connected to source tree and can therefore not be applied to it""" 
        return False
    
    def apply(self, node: SourceNode) -> SourceNode:
        return SourceNode.create(None, self.value, [], [])

class CopyNode(ModificationNode):
    def __init__(self, source: SourceNode) -> None:
        super().__init__()
        self.source = source
    
    def isApplicable(self, node: SourceNode) -> bool:
        """Copy nodes are not connected to source tree and can therefore not be applied to it""" 
        return False 
    
    def apply(self, node: SourceNode) -> SourceNode:
        return SourceNode.copy(self.source)

class CompoundNode(ModificationNode):
    def __init__(self, target: SourceNode|None, modifications: list[ModificationNode]) -> None:
        super().__init__()
        self.target = target
        self.modifications = modifications

    def isApplicable(self, node: SourceNode) -> bool:
        """If no target is specified, finds last common ancestor of modification-applicable nodes"""
        if self.target is not None:
            return SourceNode.equals(node, self.target)
        
        # Verifies that all modifications are applicable to current node
        if not CompoundNode.isApplicableCommonAncestor(node, self.modifications): 
            return False
        
        # Verifies that all modifications are not applicable to any children 
        for child in node.children: 
            if CompoundNode.isApplicableCommonAncestor(child, self.modifications):
                return False
        
        self.target = node
        return True

    def apply(self, node: SourceNode) -> SourceNode:
        new_children = [self.apply(c) for c in node.children]
        new_source_node = SourceNode.copy(node)
        new_source_node.children = new_children

        modification = next((m for m in self.modifications if m.isApplicable(node)), None)
        if modification is not None:
            return modification.apply(new_source_node) 
        else: 
            return node

    @staticmethod
    def isApplicableCommonAncestor(node, modifications: list[ModificationNode]):
        for modifications in modifications:
            if not CompoundNode.isAnyDescendantApplicable(node, modifications):
                return False
            
        return True

    @staticmethod
    def isAnyDescendantApplicable(node: SourceNode, modification: ModificationNode):
        if modification.isApplicable(node):
            return True

        for child in node.children:
            if CompoundNode.isAnyDescendantApplicable(child, modification):
                return True
            
        return False

class ReplaceNode(ModificationNode):
    def __init__(self, target: SourceNode, replacement: ModificationNode) -> None:
        super().__init__() 
        self.target = target
        self.replacement = replacement

    def isApplicable(self, node: SourceNode) -> bool:
        return SourceNode.equals(node, self.target)
    
    def apply(self, node: SourceNode) -> SourceNode:
        return self.replacement.apply(node)
    
    def getChildren(self) -> list[ModificationNode]:
        return [self.replacement]

class ReplaceTokenNode(ModificationNode): 
    """Replaces identififer token that is part of target node"""
    def __init__(self, targetNode: SourceNode, targetToken, replacement: ModificationNode) -> None:
        super().__init__()
        self.targetNode = targetNode
        self.targetToken = targetToken
        self.replacement = replacement

        if not any(t for t in targetNode.node_tokens if t == targetToken):
            raise Exception(f"Target node {targetNode.id} does not contain target token")
        
    def isApplicable(self, node: SourceNode) -> bool:
        return SourceNode.equals(node, self.targetNode)
    
    def apply(self, target: SourceNode) -> SourceNode:
        return SourceNode.replace_token(target, self.targetToken, self.replacement)
    
    def getChildren(self) -> list[ModificationNode]:
        return [self.replacement]

class ReplaceTokenKindNode(ReplaceTokenNode):
    def __init__(self, targetNode: SourceNode, targetTokenKind: str, replacement: ModificationNode) -> None:
        targetToken = next((t for t in targetNode.node_tokens if get_token_kind(t) == targetTokenKind), None)
        if targetNode is None: 
            raise Exception(f"Target node {targetNode.id} does not contain token of kind {targetTokenKind}")
        super().__init__(targetNode, targetToken, replacement)

class ReplaceChildrenNode(ModificationNode): 
    def __init__(self, target: SourceNode, replacements: list[ModificationNode]) -> None:
        super().__init__()
        self.target = target
        self.replacements = replacements

        number_of_children = len(target.children)
        if number_of_children != len(replacements):
            raise Exception(f"Expected {number_of_children} number of replacements")
        
    def isApplicable(self, node: SourceNode) -> bool:
        return SourceNode.equals(node, self.target)
    
    def apply(self, node: SourceNode) -> SourceNode:
        new_children = []
        for i in range(0, len(node.children)): 
            new_child = self.replacements[i].apply(node.children[i])
            new_children.append(new_child)

        new_node = SourceNode.copy(node)
        new_node.children = new_children
        return new_node
    
    def getChildren(self) -> list[ModificationNode]:
        return self.replacements

class TemplatedNode(ModificationNode):
    def __init__(self, template: str, replacements: list[ModificationNode]) -> None:
        super().__init__()
        self.template = template
        self.replacements = replacements

    def isApplicable(self, node: SourceNode) -> bool:
        """Templated nodes are not connected to source tree and can therefore not be applied to it""" 
        return False 
    
    def apply(self, node: SourceNode) -> SourceNode:
        new_children = [r.apply(node) for r in self.replacements]
        return SourceNode.create(None, self.template, [], new_children)
    
    def getChildren(self) -> list[ModificationNode]:
        return self.replacements
    
class TemplatedReplaceNode(ModificationNode): 
    def __init__(self, target: SourceNode, template: str, replacements: list[ModificationNode]) -> None:
        super().__init__()
        self.target = target
        self.template = template
        self.replacements = replacements

    def isApplicable(self, node: SourceNode) -> bool:
        return SourceNode.equals(node, self.target)
    
    def apply(self, node: SourceNode) -> SourceNode:
        new_children = [r.apply(node) for r in self.replacements]
        return SourceNode.create(None, self.template, [], new_children)
    
    def getChildren(self) -> list[ModificationNode]:
        return self.replacements

class InsertAfterTokenNode(ModificationNode): 
    """Replaces identififer token that is part of target node"""
    def __init__(self, targetNode: SourceNode, targetToken, insertions: ModificationNode|list[ModificationNode]) -> None:
        super().__init__()
        self.targetNode = targetNode
        self.targetToken = targetToken
        self.insertions = insertions

        if not any(t for t in targetNode.get_tokens() if t == targetToken):
            raise Exception(f"Target node {targetNode.id} does not contain target token")
        
    def isApplicable(self, node: SourceNode) -> bool:
        return SourceNode.equals(node, self.targetNode)
    
    def apply(self, target: SourceNode) -> SourceNode:
        insertion_texts = [f"{i.apply(target)}" for i in self.insertions]
        insertion_nodes = [SourceToken.create(None, t) for t in insertion_texts]
        insertion_nodes.reverse()

        buffer = target
        for insertion_node in insertion_nodes: 
            buffer = SourceNode.insert_after_token(buffer, self.targetToken, insertion_node)
        return buffer
    
    def getChildren(self) -> list[ModificationNode]:
        return [self.replacement]

# Composite nodes 
class InsertAfterTokenKindNode(InsertAfterTokenNode):
    def __init__(self, targetNode: SourceNode, targetTokenKind: str, insertion: ModificationNode) -> None:
        targetToken = next((t for t in targetNode.node_tokens if get_token_kind(t) == targetTokenKind), None)
        if targetNode is None: 
            raise Exception(f"Target node {targetNode.id} does not contain token of kind {targetTokenKind}")
        
        super().__init__(targetNode, targetToken, insertion)

class InsertBeforeStatementsNode(InsertAfterTokenNode):
    """Inserts insertions just after openening brackets"""
    def __init__(self, target: SourceNode, insertions: ModificationNode|list[ModificationNode]):
        first_token = target.get_tokens()[0]
        insertions = insertions if isinstance(insertions, list) else [insertions]

        super().__init__(target, first_token, insertions)

# Node creation functions 
# Template functions are recursive by default
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