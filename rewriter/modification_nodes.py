import re
from assertions import assert_type, assert_type_or_none, assert_list_type
from source_nodes import SourceNode, SourceNodeResolver, SourceText, SourceToken

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
    
    def __str__(self) -> str:
        return f"{type(self).__name__}()"

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
        assert_type(value, str)

        super().__init__()
        self.value = value
    
    def apply(self) -> SourceNode:
        return SourceText.create(None, None, self.value)
    
    def __str__(self) -> str:
        return f"{type(self).__name__}(value = \"{self.value}\")"

class CopyNode(InsertModificationNode):
    def __init__(self, source: SourceNode) -> None:
        assert_type(source, SourceNode)

        super().__init__()
        self.source = source
    
    def apply(self) -> SourceNode:
        return SourceNode.copy(self.source)
    
    def __str__(self) -> str:
        return f"{type(self).__name__}(source = \"{self.source}\")"

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
        assert_type(source_node, SourceNode)

        # Depth first replacement
        children = source_node.get_children()
        new_children = [self.apply_to(c) for c in children]
        new_source_node = SourceNode.replace_values(source_node, children, new_children)

        replacement_node = next((r for r in self.replacements if r.is_applicable(source_node)), None)

        # Apply modification if found
        if replacement_node is not None:
            return replacement_node.apply(new_source_node) 
        else: 
            return new_source_node

    def get_children(self) -> list[ModificationNode]:
        return self.replacements
    
    def with_child(self, target, replacement) -> 'CopyReplaceNode': 
        assert_type(target, SourceNode)
        assert_type(replacement, ReplaceModificationNode)

        children = [(replacement if c == target else c) for c in self.replacements]
        return CopyReplaceNode(self.source, children)

    def __str__(self) -> str:
        return f"{type(self).__name__}(source = \"{self.source}\", replacements=[{len(self.replacements)} item(s)])"

class TemplatedNode(InsertModificationNode):
    def __init__(self, template: str, insertions: list[InsertModificationNode]) -> None:
        assert_type(template, str)
        assert_list_type(insertions, InsertModificationNode)

        super().__init__()
        self.template = template
        self.insertions = insertions

    def apply(self) -> SourceNode:
        template_values = [n.apply() for n in self.insertions]
        return SourceNode.create_from_template(self.template, template_values)
    
    def get_children(self) -> list[ModificationNode]:
        return self.insertions
    
    def __str__(self) -> str:
        return f"{type(self).__name__}(template = {self.template}, insertions = [{len(self.template)} items])"

# Replace nodes
class ReplaceNode(ReplaceModificationNode):
    def __init__(self, target: SourceNode, insertion: InsertModificationNode) -> None:
        assert_type(target, SourceNode)
        assert_type(insertion, InsertModificationNode)

        super().__init__() 
        self.target = target
        self.replacement = insertion

    def is_applicable(self, node: SourceNode) -> bool:
        assert_type(node, SourceNode)
        return SourceNode.equals(node, self.target)
    
    def apply(self, node: SourceNode) -> SourceNode:
        return self.replacement.apply()
    
    def get_children(self) -> list[ModificationNode]:
        return [self.replacement]
    
    def __str__(self) -> str:
        return f"{type(self).__name__}(target = \"{self.target}\", insertion = \"{self.insertion}\")"

class ReplaceTokenNode(ReplaceModificationNode): 
    """Replaces identififer token that is part of target node"""
    def __init__(self, targetNode: SourceNode, targetToken: SourceToken, insertion: InsertModificationNode) -> None:
        assert_type(targetNode, SourceNode)
        assert_type(targetToken, SourceToken)
        assert_type(insertion, InsertModificationNode)
        
        super().__init__()
        self.targetNode = targetNode
        self.targetToken = targetToken
        self.insertion = insertion

        if not any(t for t in targetNode.get_tokens() if t == targetToken):
            raise Exception(f"Target node {targetNode.id} does not contain target token")
        
    def is_applicable(self, node: SourceNode) -> bool:
        assert_type(node, SourceNode)
        return SourceNode.equals(node, self.targetNode)
    
    def apply(self, target: SourceNode) -> SourceNode:
        assert_type(target, SourceNode)
        return SourceNode.replace_value(target, self.targetToken, self.insertion)
    
    def get_children(self) -> list[ModificationNode]:
        return [self.insertion]
    
    def __str__(self) -> str:
        return f"{type(self).__name__}(targetNode = \"{self.targetNode}\", targetToken = \"{self.targetToken}\", insertion = \"{self.insertion}\")"

