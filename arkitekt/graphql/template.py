from herre.wards.graphql import ParsedQuery
from arkitekt.graphql.node import DETAIL_NODE_FR


TEMPLATE_FRAGMENT = (
    """
    id
    registry {
      app {
        name
      }
      user {
        username
      }
    }
    node {
"""
    + DETAIL_NODE_FR
    + """
    }
"""
)


TEMPLATE_GET_QUERY = ParsedQuery(
    """
query Template($id: ID,){
  template(id: $id){
    """
    + TEMPLATE_FRAGMENT
    + """
  }
}
"""
)


UPDATE_OR_CREATE_TEMPLATE = ParsedQuery(
    """
mutation CreateTemplate($node: ID!, $params: GenericScalar, $extensions: [String], $version: String){
  createTemplate(node: $node, params: $params, extensions: $extensions, version: $version){
    """
    + TEMPLATE_FRAGMENT
    + """
  }
}
"""
)
