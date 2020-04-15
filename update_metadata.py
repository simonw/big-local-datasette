import sqlite_utils
import sys
import json


def update_metadata(db, in_metadata_path, out_metadata_path):
    metadata = json.load(open(in_metadata_path))
    metadata["databases"] = metadata.get("databases") or {}
    for project in db["projects"].rows:
        about = {}
        db_name = project["name"].replace(" ", "_")
        metadata["databases"][db_name] = metadata["databases"].get(db_name) or {}
        if project.get("readme_markdown"):
            about = {
                "about": "README",
                "about_url": "/biglocal/readme?id={}&_hide_sql=1".format(project["id"]),
            }

        metadata["databases"][db_name].update(
            dict({"description": project["description"] or "", "tables": {},}, **about)
        )
        # And for all of the tables
        for row in db["files"].rows_where("project = ?", [project["id"]]):
            if row["ext"] == "csv":
                table_name = row["name"].replace(".csv", "")
                table_metadata = {"description": project["description"] or ""}
                if about:
                    table_metadata.update(about)
                metadata["databases"][db_name]["tables"][table_name] = table_metadata
    open(out_metadata_path, "w").write(json.dumps(metadata, indent=4))


if __name__ == "__main__":
    db_path, in_metadata_path, out_metadata_path = (
        sys.argv[-3],
        sys.argv[-2],
        sys.argv[-1],
    )
    assert db_path.endswith(".db")
    assert in_metadata_path.endswith(".json")
    assert out_metadata_path.endswith(".json")
    assert in_metadata_path != out_metadata_path
    db = sqlite_utils.Database(db_path)
    update_metadata(db, in_metadata_path, out_metadata_path)
