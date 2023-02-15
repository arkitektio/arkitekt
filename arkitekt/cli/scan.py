from importlib import import_module
import inspect
module_path = f"hu"

z = locals()
y = locals()

def inspect_dangerous_variables(module_path):

    module = import_module(module_path)

    dangerous_variables = {}

    for key, value in inspect.getmembers(module):
        if key.startswith('_'):
            continue
        if inspect.isclass(value):
            continue
        if inspect.ismodule(value):
            continue
        if inspect.isfunction(value):
            continue
        if inspect.isbuiltin(value):
            continue
            
        if type(value) in [str, float, int, bool, list, dict, tuple]:
            if key != key.upper():
                dangerous_variables[key] = value
            continue

    return dangerous_variables


def scan_module(module_path):
    return inspect_dangerous_variables(module_path)

    
    







