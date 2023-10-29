# Based on https://stackoverflow.com/questions/952914/how-do-i-make-a-flat-list-out-of-a-list-of-lists
def flatten(l):
    return [item for sublist in l for item in sublist]

# Based on https://stackoverflow.com/questions/19053707/converting-snake-case-to-lower-camel-case-lowercamelcase
def get_node_type(node): 
    kind = node.kind.name
    return "".join(x.capitalize() for x in kind.lower().split("_"))

def get_node_token(node, type):
    return next(t for t in node.get_tokens() if t.kind.name == type.upper()) 

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

class Change:
    def __init__(self, startIndex, endIndex, value) -> None:
        self.startIndex = startIndex
        self.endIndex = endIndex
        self.value = value

class BaseNode: 
    def getChildren(self): 
        return []
    
class ValueNode(BaseNode): 
    def getValue(self, code) -> str: 
        raise Exception("Not implemented")

class ConstantValueNode(ValueNode): 
    def __init__(self, value: str) -> None:
        super().__init__()

        self.value = value;

    def getValue(self, code) -> str:
        return self.value

class CopyValueNode(ValueNode):
    def __init__(self, node) -> None:
        super().__init__()

        self.startLocation = node.extent.start
        self.endLocation = node.extent.end
    
    def getValue(self, code) -> str:
        startIndex = get_code_index(code, self.startLocation)
        endIndex = get_code_index(code, self.endLocation)
        return code[startIndex:endIndex]
    
    def __str__(self) -> str:
        buffer = "CopyValueNode("
        if self.startLocation is not None: 
            buffer += f"start=l{self.startLocation.line}c{self.startLocation.column}, "
        if self.endLocation is not None: 
            buffer += f"end=l{self.endLocation.line}c{self.endLocation.column}"
        return buffer + ")"

class ModificationNode(BaseNode): 
    def apply(self, code):
        """ Applies all changes to code. Fails on overlapping changes"""
        buffer = []
        changes = self.getChanges(code)

        i = 0
        while i < len(code):
            current_changes = [c for c in changes if c.startIndex <= i and i < c.endIndex]

            if len(current_changes) == 0: 
                buffer.append(code[i])
                i += 1
            elif len(current_changes) == 1:
                current_change = current_changes[0]
                buffer.append(current_change.value)
                i = current_change.endIndex
            else: 
                raise Exception("Overlapping changes")
            
        return "".join(buffer)

    def getChanges(self, code) -> list[Change]: 
        raise Exception("Not implemented")

    
    def __str__(self) -> str:
        return "ModificationNode()"

class CompoundModificationNode(ModificationNode):
    def __init__(self, modifications: list[ModificationNode]) -> None:
        super().__init__()

        self.modifications = modifications

    def getChanges(self, code) -> list[Change]:
        modification_changes = [m.getChanges(code) for m in self.modifications if m is not None]
        modification_filtered_changes = [c for c in modification_changes if c is not None]
        
        return flatten(modification_filtered_changes)
    
    def getChildren(self):
        return self.modifications
    
    def __str__(self) -> str:
        return f"CompoundModification({len(self.modifications)} changes)"

class ReplaceNode(ModificationNode):
    def __init__(self) -> None:
        super().__init__()

        self.startLocation = None
        self.endLocation = None
        self.offset = None
        self.replacement: ValueNode|None = None

    def getChanges(self, code) -> list[Change]:
        startIndex = get_code_index(code, self.startLocation)
        endIndex = get_code_index(code, self.endLocation) if self.endLocation is not None else startIndex + self.offset

        return [Change(startIndex, endIndex, self.replacement.getValue())]
    
    def __str__(self) -> str:
        buffer = "ReplaceNode("
        if self.startLocation is not None: 
            buffer += f"start=l{self.startLocation.line}c{self.startLocation.column}, "
        if self.endLocation is not None: 
            buffer += f"end=l{self.endLocation.line}c{self.endLocation.column}, "
        if self.offset is not None: 
            buffer += f"offset={self.offset}, "
        if self.replacement is not None: 
            buffer += f"replacement={self.replacement.getValue()}"

        return buffer + ")"

