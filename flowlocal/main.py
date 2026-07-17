"""Entry point: dispatch to the platform app."""

import sys


def main() -> None:
    if sys.platform == "darwin":
        from .app import main as run
    elif sys.platform == "win32":
        from .app_win import main as run
    else:
        sys.exit("FlowLocal supports macOS (Apple Silicon) and Windows.")
    run()


if __name__ == "__main__":
    main()
