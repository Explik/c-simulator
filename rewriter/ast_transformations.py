from ast_visitors import AstVisitor, Change, ConstantValueNode, CopyValueNode, ModificationNode, ReplaceNode, TemplatedValueNode

def get_node_type(node): 
    kind = node.kind.name
    return "".join(x.capitalize() for x in kind.lower().split("_"))

def AssignmentTemplateNode(lvalue, rvalue): 
    return TemplatedValueNode("{0}={1}", [lvalue, rvalue])

def CommaTemplateNode(*args): 
    placeholders = ["{" + f"{n}" + "}" for n in list(range(0, len(args)))]
    template = ", ".join(placeholders)

    return TemplatedValueNode(template, args)

# Transformation visitors must follow the following rules:
# - Expression transformations must return c_ast.ExprList
# - Statement transformations must return another statement
# - Block transformations must return c_ast.Compound
class BaseTransformation(): 
    def __init__(self) -> None:
        #self.pushVariable: Callable[[str], c_ast.Node]|None = None;
        #self.popVariables: Callable[[],list[c_ast.Node]]|None = None;
        #self.callback: Callable[[c_ast.Node], c_ast.Node]|None = None;
        pass

    def isApplicable(self, node) -> bool: 
        raise Exception("isApplicable is not implemented")
    
    def apply(self, node) -> Change:
        raise Exception("apply is not implemented")

# Performs Id transformation
# a
# (temp0 = a, notify(...), temp0)
class IdTransformation(BaseTransformation):
    def isApplicable(self, node) -> bool:
        return get_node_type(node) == "DeclRefExpr"

    def apply(self, node):
        value = CommaTemplateNode(
            AssignmentTemplateNode(
                ConstantValueNode('temp0'),
                CopyValueNode(node)
            ),
            ConstantValueNode('notify()'),
            ConstantValueNode('temp0')
        )
        return ReplaceNode.create(node, value)
    
class TransformationVisitor(AstVisitor):
    def __init__(self): 
        self.transformations = [IdTransformation()]

    def generic_visit(self, node) -> ModificationNode | None:
        transformation = next((t for t in self.transformations if t.isApplicable(node)), None)
        if transformation is None:
            return AstVisitor.generic_visit(self, node)
        
        return transformation.apply(node)