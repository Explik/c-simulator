import re
from assertions import assert_type, assert_list_type

def get_token_kind(token: 'SourceToken'):
    return token.token.kind.name.lower()

class SourceText: 
    def __init__(self) -> None:
        self.start_index: int|None = None
        self.end_index: int|None = None
        self.value: str|None = None 

    def __eq__(self, node: object) -> bool:
        if not(isinstance(node, SourceText)): 
            return False
        return self.value == node.value

    def __str__(self) -> str:
        return self.value

    @staticmethod
    def create(start_index, end_index, value):
        instance = SourceText()
        instance.start_index = start_index
        instance.end_index = end_index
        instance.value = value
        return instance


class SourceToken(SourceText): 
    counter = 0

    def __init__(self) -> None:
        super().__init__()
        self.token = None

    def __eq__(self, node: object) -> bool:
        if not(isinstance(node, SourceToken)): 
            return False
        return self.id == node.id
    
    @staticmethod
    def create(start_index, end_index, value, token):
        SourceToken.counter += 1
        instance = SourceToken()
        instance.id = SourceToken.counter
        instance.start_index = start_index
        instance.end_index = end_index
        instance.value = value
        instance.token = token
        return instance
    
    @staticmethod
    def copy(source: 'SourceToken'):
        instance = SourceToken()
        instance.id = source.id
        instance.start_index = source.start_index
        instance.end_index = source.end_index
        instance.value = source.value
        instance.token = source.token
        return instance
    
    @staticmethod
    def reset():
        SourceToken.counter = 0


class SourceNode(SourceText): 
    counter = 0
    
    def __init__(self) -> None:
        super().__init__()
        self.id: int|None = None
        self.node: object|None = None
        self.parent: SourceNode|None = None
        self.values: list[SourceText] = []
    
    def __eq__(self, node: object) -> bool:
        if not(isinstance(node, SourceNode)): 
            return False
        return self.id == node.id

    def __str__(self) -> str:
        return "".join([f"{v}" for v in self.values])

    def get_children(self) -> list['SourceNode']: 
        return [v for v in self.values if type(v) == SourceNode]
    
    def get_tokens(self) -> list[SourceToken]:
        return [v for v in self.values if type(v) == SourceToken]

    def is_statement(self):
        if self.parent is None: 
            return False

        parent_type = SourceNodeResolver.get_type(self.parent)
        grand_parent_type = self.parent and self.parent.parent and SourceNodeResolver.get_type(self.parent.parent)
        parent_children = self.parent.get_children()

        if parent_type in ["CompoundStmt", "DeclStmt"]:
            return True
        
        if grand_parent_type in ["SwitchStmt"] and parent_children[0] == self:
            return True

        if parent_type in ["CaseStmt", "DefaultStmt"] and parent_children[0] != self:
            return True

        return parent_type in ["ForStmt", "IfStmt", "WhileStmt"]
    
    @staticmethod
    def create(node, values: list[SourceText]) -> 'SourceNode':
        SourceNode.counter += 1
        instance = SourceNode()
        instance.id = SourceNode.counter
        instance.node = node
        instance.start_index = min([v.start_index for v in values]) if len(values) and not any([v for v in values if v.start_index is None]) else None
        instance.end_index = max([v.end_index for v in values]) if len(values) and not any([v for v in values if v.end_index is None]) else None
        instance.values = values
        return instance
    
    @staticmethod
    def create_from_template(template_string: str, insertions: list[SourceText]): 
        assert_type(template_string, str)
        assert_list_type(insertions, SourceText)
        
        # Split template string of format {0}, {1}, {2}
        pattern = re.compile(r'\{\d+\}')
        template_parts = pattern.split(template_string)
        template_placeholders = pattern.findall(template_string)

        # Build values matching templates and insertions
        values = []
        for i, part in enumerate(template_parts):
            # Add the token part
            if part:
                values.append(SourceText.create(None, None, part))
            
            # Add the placeholder if it exists
            if i < len(template_placeholders):
                placeholder_index = int(template_placeholders[i][1:-1])
                
                # Check if the placeholder index is within the bounds of the insertions array
                if placeholder_index < len(insertions):
                    values.append(insertions[placeholder_index])
                else:
                    raise IndexError(f"Placeholder index {placeholder_index} is out of bounds.")

        return SourceNode.create(None, values)

    @staticmethod
    def copy(source: 'SourceNode'): 
        s = SourceNode()
        s.id = source.id
        s.node = source.node
        s.start_index = source.start_index
        s.end_index = source.end_index
        s.parent = s.parent
        s.values = source.values
        return s
    
    @staticmethod
    def equals(node1, node2): 
        return node1.id == node2.id

    @staticmethod
    def replace_value(node: 'SourceNode', target: SourceText, *replacements: list[SourceText]) -> 'SourceNode':
        assert_type(node, SourceNode)
        assert_type(target, SourceText)
        assert_list_type(replacements, SourceText)
        
        value_index = next((i for i,v in enumerate(node.values) if v == target), None)
        if (value_index is None): raise Exception(f"None does not contain token")

        new_values = node.values[0:value_index] + replacements + node.values[value_index+1:]
        new_node = SourceNode.copy(node)
        new_node.values = new_values
        return new_node

    @staticmethod
    def replace_values(node: 'SourceNode', targets: list[SourceText], replacements: list[SourceText]) -> 'SourceNode':
        assert_type(node, SourceNode)
        assert_list_type(targets, SourceText)
        assert_list_type(replacements, SourceText)
        
        if len(targets) != len(replacements):
            raise Exception("Targets and replacements are not the same length")
        
        new_values = list(node.values)
        target_indexes = [new_values.index(t) for t in targets]
        for i in range(0, len(targets)):
            new_values[target_indexes[i]] = replacements[i]

        new_node = SourceNode.copy(node)
        new_node.values = new_values
        return new_node

    @staticmethod
    def insert_before_value(node: 'SourceNode', target: SourceText, *insertions: list[SourceText]):
        assert_type(node, SourceNode)
        assert_type(target, SourceText)
        assert_list_type(insertions, SourceText)
        
        value_index = next((i for i,v in enumerate(node.values) if v == target), None)
        if (value_index is None): raise Exception(f"None does not contain token")

        new_values = node.values[0:value_index] + list(insertions) + node.values[value_index:]
        new_node = SourceNode.copy(node)
        new_node.values = new_values
        return new_node
    
    @staticmethod
    def insert_after_value(node: 'SourceNode', target: SourceText, *insertions: list[SourceText]):
        assert_type(node, SourceNode)
        assert_type(target, SourceText)
        assert_list_type(insertions, SourceText)
        
        value_index = next((i for i,v in enumerate(node.values) if v == target), None)
        if (value_index is None): raise Exception(f"None does not contain token")

        new_values = node.values[0:value_index + 1] + list(insertions) + node.values[value_index + 1:]
        new_node = SourceNode.copy(node)
        new_node.values = new_values
        return new_node

    @staticmethod
    def reset():
        SourceNode.counter = 0