class ReplaceTokenKindNode(ReplaceTokenNode):
    def __init__(self, targetNode: SourceNode, targetTokenKind: str, replacement: ModificationNode) -> None:
        targetToken = next((t for t in targetNode.get_tokens() if get_token_kind(t) == targetTokenKind), None)
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
        assert_type(node, SourceNode)
        return SourceNode.equals(node, self.target)
    
    def apply(self, node: SourceNode) -> SourceNode:
        assert_type(node, SourceNode)

        children = node.get_children()
        new_children = []
        for i in range(0, len(children)): 
            new_child = self.insertions[i].apply()
            new_children.append(new_child)

        return SourceNode.replace_values(node, children, new_children)
    
    def get_children(self) -> list[ModificationNode]:
        return self.insertions
    
    def __str__(self) -> str:
        return f"{type(self).__name__}(target = \"{self.target}\", insertions = [{len(self.insertions)} items])"

class CompoundReplaceNode(ReplaceModificationNode):
    def __init__(self, target: SourceNode|None, modifications: list[ReplaceModificationNode]) -> None:
        assert_type_or_none(target, SourceNode)
        assert_list_type(modifications, ReplaceModificationNode)

        super().__init__()
        self.target = target
        self.modifications = modifications

    def is_applicable(self, node: SourceNode) -> bool:
        # If no target is specified, finds last common ancestor of modification-applicable nodes
        assert_type(node, SourceNode)
        
        if self.target is not None:
            return SourceNode.equals(node, self.target)
        
        # Verifies that all modifications are applicable to current node
        if not CompoundReplaceNode.isApplicableCommonAncestor(node, self.modifications): 
            return False
        
        # Verifies that all modifications are not applicable to any children 
        for child in node.get_children(): 
            if CompoundReplaceNode.isApplicableCommonAncestor(child, self.modifications):
                return False
        
        self.target = node
        return True

    def apply(self, node: SourceNode) -> SourceNode:
        assert_type(node, SourceNode)
        return self.apply_to(node)
    
    def apply_to(self, source_node: SourceNode):
        assert_type(source_node, SourceNode)

        # Depth first replacement
        children = source_node.get_children()
        new_children = [self.apply_to(c) for c in children]
        new_source_node = SourceNode.replace_values(source_node, children, new_children)

        replacement_node = next((r for r in self.modifications if r.is_applicable(source_node)), None)

        # Apply modification if found
        if replacement_node is not None:
            return replacement_node.apply(new_source_node) 
        else: 
            return new_source_node

    def get_children(self) -> list[ModificationNode]:
        return self.modifications

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

        for child in node.get_children():
            if CompoundReplaceNode.isAnyDescendantApplicable(child, modification):
                return True
            
        return False

    def __str__(self) -> str:
        return f"{type(self).__name__}(target = \"{self.target}\", modifications = [{len(self.modifications)} items])"

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
        assert_type(node, SourceNode)
        return SourceNode.equals(node, self.target)
    
    def apply(self, node: SourceNode) -> SourceNode:
        assert_type(node, SourceNode)

        new_children = [r.apply() for r in self.insertions]
        return SourceNode.create_from_template(self.template, new_children)
    
    def get_children(self) -> list[ModificationNode]:
        return self.insertions
    
    def __str__(self) -> str:
        return f"{type(self).__name__}(target = \"{self.target}\", template = \"{self.template}\", insertions = [{len(self.insertions)} items])"

