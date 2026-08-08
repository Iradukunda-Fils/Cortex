"""
Cortex Platform CLI Execution Entrypoint

Enables executing the Cortex Developer CLI directly via Python module dispatch:
    python3 -m cortex <command> [options]
"""

import sys
from cortex.tools.cli.main import main

if __name__ == "__main__":
    sys.exit(main())
