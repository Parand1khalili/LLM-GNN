"""Command-line entry point for offline intake; never starts replay."""
try:
    from .admission import main, verify
except ImportError:
    from admission import main, verify

if __name__ == "__main__":
    raise SystemExit(main())
