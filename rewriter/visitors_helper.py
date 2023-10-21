from pycparser import c_ast

# Creates "type name;"
def createDecl(type: str, name: str) -> c_ast.Decl:
    type_node = c_ast.TypeDecl(
        declname= name,
        quals=[],
        align=None,
        type = c_ast.IdentifierType(names = [type])
    )
    return c_ast.Decl(
        name=name, 
        quals=[],
        align=[],
        storage=[],
        funcspec=[],
        type=type_node,
        init=None,
        bitsize=None
    )

# Creates "notify(str, &id)"
# identifier - ID node translates to &id and None translates to null
def createNotify(metadata: str|list[str], identifier: c_ast.ID|None) -> c_ast.FuncCall:
    par1 = ";".join(metadata) if isinstance(metadata, list) else metadata
    par2 = c_ast.UnaryOp("&", identifier) if identifier != None else c_ast.Constant("void*", "null");


    return c_ast.FuncCall(
        name=c_ast.ID("notify"),
        args=c_ast.ExprList(
            exprs=[
                c_ast.Constant(type="string", value=f'"{par1}"'),
                par2,
            ]
        ),
    )


# Creates "void notify(char *metadata, void *data);"
def createNotifyDecl() -> c_ast.Decl:
    par1 = c_ast.Decl(
        name="metadata",
        quals=None,
        align=[],
        storage=[],
        funcspec=[],
        init=None,
        bitsize=None,
        type=c_ast.PtrDecl(
            quals=None,
            type=c_ast.TypeDecl(
                declname="metadata",
                quals=[],
                align=None,
                type=c_ast.IdentifierType(names=["char"]),
            ),
        ),
    )
    par2 = c_ast.Decl(
        name="data",
        quals=None,
        align=[],
        storage=[],
        funcspec=[],
        init=None,
        bitsize=None,
        type=c_ast.PtrDecl(
            quals=None,
            type=c_ast.TypeDecl(
                declname="data",
                quals=[],
                align=None,
                type=c_ast.IdentifierType(names=["void"]),
            ),
        ),
    )
    return c_ast.Decl(
        name="notify",
        quals=[],
        align=[],
        storage=[],
        funcspec=[],
        init=None,
        bitsize=None,
        type=c_ast.FuncDecl(
            type=c_ast.TypeDecl(
                declname="notify",
                quals=[],
                align=None,
                type=c_ast.IdentifierType(names=["void"]),
            ),
            args=c_ast.ParamList(params=[par1, par2]),
        ),
    )


# Creates "notify("a=assign;...", &id)"
def createNotifyFromAssigment(node: c_ast.Assignment, identifier: c_ast.ID) -> c_ast.FuncCall:
    type = node.data.get("expression-type")
    name = node.lvalue.name

    if type == None: 
        raise Exception("Node is missing expression-type data")
    
    return createNotify(
        [
            "a=assign",
            "t=%s" % type,
            "i=%s" % name
        ],
        identifier
    )


# Creates "notify("a=decl;...", &id)"
def createNotifyFromDecl(node: c_ast.Decl, identifier: c_ast.ID) -> c_ast.FuncCall:
    type = node.type.type.names[0]
    
    if type == None: 
        raise Exception("Node is missing expression-type data")
    
    return createNotify(
        [
            "a=decl",
            "t=%s" % type,
            "i=%s" % node.name
        ],
        identifier
    )


# Creates "notify("a=eval;...", &id)"
def createNotifyFromExpr(node: c_ast.Node, identifier: c_ast.ID) -> c_ast.FuncCall:
    type = node.data.get("expression-type")
    location = node.data.get("location")
    
    if type == None: 
        raise Exception("Node is missing expression-type data")
    if location == None:
        raise Exception("Node is missing location data")

    return createNotify(
        [
            "a=eval",
            "t=%s" % type,
            "l=[%s,%s,%s,%s]" % (location[0], location[1], location[2], location[3])
        ],
        identifier
    )


# Creates "notify("a=state;...", null)"
def createNotifyFromStat(node: c_ast.Node) -> c_ast.Node:
    location = node.data.get("location")
    
    if type == None: 
        raise Exception("Node is missing expression-type data")
    if location == None:
        raise Exception("Node is missing location data")

    return createNotify(
        [
            "a=stat",
            "l=[%s,%s,%s,%s]" % (location[0], location[1], location[2], location[3])
        ],
        None
    )