#!/bin/bash

echo 'Running "prepdocs_dual.py" - Config-driven dual-index document preparation'
echo ''

# Load Python environment
. ./scripts/load_python_env.sh

# Run the dual prepdocs script with verbose output by default
./.venv/bin/python ./app/backend/prepdocs_dual.py --verbose "$@"
