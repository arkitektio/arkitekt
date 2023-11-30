from importlib import import_module
import inspect
module_path = "hu"

z = locals()
y = locals()

def inspect_dangerous_variables(module_path):
    """Inspect the module and return a dictionary of all the variables that are
    not upper case and that are not classes, modules, functions or builtins.
    
    This is used to check if a module is safe to import. Or if it runs code
    that might be dangegours:
    
    TODO: This is not the ebst way to do this. We should probably use the ast
    module to parse the module and check for dangerous code. This is a quick
    and dirty solution.
    
    """

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
    """Scan a module for dangerous variables."""
    return inspect_dangerous_variables(module_path)

    
    







