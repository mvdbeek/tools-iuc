from __future__ import division, print_function

import argparse
import hashlib
import json
import os
import os.path
import subprocess

DATA_TABLE_NAME = "ncbi_taxonomy_sqlite"


def taxonomy_digest(taxonomy_dir):
    """Hash the two source files consumed by taxonomy_util."""
    digest = hashlib.sha256()
    for filename in ("nodes.dmp", "names.dmp"):
        file_digest = hashlib.sha256()
        with open(os.path.join(taxonomy_dir, filename), "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                file_digest.update(chunk)
        digest.update(filename.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_digest.digest())
    return digest.hexdigest()


def build_sqlite(taxonomy_dir, output_directory, name=None, description=None):
    if not os.path.exists(output_directory):
        os.mkdir(output_directory)
    output_filename = os.path.join(output_directory, "tax.ncbitaxonomy.sqlite")
    subprocess.check_call(
        ["taxonomy_util", "-d", output_filename, "to_sqlite", taxonomy_dir]
    )

    source_digest = taxonomy_digest(taxonomy_dir)
    value = "ncbitaxonomy_sha256_{}".format(source_digest)

    if description is None or description.strip() == "":
        display_name = name.strip() if name and name.strip() else "NCBI Taxonomy database"
        description = "{} (source sha256:{})".format(
            display_name, source_digest[:12]
        )

    data = [dict(value=value, description=description, path=output_filename)]
    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build SQLite database from NCBI taxonomy"
    )
    parser.add_argument(
        "--output_directory", default="tmp", help="Directory to write output to"
    )
    parser.add_argument(
        "taxonomy_dir",
        help="Path to directory containing NCBI Taxonomy nodes.dml and names.dmp file"
    )
    parser.add_argument(
        "name",
        help="Name to use for the entry in the data table"
    )
    parser.add_argument(
        "description",
        help="Description to use for the entry in the data table"
    )
    parser.add_argument(
        "galaxy_datamanager_filename",
        help="Galaxy JSON format file describing data manager inputs",
    )
    args = parser.parse_args()

    with open(args.galaxy_datamanager_filename) as fh:
        config = json.load(fh)
    output_directory = config.get("output_data", [{}])[0].get("extra_files_path", None)
    if output_directory is None:
        output_directory = args.output_directory

    if not os.path.isdir(output_directory):
        os.makedirs(output_directory)

    data_manager_dict = {}
    data_manager_dict["data_tables"] = config.get("data_tables", {})
    data_manager_dict["data_tables"][DATA_TABLE_NAME] = data_manager_dict[
        "data_tables"
    ].get(DATA_TABLE_NAME, [])

    data = build_sqlite(args.taxonomy_dir, output_directory, args.name, args.description)

    data_manager_dict["data_tables"][DATA_TABLE_NAME].extend(data)
    with open(args.galaxy_datamanager_filename, "w") as fh:
        json.dump(data_manager_dict, fh, sort_keys=True)
        fh.write("\n")
