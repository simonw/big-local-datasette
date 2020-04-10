# Fetch all project information into a SQLite database
import sqlite_utils, httpx, sys

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
    token = sys.argv[-1]
    db = sqlite_utils.Database("biglocal.db")
    fetch_projects(db, token)
