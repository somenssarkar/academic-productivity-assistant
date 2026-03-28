#!/usr/bin/env bash
# start_toolbox.sh — Start MCP Toolbox locally for development
# Requires: toolbox binary in PATH or ./toolbox

set -euo pipefail

TOOLBOX_BIN="${TOOLBOX_BIN:-toolbox}"
TOOLS_FILE="${TOOLS_FILE:-mcp_servers/database/tools.yaml}"
PORT="${TOOLBOX_PORT:-5000}"

# Export required env vars (toolbox reads these for AlloyDB connection)
export GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT}"
export DB_USER="${DB_USER:?Set DB_USER}"
export DB_PASSWORD="${DB_PASSWORD:?Set DB_PASSWORD}"

echo "==> Starting MCP Toolbox on port $PORT"
echo "    Tools file: $TOOLS_FILE"
echo "    Project: $GOOGLE_CLOUD_PROJECT"

"$TOOLBOX_BIN" --tools-file="$TOOLS_FILE" --port="$PORT"
