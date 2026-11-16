"""Entry point: python -I bench.py run [tests...]"""

import sys
from pathlib import Path

# -I leaves the script's directory off sys.path; add it explicitly.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ps1bench.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
