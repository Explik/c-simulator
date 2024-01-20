def read_file(file_name): 
    f = open(file_name)
    buffer = f.read()
    f.close()
    return buffer

def write_file(file_name, content): 
    f = open(file_name, "x")
    f.write(content)
    f.close()

def ellipse_string(input: str, max_length: int): 
    if input is None or max_length is None or len(input) < max_length: 
        return input
    
    return input[0:max_length - 3] + "..."