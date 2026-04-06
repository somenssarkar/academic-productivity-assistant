# start_toolbox.ps1 — Start MCP Toolbox locally on Windows (PowerShell)
# Run from repo root: .\scripts\infra\start_toolbox.ps1

param(
    [string]$ToolboxBin = "scripts\infra\toolbox.exe",
    [string]$ToolsFile  = "mcp_servers\database\tools.yaml",
    [string]$EnvFile    = "eduflow_agents\.env",
    [int]   $Port       = 5000
)

# Load .env file into shell environment
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim())
        }
    }
    Write-Host "==> Loaded env vars from $EnvFile"
}

# Validate required vars
if (-not $env:GOOGLE_CLOUD_PROJECT) { throw "GOOGLE_CLOUD_PROJECT is not set" }
if (-not $env:DB_USER)              { throw "DB_USER is not set" }
if (-not $env:DB_PASSWORD)          { throw "DB_PASSWORD is not set" }
if (-not $env:DB_REGION)            { throw "DB_REGION is not set (e.g. asia-southeast1)" }
if (-not $env:DB_INSTANCE)          { throw "DB_INSTANCE is not set (e.g. eduflow-db)" }

Write-Host "==> Starting MCP Toolbox on port $Port"
Write-Host "    Tools file: $ToolsFile"
Write-Host "    DB: $env:GOOGLE_CLOUD_PROJECT/$env:DB_REGION/$env:DB_INSTANCE/eduflow"

& $ToolboxBin --tools-file=$ToolsFile --port=$Port
