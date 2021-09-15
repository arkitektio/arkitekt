from herre.wards.graphql import ParsedQuery
from arkitekt.graphql.node import DETAIL_NODE_FR


TEMPLATE_GET_QUERY = ParsedQuery("""
query Template($id: ID,){
  template(id: $id){
    id
    node {
        """
        + DETAIL_NODE_FR+
        """
    }
  }
}
""")


UPDATE_OR_CREATE_TEMPLATE = ParsedQuery("""
mutation CreateTemplate($node: ID!, $params: GenericScalar){
  createTemplate(node: $node, params: $params){
    id
    node {
        """
        + DETAIL_NODE_FR+
        """
    }
  }
}
""")