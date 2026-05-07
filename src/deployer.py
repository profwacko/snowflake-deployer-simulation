import os
import re
import sys

import yaml


SNOWFLAKE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snowflake")
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def tryint(s):
    try:
        return int(s)
    except ValueError:
        return s


def alphanum_key(s):
    """Turn a string into a list of string and number chunks for lexicographic sort.
    "z22a" -> ["z", 22, "a"]
    """
    return [tryint(c) for c in re.split(r"(\d+)", s)]


def collect_files_non_prod():
    """Walk src/snowflake and collect all .sql files in lexicographic order."""
    files = []
    for subdir, dirs, filenames in os.walk(SNOWFLAKE_DIR, topdown=True):
        dirs.sort(key=alphanum_key)
        for filename in sorted(filenames, key=alphanum_key):
            if filename.endswith(".sql"):
                files.append(os.path.join(subdir, filename))
    return sorted(files, key=alphanum_key)


def collect_files_prod():
    """Walk src/snowflake for prod.yaml files; execute each only if changes detected in that directory."""
    import subprocess

    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/master...HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    changed = set(result.stdout.splitlines())

    files = []
    for subdir, dirs, filenames in os.walk(SNOWFLAKE_DIR, topdown=True):
        dirs.sort(key=alphanum_key)
        if "prod.yaml" not in filenames:
            continue
        rel_subdir = os.path.relpath(subdir, REPO_ROOT).replace(os.sep, "/")
        if not any(p.startswith(rel_subdir + "/") for p in changed):
            continue
        yaml_path = os.path.join(subdir, "prod.yaml")
        print(f"Loading prod.yaml: {os.path.relpath(yaml_path, REPO_ROOT)}")
        with open(yaml_path) as f:
            paths = yaml.safe_load(f)
        if not paths:
            raise ValueError(f"{yaml_path} is empty or invalid")
        for path in paths:
            full_path = os.path.join(subdir, path)
            if not os.path.isfile(full_path):
                raise FileNotFoundError(f"File listed in {yaml_path} not found: {full_path}")
            files.append(full_path)
    return files


# Reference implementation provided as a starting point for contributors.
def collect_files_changed(base_branch):
    """Collect .sql files under src/snowflake that changed vs. origin/<base_branch>."""
    import subprocess

    result = subprocess.run(
        ["git", "diff", "--name-only", f"origin/{base_branch}...HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    changed = result.stdout.splitlines()
    files = []
    for path in changed:
        full_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), path
        )
        if full_path.startswith(SNOWFLAKE_DIR) and path.endswith(".sql"):
            if os.path.isfile(full_path):
                files.append(full_path)
    return sorted(files, key=alphanum_key)


def relative_path(file):
    return os.path.relpath(file, SNOWFLAKE_DIR)


def execute_files(files):
    for file in files:
        print(f"Executing {relative_path(file)}")


def main():
    env = os.environ.get("ENV")
    if env is None:
        print(
            "ERROR: ENV environment variable is not set. Use NON_PROD or PROD.",
            file=sys.stderr,
        )
        sys.exit(1)

    if env == "DEV":
        print("Running in DEV mode: executing diffs lexicographically.")
        files = collect_files_changed("dev")
    elif env == "UAT":
        print("Running in UAT mode: executing diffs lexicographically.")
        files = collect_files_changed("uat")
    elif env == "NON_PROD":
        print("Running in NON-PROD mode: executing diffs lexicographically.")
        files = collect_files_changed("master")
    elif env == "PROD":
        print("Running in PROD mode: executing whitelisted files from prod.yaml.")
        files = collect_files_prod()
    else:
        print(
            f"ERROR: Unknown ENV value '{env}'. Use DEV, UAT, NON_PROD, or PROD.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Files to execute ({len(files)}):")
    for f in files:
        print(f"  {relative_path(f)}")
    print()

    execute_files(files)


if __name__ == "__main__":
    main()
