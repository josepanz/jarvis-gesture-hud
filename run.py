"""Entry point portable: agrega src/ al path y arranca Jarvis."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from jarvis.main import main

if __name__ == "__main__":
    main()
