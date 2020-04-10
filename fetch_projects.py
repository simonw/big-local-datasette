# Fetch all project information into a SQLite database
import sqlite_utils, httpx

TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE1ODY0NjkxMTIsIm5iZiI6MTU4NjQ2OTExMiwianRpIjoiYzRjMzdlMTEtMDQ1NS00MmUxLWE0OTQtZWNiMDE3MDZjY2Q2IiwiaWRlbnRpdHkiOiI1ZjMxYjYwMi1lZGVmLTRmMzItODlkMC0wMDhlMTFmNDA4YjIiLCJmcmVzaCI6ZmFsc2UsInR5cGUiOiJhY2Nlc3MifQ.nfUqmXqoi4YjyaXTfXe8bFNQVrn8acPJZVdQlMeAyag"

graphql_query = """
{
  openProjects {
    edges {
      node {
        name
        createdAt
        updatedAt
        contact
        description
        isOpen
        id
        files {
          name
          uri
          uriType
          createdAt
          updatedAt
        }
      }
    }
  }
}
"""


def fetch_projects(db, token):
    response = httpx.post(
        "https://api.biglocalnews.org/graphql",
        json={"query": graphql_query},
        headers={"Authorization": "JWT {}".format(token)},
        timeout=None,
    )
    data = response.json()
    for edge in data["data"]["openProjects"]["edges"]:
        project = edge["node"]
        files = project.pop("files")
        db["projects"].upsert(project, pk="id")
        if files:
            db["files"].upsert_all(
                [
                    dict(
                        project=project["id"],
                        ext=fileinfo["name"].split(".")[-1],
                        **fileinfo
                    )
                    for fileinfo in files
                ],
                pk=("project", "name"),
                foreign_keys=("project",),
            )


if __name__ == "__main__":
    db = sqlite_utils.Database("biglocal.db")
    fetch_projects(db, TOKEN)
