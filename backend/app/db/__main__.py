import sys

from app.db.migrate import migrate
from app.settings import Settings


def main(argv: list[str]) -> int:
    if argv != ["migrate"]:
        print("usage: python -m app.db migrate", file=sys.stderr)
        return 2
    version = migrate(Settings().database_path)
    print(f"database at schema version {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
