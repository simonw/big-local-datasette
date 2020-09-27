import sqlite_utils, csv, pathlib, requests
import click

THRESHOLD = 50000000


def uri_for_file(project_id, filename, token):
    graphql_query = """
    mutation {
      createFileDownloadUri(input:{
        projectId:"PROJECT_ID",
        fileName:"FILENAME"
      }) {
        ok {
          name
          uri
          uriType
        }
      }
    }
    """.replace(
        "PROJECT_ID", project_id
    ).replace(
        "FILENAME", filename
    )
    response = requests.post(
        "https://api.biglocalnews.org/graphql",
        json={"query": graphql_query},
        headers={"Authorization": "JWT {}".format(token)},
    )
    return response.json()["data"]["createFileDownloadUri"]["ok"]["uri"]


def size_and_etag_and_status(url):
    response = requests.head(url)
    status = response.status_code
    return int(response.headers["Content-Length"]), response.headers.get("ETag"), status


def url_to_dicts(url):
    response = requests.get(url, stream=True)
    reader = csv.DictReader(
        line.decode("utf-8", errors="ignore") for line in response.iter_lines()
    )
    for row in reader:
        skip = False
        for key in row:
            if key is None:
                skip = True
                continue
            if isinstance(row[key], str) and row[key].isdigit():
                row[key] = int(row[key])
        if skip:
            continue
        yield row


def file_is_not_empty(filename):
    path = pathlib.Path(filename)
    return path.exists() and path.stat().st_size > 0


@click.command()
@click.argument("db_path", type=click.Path(file_okay=True, dir_okay=False))
@click.argument("big_local_token")
def populate_tables(db_path, big_local_token):
    biglocal_db = sqlite_utils.Database(db_path)
    # Just the CSV files below threshold
    rows = biglocal_db["files"].rows_where("ext = 'csv'", order_by="project, name")
    # Each project gets a separate file
    projects_by_id = {
        project["id"]: project for project in biglocal_db["projects"].rows
    }
    # Annotate projects with database_name
    database_names = set()
    for project in projects_by_id.values():
        project_name = project["name"].replace(" ", "_")
        database_name = project_name
        suffix = 1
        while database_name in database_names:
            suffix += 1
            database_name = "{}-{}".format(project_name, suffix)
        database_names.add(database_name)
        project["database_file"] = database_name + ".db"

    for row in rows:
        project = projects_by_id[row["project"]]
        database_file = project["database_file"]
        uri = uri_for_file(project["id"], row["name"], big_local_token)
        print(uri)
        # HEAD request to get size and ETag
        size, etag, status = size_and_etag_and_status(uri)
        if status != 200:
            print("Skipping {}, HTTP status = {}".format(row["name"], status))
            continue
        if size > THRESHOLD:
            print("Skipping {}, {} bytes is too large".format(row["name"], size))
            biglocal_db["files"].update(
                (row["project"], row["name"]),
                {"size": size},
                alter=True,
            )
            continue
        if etag and row.get("etag") == etag and file_is_not_empty(database_file):
            print("Skipping {}, ETag {} has not changed".format(row["name"], etag))
            continue

        # Update etag and size in database
        biglocal_db["files"].update(
            (row["project"], row["name"]),
            {"size": size, "etag": etag},
            alter=True,
        )

        db = sqlite_utils.Database(database_file)
        with db.conn:
            table_name = row["name"].replace(".csv", "")
            print("Fetching {} into DB {}".format(table_name, database_file))
            print(table_name, size)
            if db[table_name].exists():
                db[table_name].drop()
            db[table_name].insert_all(url_to_dicts(url=uri))
            if db[table_name].exists():
                print("Inserted {} rows".format(db[table_name].count))
            else:
                print("No rows so did not create table {}".format(table_name))


if __name__ == "__main__":
    populate_tables()
