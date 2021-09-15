

from arkitekt.packers.structure import Structure
from typing import Type


class NoTranspilerException(Exception):
    pass


class TranspilerRegistry():


    def __init__(self) -> None:
        self.typeStructureTranspilerMap = {}
        self.typeTranspilerMap = {}

    def get_transpiler(self, type: str, structure: str):
        assert type in self.typeStructureTranspilerMap, f"No Transpiler registered for this Type {type} {self.typeStructureTranspilerMap}"
        assert structure in self.typeStructureTranspilerMap[type], f"No Transpiler registered for this Structure {structure} on {type}"
        return self.typeStructureTranspilerMap[type][structure]


    def register_transpiler(self, transpiler):
        self.typeStructureTranspilerMap.setdefault(transpiler.type_name, {})[transpiler.structure_name] = transpiler
        self.typeTranspilerMap[transpiler.type] = transpiler

    def get_transpiler_for_type(self, type, allow_subclass=True):
        if type in self.typeTranspilerMap:
            return self.typeTranspilerMap[type]

        if allow_subclass:
            for base_class, transpiler in self.typeTranspilerMap.items():
                if issubclass(type, base_class): 
            
                    return transpiler

        raise NoTranspilerException(f"Could not find a Transpiler for type {type}")




TRANSPILER_REGISTRY = None

def get_transpiler_registry():
    global TRANSPILER_REGISTRY
    if TRANSPILER_REGISTRY == None:
        TRANSPILER_REGISTRY = TranspilerRegistry()
    return TRANSPILER_REGISTRY