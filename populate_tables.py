import sqlite_utils, csv, requests

THRESHOLD = 50000000

def url_to_dicts(url):
    response = requests.get(url, stream=True)
    reader = csv.DictReader(line.decode('utf-8') for line in response.iter_lines())
    yield from reader


def populate_tables(db):
    # Just the CSV files below threshold
    rows = db["files"].rows_where("ext = 'csv' and size < ?", [THRESHOLD])
    for row in rows:
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
