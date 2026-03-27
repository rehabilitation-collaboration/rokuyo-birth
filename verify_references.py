"""Reference verification wrapper — delegates to the shared tool.

Usage:
    python verify_references.py [manuscript.md]

Output is written to output/reference_verification.{md,json}.
"""

import subprocess
import sys
from pathlib import Path

TOOL = Path.home() / "claude" / "internal" / "tools" / "verify_refs.py"
MANUSCRIPT = Path(__file__).parent / "manuscript.md"


def main():
    manuscript = Path(sys.argv[1]) if len(sys.argv) > 1 else MANUSCRIPT
    output_dir = manuscript.parent / "output"
    cmd = [sys.executable, str(TOOL), str(manuscript), "--output-dir", str(output_dir)]
    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main())
