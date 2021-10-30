from herre.wards.graphql import ParsedQuery


PORTS_FR = """
  args {
      __typename
      key
      required
      description
      widget {
        __typename
        dependencies
        ... on QueryWidget {
          query  
        }
        ... on SearchWidget {
          query
        }
        ... on StringWidget {
          placeholder
        }
        ... on SliderWidget {
              min
              max  
        }
      }
      label
      ... on StructureArgPort {
        identifier
      }
      ... on EnumArgPort {
        options
      }
      ... on ListArgPort {
        child {
          __typename
          key
          required
          description
          label
          ... on StructureArgPort {
            identifier
          }
        }
        
      }
  }
  kwargs {
      __typename
      key
      required
      description
      widget {
        __typename
        dependencies
        ... on QueryWidget {
          query  
        }
        ... on SearchWidget {
          query
        }
        ... on StringWidget {
          placeholder
        }
        ... on SliderWidget {
          min
          max
        }
      }
      label
      ... on StructureKwargPort {
        identifier
      }
      ... on IntKwargPort {
        default
      }
      ... on EnumKwargPort {
        options
      }
      ... on ListKwargPort {
        child {
          __typename
          key
          required
          description
          label
          ... on StructureKwargPort {
            identifier
          }
          ... on IntKwargPort {
            default
          }
        }
        
      }
  }
  returns {
      __typename
      key
      description
      ... on StructureReturnPort {
        identifier
      }
      ... on ListReturnPort {
        child {
          __typename
          ... on StructureReturnPort {
            identifier
          }
        }
      }
  }
"""


DETAIL_NODE_FR = """
  name
  package
  interface
  id
  type
  description
""" + PORTS_FR


NODE_GET_QUERY = ParsedQuery("""
query Node($id: ID, $package: String, $interface: String, $template: ID, $q: String){
  node(id: $id, package: $package, interface: $interface, template: $template, q: $q){
    """+ DETAIL_NODE_FR +"""
  }
}
""")


NODE_CREATE_QUERY = ParsedQuery("""
mutation CreateNodeMutation(
    $description: String!,
    $args: [ArgPortInput]!,
    $kwargs: [KwargPortInput]!,
    $returns: [ReturnPortInput]!,
    $package: String!, $interface: String!,
    $name: String!
    $type: NodeTypeInput){
  createNode(description: $description, args: $args, kwargs: $kwargs, returns: $returns, package:$package, interface: $interface, name: $name, type: $type){
    """+ DETAIL_NODE_FR +"""
  }
}
""")