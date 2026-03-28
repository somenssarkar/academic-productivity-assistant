# start_toolbox.ps1 — Start MCP Toolbox locally on Windows (PowerShell)

param(
    [string]$ToolboxBin = "toolbox",
    [string]$ToolsFile  = "mcp_servers\database\tools.yaml",
    [int]   $Port       = 5000
)

# Required env vars — set these in your shell or .env before running
if (-not $env:GOOGLE_CLOUD_PROJECT) { throw "GOOGLE_CLOUD_PROJECT is not set" }
if (-not $env:DB_USER)              { throw "DB_USER is not set" }
if (-not $env:DB_PASSWORD)          { throw "DB_PASSWORD is not set" }

Write-Host "==> Starting MCP Toolbox on port $Port"
Write-Host "    Tools file: $ToolsFile"
Write-Host "    Project: $env:GOOGLE_CLOUD_PROJECT"

& $ToolboxBin --tools-file=$ToolsFile --port=$Port
