"""Fresh account-panel endpoint canary; separate from the historical failed intent."""
from .canary import main

if __name__ == "__main__":
    raise SystemExit(main(target="account-panel"))