class TemplatedReplaceNode(ModificationNode): 
    def __init__(self, node, template: str, nodes: list[BaseNode]) -> None:
        super().__init__()

        self.startLocation = node.extent.start
        self.endLocation = node.extent.end
        self.template = template
        self.nodes = nodes
    
    def getChanges(self, code) -> list[Change]:
        template_buffer = self.template
        value_nodes = [n for n in self.nodes if isinstance(n, ValueNode)]

        for i in range(len(value_nodes)):
            value_node = value_nodes[i]
            template_buffer = template_buffer.replace("{"+f"{i}"+"}", value_node.getValue(code))

        startIndex = get_code_index(code, self.startLocation)
        endIndex = get_code_index(code, self.endLocation) 
        return [Change(startIndex, endIndex, template_buffer)]
    
    def getChildren(self):
        return self.nodes
    
    def __str__(self) -> str:
        buffer = "TemplatedReplaceNode("
        if self.startLocation is not None: 
            buffer += f"start=l{self.startLocation.line}c{self.startLocation.column}, "
        if self.endLocation is not None: 
            buffer += f"end=l{self.endLocation.line}c{self.endLocation.column}, "
        if self.nodes is not None:
            buffer += f"{len(self.nodes)} changes"
        return buffer + ")"
    
class ReplaceIdentiferNode(ReplaceNode): 
    def __init__(self, node, id) -> None:
        super().__init__()

        self.replacement = ConstantValueNode(id)

        # Specifying location for replacement
        node_type = get_node_type(node)
        if (node_type == 'VarDecl'):
            identifier_token = get_node_token(node, 'identifier')
            self.startLocation = identifier_token.location  
            self.offset = len(identifier_token.spelling)
        elif (node_type == 'DeclRefExpr'): 
            self.startLocation = node.extent.start
            self.endLocation = node.extent.end
        else: 
            raise Exception(f"Unsupported node type {node_type}")

# Based on pycparser's NodeVisitor
class AstVisitor:
    def visit(self, node) -> ModificationNode|None: 
        node_type = get_node_type(node)
        node_method_name = 'visit_' + node_type
        node_method = getattr(self, node_method_name, self.generic_visit)

        return node_method(node)

    def generic_visit(self, node) -> ModificationNode|None: 
        node_children = node.get_children()
        node_modifications = [self.visit(c) for c in node_children]
        node_filtered_modifications = [m for m in node_modifications if m is not None]

        if len(node_filtered_modifications) == 0:
            return None
        elif len(node_filtered_modifications) == 1:
            return node_filtered_modifications[0]
        else:
            return CompoundModificationNode(node_filtered_modifications)
 
class ReplaceIdentifierVisitor(AstVisitor):
    def __init__(self, target, replacement) -> None:
        super().__init__()

        self.target = target
        self.replacement = replacement

    def visit_VarDecl(self, node) -> ModificationNode|None: 
        if (node.spelling == self.target):
            return ReplaceIdentiferNode(node, self.replacement)
        else: 
            return None

    def visit_DeclRefExpr(self, node) -> ModificationNode|None:
        if (node.spelling == self.target):
            return ReplaceIdentiferNode(node, self.replacement)
        else: 
            return None

class ReplaceAdditionVisitor(AstVisitor):
    def visit_BinaryOperator(self, node) -> ModificationNode | None:
        operands = list(node.get_children())
        lvalue = self.visit(operands[0])
        rvalue = self.visit(operands[1])

        return TemplatedReplaceNode(
            node,
            "add({0}, {1})", 
            [
                lvalue if lvalue is not None else CopyValueNode(operands[0]),
                rvalue if rvalue is not None else CopyValueNode(operands[1])
            ]
        )

class AstPrinter: 
    def print(self, code, node, level=0):
        """Recursive function to traverse the AST."""
        print('  ' * level + self._stringify_node(code, node))

        for child in node.get_children():
            self.print(code, child, level + 1)

    def _stringify_node(self, code, node): 
        buffer = f"{get_node_type(node)}: "

        if hasattr(node, 'type') and hasattr(node.type, 'spelling') and len(f"{node.type.spelling}") != 0:
            buffer += f"type={node.type.spelling} "

        if hasattr(node, 'displayname') and len(f"{node.displayname}") != 0: 
            buffer += f"display_name={node.displayname} "

        if hasattr(node, 'extent'): 
            start = node.extent.start
            end = node.extent.end
            buffer += f"loc=l{start.line}c{start.column} "
            buffer += f"code={self._get_code_part(code, start, end)} "

        return buffer
    
    def _get_code_part(self, code, loc1, loc2):
        start_index = get_code_index(code, loc1)
        end_index = get_code_index(code, loc2)

        return "\"" + code[start_index:end_index].replace("\n", "\\n") +  "\""
    
class ModificationPrinter: 
    def print(self, modification: ModificationNode, level = 0):
        """Recursive function to traverse the AST."""
        print('  ' * level + f"{modification}")

        for child in modification.getChildren():
            self.print(child, level + 1)