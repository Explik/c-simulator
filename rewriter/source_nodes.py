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

class SourceRange: 
    def __init__(self, node) -> None:
        self.node = node

    def serialize(self, code): 
        (startIndex, endIndex) = get_code_indexes(code, self.node.node.extent)
        return "{\"startIndex\": " + f"{startIndex}" + ", \"endIndex\": " + f"{endIndex}" + "}"
    
    @staticmethod
    def create(node: 'SourceNode') -> 'SourceRange':
        return SourceRange(node)

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

    def get_range(self) -> SourceRange|None: 
        return self.node and SourceRange.create(self)

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

    def __eq__(self, node: object) -> bool:
        if not(isinstance(node, SourceNode)): 
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
        s.parent = None
        s.children = children
        return s

    @staticmethod
    def copy(source: 'SourceNode'): 
        s = SourceNode()
        s.id = source.id
        s.value = source.value
        s.node = source.node
        s.tokens = source.tokens
        s.parent = source.parent
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
    def get_scope(node: SourceNode) -> SourceRange|None:
        parent: SourceNode = node.parent
        while parent is not None: 
            if SourceNodeResolver.get_type(parent) in ["CompoundStmt", "ForStmt", "FunctionDecl", "WhileStmt"]:
                return parent.get_range()
            parent = parent.parent

    @staticmethod
    def get_unary_operator(node: SourceNode) -> str:
        # Based on https://stackoverflow.com/questions/51077903/get-binary-operation-code-with-clang-python-bindings
        assert len(node.children) == 1
        return node.get_tokens()[0].token.spelling

    @staticmethod
    def get_binary_operator(node: SourceNode) -> str:
        # Based on https://stackoverflow.com/questions/51077903/get-binary-operation-code-with-clang-python-bindings
        assert len(node.children) == 2
        return node.get_tokens()[0].token.spelling

class SourceTreeCreator: 
    def __init__(self, filter = None) -> None:
        self.filter = filter

    def create(self, code, node, level = 0):
        """Recursively split code into segments based on node ranges"""
        token_buffer = []
        value_buffer = []

        use_filter = self.filter is not None and level == 0
        children = list(filter(self.filter, node.get_children())) if use_filter else list(node.get_children())
        tokens = list([t for t in node.get_tokens() if t.cursor.hash == node.hash])
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
        
        transformed_children = [self.create(code, n, level + 1) for n in children]
        source_node = SourceNode.create(node, "".join(value_buffer), token_buffer, transformed_children)
        for child in source_node.get_children():
            child.parent = source_node
        return source_node

class SourceTreePrinter:
    def __init__(self, show_placeholders = False) -> None:
        self.show_placeholders = show_placeholders

    def print(self, node, level = 0):
        """Recursive print function to traverse the AST"""
        node_value = f"{node.value}" if self.show_placeholders else f"{node}"
        print('  ' * level + f"{node_value} (#{node.id})".replace("\n", "\\n"))

        for child in node.children: 
            self.print(child, level + 1)