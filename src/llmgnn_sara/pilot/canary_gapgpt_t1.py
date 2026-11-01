"""Explicitly approved temperature1 derivative; never automatic fallback."""
from .canary import main

if __name__ == "__main__":
    raise SystemExit(main(target="account-panel-temperature1"))
