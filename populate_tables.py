import sqlite_utils, csv, pathlib, requests

THRESHOLD = 50000000


def size_and_etag_and_status(url):
    response = requests.head(url)
    status = response.status_code
    return int(response.headers["Content-Length"]), response.headers.get("ETag"), status


def url_to_dicts(url):
    response = requests.get(url, stream=True)
    reader = csv.DictReader(line.decode("utf-8") for line in response.iter_lines())
    for row in reader:
        for key in row:
            if row[key].isdigit():
                row[key] = int(row[key])
        yield row


def file_is_not_empty(filename):
    path = pathlib.Path(filename)
    return path.exists() and path.stat().st_size > 0


def populate_tables(biglocal_db):
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
        if not row["uri"]:
            print("Skipping {}, uri is null".format(row["name"]))
            continue
        # HEAD request to get size and ETag
        size, etag, status = size_and_etag_and_status(row["uri"])
        if status != 200:
            print("Skipping {}, HTTP status = {}".format(row["name"], status))
            continue
        if size > THRESHOLD:
            print("Skipping {}, {} bytes is too large".format(row["name"], size))
            biglocal_db["files"].update(
                (row["project"], row["name"]), {"size": size}, alter=True,
            )
            continue
        if etag and row.get("etag") == etag and file_is_not_empty(database_file):
            print("Skipping {}, ETag {} has not changed".format(row["name"], etag))
            continue

        # Update etag and size in database
        biglocal_db["files"].update(
            (row["project"], row["name"]), {"size": size, "etag": etag}, alter=True,
        )

        db = sqlite_utils.Database(database_file)
        with db.conn:
            table_name = row["name"].replace(".csv", "")
            print("Fetching {} into DB {}".format(table_name, database_file))
            print(table_name, size)
            if db[table_name].exists():
                db[table_name].drop()
            db[table_name].insert_all(url_to_dicts(url=row["uri"]))
            print("Inserted {} rows".format(db[table_name].count))


if __name__ == "__main__":
    db = sqlite_utils.Database("biglocal.db")
    populate_tables(db)
