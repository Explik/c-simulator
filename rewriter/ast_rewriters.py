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

class StringNode: 
    def __init__(self, value, node, children) -> None:
        self.value = value
        self.node = node
        self.children = children

    def __str__(self) -> str:
        buffer = self.value
        for i in range(0, len(self.children)):

            buffer = buffer.replace("{"+f"{i}"+"}", f"{self.children[i]}")
        return buffer

class StringTreeCreator: 
    def create(self, code, node):
        """Recursively split code into segments based on node ranges"""
        children = list(node.get_children())
        child_locations = [(i, c, get_code_index(code, c.extent.start), get_code_index(code, c.extent.end)) for i,c in enumerate(children)]
        (startIndex, endIndex) = get_code_indexes(code, node.extent)

        if len(children) == 0:
            return StringNode(code[startIndex:endIndex], node, [])
        
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
        return StringNode("".join(buffer), node, transformed_children)

class StringTreePrinter1:
    def print(self, node, level = 0):
        """Recursive print function to traverse the AST"""
        print('  ' * level + node.value.replace("\n", "\\n"))

        for child in node.children: 
            self.print(child, level + 1)

class StringTreePrinter2:
    def print(self, node, level = 0):
        """Recursive print function to traverse the AST"""
        print('  ' * level + f"{node}".replace("\n", "\\n"))

        for child in node.children: 
            self.print(child, level + 1)
