# Fetch all project information into a SQLite database
import sqlite_utils, requests, sys, click

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


@click.command()
@click.argument("db_path", type=click.Path(file_okay=True, dir_okay=False))
@click.argument("big_local_token")
@click.option(
    "--contact", multiple=True, help="Only fetch projects owned by these emails"
)
def fetch_projects(db_path, big_local_token, contact):
    db = sqlite_utils.Database(db_path)
    response = requests.post(
        "https://api.biglocalnews.org/graphql",
        json={"query": graphql_query},
        headers={"Authorization": "JWT {}".format(big_local_token)},
    )
    assert 200 == response.status_code, response.status_code
    data = response.json()
    for edge in data["data"]["openProjects"]["edges"]:
        project = edge["node"]
        files = project.pop("files")
        if contact and project["contact"] not in contact:
            continue
        db["projects"].insert(project, pk="id", replace=True)
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
    fetch_projects()
