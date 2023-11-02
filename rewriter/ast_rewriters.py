# Based on https://stackoverflow.com/questions/19053707/converting-snake-case-to-lower-camel-case-lowercamelcase
def get_node_type(node): 
    kind = node.kind.name
    return "".join(x.capitalize() for x in kind.lower().split("_"))

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
class SourceNode: 
    counter = 0

    def __str__(self) -> str:
        buffer = self.value
        for i in range(0, len(self.children)):

            buffer = buffer.replace("{"+f"{i}"+"}", f"{self.children[i]}")
        return buffer
    
    @staticmethod
    def create(value, node, children) -> None:
        SourceNode.counter += 1
        s = SourceNode()
        s.id = SourceNode.counter
        s.value = value
        s.node = node
        s.children: list[SourceNode] = children
        return s

    @staticmethod
    def copy(source): 
        s = SourceNode()
        s.id = source.id
        s.value = source.value
        s.node = source.node
        s.children = source.children
        return s
    
    @staticmethod
    def equals(node1, node2): 
        return node1.id == node2.id

class SourceTreeCreator: 
    def create(self, code, node):
        """Recursively split code into segments based on node ranges"""
        children = list(node.get_children())
        child_locations = [(i, c, get_code_index(code, c.extent.start), get_code_index(code, c.extent.end)) for i,c in enumerate(children)]
        (startIndex, endIndex) = get_code_indexes(code, node.extent)

        if len(children) == 0:
            return SourceNode.create(code[startIndex:endIndex], node, [])
        
        buffer = []
        i = startIndex
        while i < endIndex:
            child_location = next((cl for cl in child_locations if  cl[2] <= i and i < cl[3]), None)
            
            if child_location is None: 
                buffer.append(code[i])
                i += 1
            else:
                buffer += ("{" + f"{child_location[0]}" + "}")
                i += (child_location[3] - child_location[2])
        
        transformed_children = [self.create(code, n) for n in children]
        return SourceNode.create("".join(buffer), node, transformed_children)

class SourceTreePrinter:
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

class ConstantNode(ModificationNode):
    def __init__(self, value: str) -> None:
        super().__init__()
        self.value = value

    def isApplicable(self, node: SourceNode) -> bool:
        """Constant nodes are not connected to source tree and can therefore not be applied to it""" 
        return False
    
    def apply(self, node: SourceNode) -> SourceNode:
        return SourceNode.create(self.value, None, [])

class ReplaceNode(ModificationNode):
    def __init__(self, target: SourceNode, replacement: ModificationNode) -> None:
        super().__init__() 
        self.target = target
        self.replacement = replacement

    def isApplicable(self, node: SourceNode) -> bool:
        return SourceNode.equals(node, self.target)
    
    def apply(self, node: SourceNode) -> SourceNode:
        return self.replacement.apply(node)

# Based on pycparser's NodeVisitor
class SourceTreeVisitor:
    def visit(self, source_node: SourceNode): 
        node_type = get_node_type(source_node.node)
        node_method_name = 'visit_' + node_type
        node_method = getattr(self, node_method_name, self.generic_visit)
        node_result = node_method(source_node)
        return node_result

    def generic_visit(self, source_node: SourceNode) -> ModificationNode|None: 
        source_node_modifications = [self.visit(c) for c in source_node.children]
        source_node_filtered_modifications = [m for m in source_node_modifications if m is not None]

        if len(source_node_filtered_modifications) == 0:
            return None
        elif len(source_node_filtered_modifications) == 1:
            return source_node_filtered_modifications[0]
        else:
            return None #CompoundModificationNode(source_node_filtered_modifications)

class SourceTreeModifier: 
    def __init__(self, modification_nodes: list[ModificationNode]) -> None:
        self.modification_nodes = modification_nodes

    def visit(self, source_node: SourceNode): 
        # Depth first replacement
        new_children = [self.visit(c) for c in source_node.children]
        new_source_node = SourceNode.copy(source_node)
        new_source_node.children = new_children

        # Modification is found using nodes in the original tree
        modification_node = next((n for n in self.modification_nodes if n.isApplicable(new_source_node)), None)

        # Apply modification if found
        if modification_node is None: 
            return new_source_node
        else: 
            return modification_node.apply(new_source_node)

class ReplaceIdentifierSourceTreeVisitor(SourceTreeVisitor):
    def __init__(self, target: str, replacement: str) -> None:
        super().__init__()

        self.target = target
        self.replacement = replacement

    #def visit_VarDecl(self, source_node) -> ModificationNode|None: 
    #    if (source_node.node.spelling == self.target):
    #        return ReplaceNode(source_node, ConstantNode(self.replacement))
    #    else: 
    #        return None

    def visit_DeclRefExpr(self, source_node) -> ModificationNode|None:
        if (source_node.node.spelling == self.target):
            return ReplaceNode(source_node, ConstantNode(self.replacement))
        else: 
            return None
