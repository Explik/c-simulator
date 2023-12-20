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
        instance.id = SourceToken.counter
        instance.start_index = source.start_index
        instance.end_index = source.end_index
        instance.value = source.value
        instance.token = source.token
        return instance

class SourceNode(SourceText): 
    counter = 0
    
    def __init__(self) -> None:
        super().__init__()
        self.parent: SourceNode|None = None
        self.values: list[SourceText] = []
    
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

    def __eq__(self, node: object) -> bool:
        if not(isinstance(node, SourceNode)): 
            return False
        return self.id == node.id

    def __str__(self) -> str:
        return "".join([f"{v}" for v in self.values])
    
    @staticmethod
    def create(node, values: list[SourceText]) -> 'SourceNode':
        SourceNode.counter += 1
        instance = SourceNode()
        instance.id = SourceNode.counter
        instance.node = node
        instance.values = values
        return instance
    
    @staticmethod
    def copy(source: 'SourceNode'): 
        s = SourceNode()
        s.id = source.id
        s.node = s.node
        s.parent = s.parent
        s.values = source.values
        return s
    
    @staticmethod
    def equals(node1, node2): 
        return node1.id == node2.id

    @staticmethod
    def replace_value(node: 'SourceNode', target: SourceText, replacements: list[SourceText]) -> 'SourceNode':
        value_index = next((i for i,v in enumerate(node.values) if v == target), None)
        if (value_index is None): raise Exception(f"None does not contain token")

        new_values = node.values[0:value_index] + replacements + node.values[value_index+1:]
        new_node = SourceNode.copy(node)
        new_node.values = new_values
        return new_node

    def insert_before_value(node: 'SourceNode', target: SourceText, *insertions: list[SourceText]):
        value_index = next((i for i,v in enumerate(node.values) if v == target), None)
        if (value_index is None): raise Exception(f"None does not contain token")

        new_values = node.values[0:value_index-1] + insertions + node.values[value_index:]
        new_node = SourceNode.copy(node)
        new_node.values = new_values
        return new_node
    
    def insert_after_value(node: 'SourceNode', target: SourceText, *insertions: list[SourceText]):
        value_index = next((i for i,v in enumerate(node.values) if v == target), None)
        if (value_index is None): raise Exception(f"None does not contain token")

        new_values = node.values[0:value_index-1] + insertions + node.values[value_index:]
        new_node = SourceNode.copy(node)
        new_node.values = new_values
        return new_node

  
class SourceNodeResolver: 
    """Utility methods for SourceNode information"""
    
    @staticmethod
    def get_type(node: SourceNode) -> str:
        # Based on https://stackoverflow.com/questions/19053707/converting-snake-case-to-lower-camel-case-lowercamelcase
        kind = node.node.kind.name
        return "".join(x.capitalize() for x in kind.lower().split("_"))
    
    @staticmethod
    def get_scope(node: SourceNode) -> None:
        parent: SourceNode = node.parent
        while parent is not None: 
            if SourceNodeResolver.get_type(parent) in ["CompoundStmt", "ForStmt", "FunctionDecl", "WhileStmt"]:
                return None #parent.get_range()
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
    
    def create(self, code, root): 
        file_name = root.spelling
        tokens = root.get_tokens()
        nodes = [c for c in root.get_children() if c.location.file.name == file_name]

        code_map = self.create_code_map(code)
        token_seq = self.create_token_sequence(tokens, code, code_map)
        node_tree = self.create_node_tree(root, nodes, code_map, token_seq)
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

    def create_node_tree(self, node, children, code_map, token_seq) -> SourceNode: 
        buffer = []

        current_start_index = code_map[node.extent.start.line][node.extent.start.column]
        current_end_index = code_map[node.extent.end.line][node.extent.end.column]
        previous_end_index = current_start_index

        for child in children:
            child_start_index = code_map[child.extent.start.line][child.extent.start.column]
            child_end_index = code_map[child.extent.end.line][child.extent.end.column]

            # Adding any source parts preceding child as parent parts
            if child_start_index - previous_end_index > 0: 
                buffer.extend([t for t in token_seq if previous_end_index <= t.start_index and t.end_index <= child_start_index])
            
            # Adding any sources parts within child as child node
            buffer.append(self.create_node_tree(child, child.get_children(), code_map, token_seq))
            
            previous_end_index = child_end_index
        
        #Adding any source parts after last child as parent parts
        if current_end_index - previous_end_index > 0: 
            buffer.extend([t for t in token_seq if previous_end_index <= t.start_index and t.end_index <= current_end_index])
        
        return SourceNode.create(node, buffer)

    def attach_node_parents(self, node: SourceNode):
        for child in node.get_children(): 
            child.parent = node
            self.attach_node_parents(child)

class SourceTreePrinter:
    def print(self, node, level = 0):
        """Recursive print function to traverse the AST"""
        print('  ' * level + f"{node} (#{node.id})".replace("\n", "\\n"))

        for child in node.get_children(): 
            self.print(child, level + 1)