class InsertAfterTokenNode(ReplaceModificationNode): 
    """Replaces identififer token that is part of target node"""
    def __init__(self, targetNode: SourceNode, targetToken: SourceToken, insertion: InsertModificationNode) -> None:
        assert_type(targetNode, SourceNode)
        assert_type(targetToken, SourceToken)
        assert_type(insertion, InsertModificationNode)
        
        super().__init__()
        self.targetNode = targetNode
        self.targetToken = targetToken
        self.insertion = insertion

        if not any(t for t in targetNode.get_tokens() if t == targetToken):
            raise Exception(f"Target node {targetNode.id} does not contain target token")
        
    def is_applicable(self, node: SourceNode) -> bool:
        assert_type(node, SourceNode)
        return SourceNode.equals(node, self.targetNode)
    
    def apply(self, target: SourceNode) -> SourceNode:
        assert_type(target, SourceNode)

        insertion_token = SourceText.create(None, None, f"{self.insertion.apply()}")
        return SourceNode.insert_after_value(target, self.targetToken, insertion_token)
    
    def get_children(self) -> list[ModificationNode]:
        return [self.insertion]
    
    def __str__(self) -> str:
        return f"{type(self).__name__}(targetNode = \"{self.targetNode}\", targetToken = \"{self.targetToken}\", insertion = \"{self.insertion}\")"

class InsertAfterTokenKindNode(InsertAfterTokenNode):
    def __init__(self, targetNode: SourceNode, targetTokenKind: str, insertion: InsertModificationNode) -> None:
        assert_type(targetNode, SourceNode)
        assert_type(targetTokenKind, str)
        assert_type(insertion, InsertModificationNode)

        targetToken = next((t for t in targetNode.get_tokens() if get_token_kind(t.token) == targetTokenKind), None)
        if targetNode is None: 
            raise Exception(f"Target node {targetNode.id} does not contain token of kind {targetTokenKind}")
        
        super().__init__(targetNode, targetToken, insertion)

# Node creation functions 
# Template functions are recursive by default
def copy_replace_node(source: SourceNode, *args: list[ReplaceModificationNode]): 
    return CopyReplaceNode(source, args)

def template_node(template1, template2, *args): 
    if len(args) == 1: 
        raise Exception("Unexpected number of arguments")
    elif len(args) == 2:
        return TemplatedNode(
            template1,
            args
        )
    else: 
        return template_node(
            template1,
            template2,
            template_node(template2, template2, *args[:-1]),
            args[-1]
        )

def template_replace_node(template1, template2, target, *args):
    if len(args) == 1: 
        raise Exception("Unexpected number of arguments")
    elif len(args) == 2:
        return TemplatedReplaceNode(
            target,
            template1,
            args
        )
    else: 
        return template_replace_node(
            template1,
            template2,
            target, 
            template_node(template2, template2, *args[:-1]),
            args[-1],
        )
    
def assignment_node(*args):
    return template_node("{0} = {1}", "{0} = {1}", *args)

def assignment_replace_node(target, *args):
    return template_replace_node("{0} = {1}", "{0} = {1}", target, *args)

def comma_node(*args): 
    return template_node("{0}, {1}", "{0}, {1}", *args)

def comma_node_with_parentheses(*args):
    return template_node("({0}, {1})", "{0}, {1}", *args)

def comma_replace_node(target, *args): 
    return template_replace_node("{0}, {1}", "{0}, {1}", target, *args)

def comma_stmt_node(*args): 
    return template_node("{0}, {1};", "{0}, {1}", *args)

def comma_stmt_replace_node(target, *args): 
    return template_replace_node("{0}, {1};", "{0}, {1}", target, *args) 

def comma_replace_node_with_parentheses(target, *args): 
    return template_replace_node("({0}, {1})", "{0}, {1}", target, *args)

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

# Node-dependent classes 
class ModificationTreePrinter:
    def print(self, node: ModificationNode, level = 0):
        # Recursive print function to traverse the AST
        assert_type(node, ModificationNode)

        print('  ' * level + f"{node}".replace("\n", "\\n"))
        for child in node.get_children(): 
            self.print(child, level + 1)