class SourceType: 
    def __init__(self) -> None:
        self.type: str|None = None
        self.name: str|None = None
        self.byte_size: int|None = None 

    def serialize(self): 
        return "{ \"type\": \"" + self.type + "\", \"name\": \"" + self.name + "\", \"byteSize\": " + f"{self.byte_size}" + " }"

    @staticmethod
    def create(type, name, byte_size):
        instance = SourceType()
        instance.type = type
        instance.name = name
        instance.byte_size = byte_size
        return instance

    @staticmethod
    def create_uint(name, byte_size):
        return SourceType.create("uint", name, byte_size)
    
    @staticmethod
    def create_int(name, byte_size):
        return SourceType.create("int", name, byte_size)
    
    @staticmethod
    def create_float(name, byte_size):
        return SourceType.create("float", name, byte_size)


class SourceNodeResolver: 
    """Utility methods for SourceNode information"""
    
    @staticmethod
    def get_type(node: SourceNode) -> str:
        # Based on https://stackoverflow.com/questions/19053707/converting-snake-case-to-lower-camel-case-lowercamelcase
        kind = node.node.kind.name
        return "".join(x.capitalize() for x in kind.lower().split("_"))
    
    @staticmethod
    def get_scope(node: SourceNode) -> tuple[int, int]|None:
        parent: SourceNode = node.parent
        while parent is not None: 
            if SourceNodeResolver.get_type(parent) in ["CompoundStmt", "ForStmt", "FunctionDecl", "WhileStmt"]:
                return (parent.start_index, parent.end_index)
            parent = parent.parent

    @staticmethod
    def get_unary_operator(node: SourceNode) -> str|None:
        # Based on https://stackoverflow.com/questions/51077903/get-binary-operation-code-with-clang-python-bindings
        assert len(node.get_children()) == 1
        tokens = node.get_tokens()
        return tokens[0].token.spelling if any(tokens) else None

    @staticmethod
    def get_binary_operator(node: SourceNode) -> str:
        # Based on https://stackoverflow.com/questions/51077903/get-binary-operation-code-with-clang-python-bindings
        assert len(node.get_children()) == 2
        tokens = node.get_tokens()
        return tokens[0].token.spelling if any(tokens) else None
    
    @staticmethod
    def get_storage_class(source_node: SourceNode) -> str:
        return source_node.node.storage_class.name.lower()

    @staticmethod
    def has_token_kind(node: SourceNode, token_kind) -> bool: 
        # Only checks node and not children 
        return any(t for t in node.get_tokens() if get_token_kind(t) == token_kind)

