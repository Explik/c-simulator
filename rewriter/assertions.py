def assert_type(obj, type): 
    assert isinstance(obj, type), f"{obj} is not of type {type}"

def assert_type_or_none(obj, type):
    assert obj is None or isinstance(obj, type), f"{obj} is not None or of type {type}"

def assert_list_type(obj, item_type):
    is_list = isinstance(obj, tuple) or isinstance(obj, list)
    assert is_list and all([isinstance(i, item_type) for i in obj]), f"{obj} is not of type {item_type}"
