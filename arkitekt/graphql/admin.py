from herre.wards.graphql import ParsedQuery

RESET_REPOSITORY = ParsedQuery("""
mutation ResetRepository {
  resetRepository{
    ok
  }
}
""")