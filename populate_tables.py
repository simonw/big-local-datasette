import sqlite_utils, csv, requests

THRESHOLD = 50000000


def url_to_dicts(url):
    response = requests.get(url, stream=True)
    reader = csv.DictReader(line.decode("utf-8") for line in response.iter_lines())
    yield from reader


def populate_tables(biglocal_db):
    # Just the CSV files below threshold
    rows = biglocal_db["files"].rows_where("ext = 'csv' and size < ?", [THRESHOLD])
    # Each project gets a separate file
    project_databases = {}
    database_names = set()
    for row in rows:
        project_id = row["project"]
        if project_id in project_databases:
            db = project_databases[project_id]
        else:
            # Make a new database
            project = biglocal_db["projects"].get(project_id)
            project_name = project["name"].replace(" ", "_")
            database_name = project_name
            suffix = 1
            while database_name in database_names:
                suffix += 1
                database_name = "{}-{}".format(project_name, suffix)
            db = sqlite_utils.Database(database_name + ".db")
            project_databases[project_id] = db
        url = row["uri"]
        # TODO: Avoid duplicate table names
        table_name = row["name"].replace(".csv", "")
        print(table_name, row["size"])
        if db[table_name].exists():
            db[table_name].drop()
        db[table_name].insert_all(url_to_dicts(url))


if __name__ == "__main__":
    db = sqlite_utils.Database("biglocal.db")
    populate_tables(db)
