"""Command-line module entrypoint for `python -m netbox`."""

from netbox.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
