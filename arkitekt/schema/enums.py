from enum import Enum


class NodeType(str, Enum):
    FUNCTION = "FUNCTION"
    GENERATOR = "GENERATOR"