class SourceTypeResolver: 
    """Utility method for SourceNode information"""
    @staticmethod 
    def get_builtin_types() -> list[SourceType]: 
        return ([
            # Integer types 
            SourceType.create_int("char", 1),
            SourceType.create_int("short", 2),
            SourceType.create_int("int", 4),
            SourceType.create_int("long", 4),
            SourceType.create_int("long int", 4),

            # Unsigned integer types
            SourceType.create_uint("size_t", 4),
            SourceType.create_uint("uint", 4),

            # Floating point types
            SourceType.create_float("float", 4),
            SourceType.create_float("double", 8),
            SourceType.create_float("long double", 8)
        ])
    
    def is_builtin_type(name):
        base_name_1 = name.replace("*", "").strip()
        base_name_2 = base_name_1.split("[")[0]
        return any(t for t in SourceTypeResolver.get_builtin_types() if t.name == base_name_2)

class SourceTreeCreator: 
    def __init__(self, filter = None) -> None:
        self.filter = filter
    
    def create(self, code, root): 
        file_name = root.spelling
        tokens = root.get_tokens()
        nodes = [c for c in root.get_children() if c.location.file.name == file_name]

        code_map = self.create_code_map(code)
        token_seq = self.create_token_sequence(tokens, code, code_map)
        node_tree = self.create_node_tree(root, 0, len(code), nodes, code, code_map, token_seq)
        self.attach_node_parents(node_tree)

        return node_tree
    
    def create_code_map(self, code): 
        i = 0
        buffer = [[], [-1]]

        for c in code: 
            if c == '\n':
                buffer[-1].append(i)
                buffer.append([-1])
            else: 
                buffer[-1].append(i)
            i += 1
        buffer[-1].append(i)

        return buffer 
    
    def create_token_sequence(self, tokens, code, code_map): 
        buffer = []
        previous_end_index = 0

        for token in tokens: 
            current_start_index = code_map[token.extent.start.line][token.extent.start.column]
            current_end_index = code_map[token.extent.end.line][token.extent.end.column]

            if current_start_index - previous_end_index > 0:
                buffer.append(SourceText.create(
                    previous_end_index, 
                    current_start_index, 
                    code[previous_end_index:current_start_index]
                ))
            buffer.append(SourceToken.create(
                current_start_index, 
                current_end_index, 
                code[current_start_index:current_end_index], 
                token
            ))

            previous_end_index = current_end_index

        return buffer

    def create_node_tree(self, node, start_index, end_index, children, code, code_map, token_seq) -> SourceNode: 
        # Ordering children as the subsequent alghorithm depends on it
        ordered_children = list(children)
        ordered_children.sort(key=lambda n: self.get_node_indicies(n, code_map)[0])

        # Remove any children not contained within parent, i.e. not proper children
        proper_children = [c for c in ordered_children if self.is_overlapped_node(node, c, code_map)]

        # Remove any overlapping children  
        non_overlapping_children = []
        for child in proper_children:
            non_overlapping_children = [c for c in non_overlapping_children if not self.is_overlapped_node(child, c, code_map)]
            non_overlapping_children.append(child)

        buffer = []
        previous_end_index = start_index
        for child in non_overlapping_children:
            child_start_index, child_end_index = self.get_node_indicies(child, code_map)

            # Adding any source parts preceding child as parent parts
            if child_start_index - previous_end_index > 0: 
                buffer.extend([t for t in token_seq if previous_end_index <= t.start_index and t.end_index <= child_start_index])
            
            # Adding any sources parts within child as child node
            buffer.append(self.create_node_tree(child, child_start_index, child_end_index, list(child.get_children()), code, code_map, token_seq))
            
            previous_end_index = child_end_index
        
        #Adding any source parts after last child as parent parts
        if end_index - previous_end_index > 0: 
            buffer.extend([t for t in token_seq if previous_end_index <= t.start_index and t.end_index <= end_index])

        return SourceNode.create(node, buffer)
    
    def is_overlapped_node(self, node1, node2, code_map): 
        """Determines if node2 is contained within node1"""
        # Unpacking the ranges
        start1, end1 = self.get_node_indicies(node1, code_map)
        start2, end2 = self.get_node_indicies(node2, code_map)

        # Check if range2 is within range1
        return start1 <= start2 and end1 >= end2

    def get_node_indicies(self, node, code_map):
        start_index = code_map[node.extent.start.line][node.extent.start.column]
        end_index = code_map[node.extent.end.line][node.extent.end.column]
        return (start_index, end_index)

    def attach_node_parents(self, node: SourceNode):
        for child in node.get_children(): 
            child.parent = node
            self.attach_node_parents(child)


class SourceTreePrinter:
    def print(self, node: SourceNode, level = 0):
        # Recursive print function to traverse the AST
        assert_type(node, SourceNode)

        print('  ' * level + f"{node} (#{node.id})".replace("\n", "\\n"))
        for child in node.get_children(): 
            self.print(child, level + 1)