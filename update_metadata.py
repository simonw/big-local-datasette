import sqlite_utils
import sys
import json


def update_metadata(db, filepath):
    metadata = json.load(open(filepath))
    metadata["databases"] = {}
    for project in db["projects"].rows:
        db_name = project["name"].replace(" ", "_")
        metadata["databases"][db_name] = {
            "description": project["description"] or "",
            "tables": {},
        }
        # And for all of the tables
        for row in db["files"].rows_where("project = ?", [project["id"]]):
            if row["ext"] == "csv":
                table_name = row["name"].replace(".csv", "")
                metadata["databases"][db_name]["tables"][table_name] = {
                    "description": project["description"] or ""
                }
    open(filepath, "w").write(json.dumps(metadata, indent=4))


if __name__ == "__main__":
    db_path, metadata_path = sys.argv[-2], sys.argv[-1]
    assert db_path.endswith(".db")
    assert metadata_path.endswith(".json")
    db = sqlite_utils.Database(db_path)
    update_metadata(db, metadata_path)
