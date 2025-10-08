"""Utility script to list the first line (header) of every file under Data/Provider."""

import os


def list_first_lines(root_dir):
    if not os.path.exists(root_dir):
        print(f"Directory does not exist: {root_dir}")
        return

    print(f"Listing first lines under: {root_dir}")
    for current_root, _dirs, files in os.walk(root_dir):
        for name in sorted(files):
            file_path = os.path.join(current_root, name)
            rel_path = os.path.relpath(file_path, root_dir)
            first_line = "<empty>"
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
                    first_line = fh.readline().rstrip("\n\r") or "<empty>"
            except OSError as exc:
                first_line = f"<error: {exc}>"
            print(f"{rel_path}: {first_line}")


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    provider_dir = os.path.join(script_dir, "Data", "Provider")
    list_first_lines(provider_dir)

