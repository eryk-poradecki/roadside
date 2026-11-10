"""Print the API's OpenAPI document as JSON (input for the frontend's client codegen)."""

import json
import sys

from app.main import create_app


def main() -> None:
    json.dump(create_app().openapi(), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
