"""Owner-confirmed four never-attempted nodes; importing never dispatches."""
from .outstanding_gapgpt import main

if __name__ == "__main__":
    raise SystemExit(main(four_only=True))
