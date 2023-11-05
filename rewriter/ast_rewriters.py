import re

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
        
def get_code_index(code, location) -> int: 
    current_l = location.line
    current_c = location.column - 1
    lines = code.split("\n")
    prior_lines = lines[0:current_l]
    if len(prior_lines) > 0:
        prior_lines[-1] = prior_lines[-1][0:current_c]
        return len("\n".join(prior_lines))
    else: 
        return current_c

def get_code_indexes(code, extent) -> (int, int):
    return (get_code_index(code, extent.start), get_code_index(code, extent.end))

# Source tree 
class SourceToken: 
    def __init__(self) -> None:
        self.value = None
        self.token = None

    def __str__(self) -> str:
        return self.value

    @staticmethod
    def create(token, value): 
        t = SourceToken()
        t.value = value 
        t.token = token
        return t

class SourceNode: 
    counter = 0
    
    def get_children(self) -> list['SourceNode']: 
        return self.children
    
    def get_tokens(self) -> list[SourceToken]:
        return self.tokens

    def __eq__(self, node: object) -> bool:
        if isinstance(node, SourceNode): 
            return False
        return self.id == node.id

    def __str__(self) -> str:
        buffer = self.value
        for i in range(0, len(self.tokens)): 
            buffer = buffer.replace("{t"+f"{i}"+"}", f"{self.tokens[i]}")
        for i in range(0, len(self.children)):
            buffer = buffer.replace("{"+f"{i}"+"}", f"{self.children[i]}")
        return buffer
    
    @staticmethod
    def create(node, value, tokens: list[SourceToken], children: list['SourceNode']) -> None:
        SourceNode.counter += 1
        s = SourceNode()
        s.id = SourceNode.counter
        s.node = node
        s.value = value
        s.tokens = tokens
        s.children = children
        return s

    @staticmethod
    def copy(source: 'SourceNode'): 
        s = SourceNode()
        s.id = source.id
        s.value = source.value
        s.node = source.node
        s.tokens = source.tokens
        s.children = source.children
        return s
    
    @staticmethod
    def equals(node1, node2): 
        return node1.id == node2.id
    
    @staticmethod
    def replace_child(source: 'SourceNode', source_child: 'SourceNode', replacement: 'SourceNode'): 
        new_children = [(replacement if c == source_child else c) for c in source.children]
        new_source = SourceNode.copy(source)
        new_source.children = new_children
        return new_children
    
    @staticmethod
    def replace_token(source: 'SourceNode', source_token: SourceToken, replacement: SourceToken):
        new_children = [(replacement if t == source_token else t) for t in source.tokens]
        new_source = SourceNode.copy(source)
        new_source.children = new_children
        return new_children

    @staticmethod
    def insert_before_token(source: 'SourceNode', source_token: SourceToken, replacements: SourceToken, start_whitespace = " ", end_whitespace = " "):
        token_index = next((i for i,t in enumerate(source.tokens) if t == source_token), None)
        if (token_index is None):
            raise Exception(f"None does not contain token")
        value_index = source.value.index("{t"+f"{token_index}"+"}")
        new_value = source.value[0:value_index] + start_whitespace + ("{t"+f"{len(source.tokens)}"+"}") + end_whitespace

        new_tokens = source.tokens + [replacements]

        new_source = SourceNode.copy(source)
        new_source.value = new_value
        new_source.tokens = new_tokens
        return new_source
    
    @staticmethod
    def insert_after_token(source: 'SourceNode', source_token: SourceToken, replacements: SourceToken, start_whitespace = " ", end_whitespace = " "):
        token_index = next((i for i,t in enumerate(source.tokens) if t == source_token), None)
        if (token_index is None):
            raise Exception(f"None does not contain token")
        token_placeholder = "{t"+f"{token_index}"+"}"
        value_index = source.value.index(token_placeholder) + len(token_placeholder)
        new_value = source.value[0:value_index] + start_whitespace + ("{t"+f"{len(source.tokens)}"+"}") + end_whitespace + source.value[value_index:]

        new_tokens = source.tokens + [replacements]

        new_source = SourceNode.copy(source)
        new_source.value = new_value
        new_source.tokens = new_tokens
        return new_source

class SourceNodeResolver: 
    """Utility methods for SourceNode information"""
    
    @staticmethod
    def get_type(node: SourceNode) -> str:
        # Based on https://stackoverflow.com/questions/19053707/converting-snake-case-to-lower-camel-case-lowercamelcase
        kind = node.node.kind.name
        return "".join(x.capitalize() for x in kind.lower().split("_"))

    @staticmethod
    def get_binary_operator(node: SourceNode) -> str:
        # Based on https://stackoverflow.com/questions/51077903/get-binary-operation-code-with-clang-python-bindings
        assert len(node.children) == 2
        left_offset = len([i for i in node.children[0].tokens])
        return [i for i in node.tokens][left_offset].token.spelling

class SourceTreeCreator: 
    def create(self, code, node):
        """Recursively split code into segments based on node ranges"""
        token_buffer = []
        value_buffer = []

        children = list(node.get_children())
        tokens = list([t for t in node.get_tokens() if t.cursor == node])
        child_locations = [(i, c, get_code_index(code, c.extent.start), get_code_index(code, c.extent.end)) for i,c in enumerate(children)]
        token_locations = [(i, t, get_code_index(code, t.extent.start), get_code_index(code, t.extent.end)) for i,t in enumerate(tokens)]
        (startIndex, endIndex) = get_code_indexes(code, node.extent)

        i = startIndex
        while i < endIndex:
            child_location = next((cl for cl in child_locations if cl[2] <= i and i < cl[3]), None)
            token_location = next((tl for tl in token_locations if tl[2] <= i and i < tl[3]), None)
            
            if child_location is not None: 
                (child_number, _, child_start_index, child_end_index) = child_location
                value_buffer += ("{" + f"{child_number}" + "}")
                i += (child_end_index - child_start_index)
            elif token_location is not None: 
                (token_number, token, token_start_index, token_end_index) = token_location
                value_buffer += ("{t" + f"{token_number}" + "}") 
                i += (token_end_index - token_start_index)
                token_buffer.append(SourceToken.create(token, code[token_start_index:token_end_index]))
            else: 
                value_buffer += code[i]
                i += 1
        
        transformed_children = [self.create(code, n) for n in children]
        return SourceNode.create(node, "".join(value_buffer), token_buffer, transformed_children)

class SourceTreePrinter:
    def __init__(self) -> None:
        pass

    def print(self, node, level = 0):
        """Recursive print function to traverse the AST"""
        print('  ' * level + f"{node} (#{node.id})".replace("\n", "\\n"))

        for child in node.children: 
            self.print(child, level + 1)

class SourceTreePlaceholderPrinter:
    def print(self, node, level = 0):
        """Recursive print function to traverse the AST"""
        print('  ' * level + f"{node.value} (#{node.id})".replace("\n", "\\n"))

        for child in node.children: 
            self.print(child, level + 1)

# Modification tree 
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
        return SourceNodeModifier.replace_token(target, self.targetToken, self.replacement)
    
    def getChildren(self) -> list[ModificationNode]:
        return [self.replacement]

class ReplaceTokenKindNode(ReplaceTokenNode):
    def __init__(self, targetNode: SourceNode, targetTokenKind: str, replacement: ModificationNode) -> None:
        targetToken = next((t for t in targetNode.node_tokens if get_token_kind(t) == targetTokenKind), None)
        if targetNode is None: 
            raise Exception(f"Target node {targetNode.id} does not contain token of kind {targetTokenKind}")
        super().__init__(targetNode, targetToken, replacement)

class ReplaceChildren(ModificationNode): 
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

# Based on pycparser's NodeVisitor
class SourceTreeVisitor:
    def visit(self, source_node: SourceNode): 
        node_type = SourceNodeResolver.get_type(source_node)
        node_method_name = 'visit_' + node_type
        node_method = getattr(self, node_method_name, self.generic_visit)
        node_result = node_method(source_node)
        return node_result

    def generic_visit(self, source_node: SourceNode) -> list[ModificationNode]: 
        source_node_modification_lists = [self.visit(c) for c in source_node.children]
        source_node_modifications = flatten(source_node_modification_lists)
        return source_node_modifications

class SourceTreeModifier: 
    def __init__(self, modification_nodes: ModificationNode) -> None:
        self.modification_nodes = modification_nodes

    def visit(self, source_node: SourceNode): 
        # Depth first replacement
        new_children = [self.visit(c) for c in source_node.children]
        new_source_node = SourceNode.copy(source_node)
        new_source_node.children = new_children

        modification_node = next((m for m in self.modification_nodes if m.isApplicable(source_node)), None)

        # Apply modification if found
        if modification_node is not None:
            return modification_node.apply(new_source_node) 
        else: 
            return new_source_node

class ReplaceAdditionSourceTreeVisitor(SourceTreeVisitor):
    def visit_BinaryOperator(self, source_node: SourceNode) -> list[ModificationNode]:
        if SourceNodeResolver.get_binary_operator(source_node) != '+':
            return []
        
        lvalue = self.visit(source_node.children[0])
        if len(lvalue) == 0: 
            lvalue = [CopyNode(source_node.children[0])]
        rvalue = self.visit(source_node.children[1])
        if len(rvalue) == 0: 
            rvalue = [CopyNode(source_node.children[1])]
        
        return [TemplatedReplaceNode(
            source_node, 
            "add({0}, {1})",
            lvalue + rvalue
        )]

class ReplaceIdentifierSourceTreeVisitor(SourceTreeVisitor):
    def __init__(self, target: str, replacement: str) -> None:
        super().__init__()

        self.target = target
        self.replacement = replacement

    def visit_VarDecl(self, source_node) -> list[ModificationNode]: 
        if (source_node.node.spelling == self.target):
            return [ReplaceTokenKindNode(source_node, 'identifier', ConstantNode(self.replacement))]
        else: 
            return []

    def visit_DeclRefExpr(self, source_node) -> list[ModificationNode]:
        if (source_node.node.spelling == self.target):
            return [ReplaceNode(source_node, ConstantNode(self.replacement))]
        else: 
            return []
        
class NotifySourceTreeVisitor(SourceTreeVisitor):
    def __init__(self) -> None:
        super().__init__()
        self.declarations: list[ModificationNode] = []

    def visit_FunctionDecl(self, source_node: SourceNode) -> list[ModificationNode]:
        modifications = flatten([self.visit(c) for c in source_node.children])
        function_body_node = source_node.children[0]

        return [InsertBeforeStatementsNode(
            function_body_node,
            self.declarations
        )] + modifications

    def visit_DeclRefExpr(self, source_node) -> list[ModificationNode]:
        temp = f"temp{len(self.declarations)}"
        self.declarations.append(ConstantNode(f"int {temp};"))

        par1 = TemplatedNode(
            "{0}={1}",
            [ConstantNode(temp), CopyNode(source_node)]
        )
        par2 = ConstantNode("notify()")
        par3 = ConstantNode(temp)
        
        return [TemplatedReplaceNode(
            source_node,
            "{0},{1}",
            [
                TemplatedNode("{0},{1}", [par1, par2]),
                par3
            ]
        )]

