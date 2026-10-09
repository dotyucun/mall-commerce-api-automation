param(
    [Parameter(Position = 0)]
    [ValidateSet("bootstrap", "test", "full", "slow", "verify", "report", "performance", "stop", "down", "status")]
    [string]$Action = "test"
)

$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$Root = Split-Path -Parent $PSScriptRoot
$ComposeFile = Join-Path $Root "docker\compose.test.yml"
$ManagedSource = Join-Path $Root ".sut\mall"
$SutCommit = "0504e86b1f1b6f1b8aa6a734d37a90fb67346be7"

function Import-DotEnv {
    $path = Join-Path $Root ".env"
    if (-not (Test-Path $path)) { return }
    Get-Content -Encoding UTF8 $path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) { return }
        $name, $value = $line -split "=", 2
        if ($name -and $null -ne $value) {
            [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim(), "Process")
        }
    }
}

function Assert-Environment {
    $required = @(
        "MALL_ADMIN_PASSWORD",
        "MALL_TEST_USER_A_PASSWORD",
        "MALL_TEST_USER_B_PASSWORD",
        "MALL_MYSQL_PASSWORD",
        "MALL_RABBITMQ_PASSWORD"
    )
    $missing = $required | Where-Object { -not [Environment]::GetEnvironmentVariable($_, "Process") }
    if ($missing) {
        throw "Missing environment variables: $($missing -join ', '). Create .env from .env.example."
    }
}

function Assert-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

function Invoke-Checked {
    param([string]$Name, [string[]]$Arguments)
    Assert-Command $Name
    & $Name @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

function Set-SutSource {
    $source = if ($env:MALL_SOURCE_DIR) { $env:MALL_SOURCE_DIR } else { $ManagedSource }
    $env:MALL_SOURCE_DIR = [System.IO.Path]::GetFullPath($source).Replace("\", "/")
}

function Ensure-Docker {
    Assert-Command "docker"
    try {
        docker info *> $null
        $ready = $LASTEXITCODE -eq 0
    } catch { $ready = $false }
    if (-not $ready) {
        $desktop = Join-Path $env:LOCALAPPDATA "Programs\DockerDesktop\Docker Desktop.exe"
        if (-not (Test-Path $desktop)) { throw "Docker engine is not running" }
        Start-Process -FilePath $desktop -WindowStyle Hidden
        $deadline = (Get-Date).AddMinutes(3)
        do {
            Start-Sleep -Seconds 3
            try {
                docker info *> $null
                if ($LASTEXITCODE -eq 0) { return }
            } catch { }
        } while ((Get-Date) -lt $deadline)
        throw "Docker Desktop did not become ready within 3 minutes"
    }
}

function Ensure-Sut {
    Assert-Command "git"
    Assert-Command "mvn"
    if (-not (Test-Path (Join-Path $env:MALL_SOURCE_DIR ".git"))) {
        New-Item -ItemType Directory -Force -Path (Split-Path $env:MALL_SOURCE_DIR) | Out-Null
        Invoke-Checked "git" @("clone", "https://github.com/macrozheng/mall.git", $env:MALL_SOURCE_DIR)
    }
    $actualCommit = Invoke-Checked "git" @("-C", $env:MALL_SOURCE_DIR, "rev-parse", "HEAD")
    if ($actualCommit -ne $SutCommit) {
        if ($env:MALL_SOURCE_DIR -ne [System.IO.Path]::GetFullPath($ManagedSource).Replace("\", "/")) {
            throw "External MALL_SOURCE_DIR must already be at commit $SutCommit; actual: $actualCommit"
        }
        $dirty = Invoke-Checked "git" @("-C", $env:MALL_SOURCE_DIR, "status", "--porcelain")
        if ($dirty) { throw "Managed SUT checkout has local changes; refusing to change its commit" }
        Invoke-Checked "git" @("-C", $env:MALL_SOURCE_DIR, "fetch", "origin", $SutCommit)
        Invoke-Checked "git" @("-C", $env:MALL_SOURCE_DIR, "checkout", "--detach", $SutCommit)
    }
    Invoke-Checked "mvn" @(
        "-f", (Join-Path $env:MALL_SOURCE_DIR "pom.xml"),
        "-pl", "mall-admin,mall-portal", "-am", "-DskipTests", "-Ddocker.skip=true", "package"
    )
}

Import-DotEnv
Set-SutSource

switch ($Action) {
    "bootstrap" {
        Assert-Environment
        Ensure-Docker
        Ensure-Sut
        Invoke-Checked "python" @("-m", "pip", "install", "-r", (Join-Path $Root "requirements.txt"))
        Invoke-Checked "python" @("-m", "pip", "install", "--no-deps", "-e", $Root)
        Invoke-Checked "docker" @("compose", "-f", $ComposeFile, "up", "-d")
        Invoke-Checked "python" @((Join-Path $PSScriptRoot "wait_for_services.py"))
        Invoke-Checked "python" @((Join-Path $PSScriptRoot "prepare_test_data.py"))
        Invoke-Checked "docker" @(
            "compose", "-f", $ComposeFile, "exec", "-T", "redis", "redis-cli", "DEL",
            "mall:ums:admin:admin", "mall:ums:member:autotest_a", "mall:ums:member:autotest_b"
        )
    }
    "test" {
        Assert-Environment
        Push-Location $Root
        try { Invoke-Checked "python" @("-m", "pytest", "-m", "not slow") } finally { Pop-Location }
    }
    "slow" {
        Assert-Environment
        Push-Location $Root
        try { Invoke-Checked "python" @("-m", "pytest", "-m", "slow") } finally { Pop-Location }
    }
    "full" {
        Assert-Environment
        Push-Location $Root
        try { Invoke-Checked "python" @("-m", "pytest") } finally { Pop-Location }
    }
    "verify" {
        Assert-Environment
        Invoke-Checked "python" @((Join-Path $PSScriptRoot "verify_test_data.py"))
    }
    "report" {
        Assert-Command "allure"
        Invoke-Checked "allure" @(
            "generate", (Join-Path $Root "reports\allure-results"),
            "-o", (Join-Path $Root "reports\allure-report"), "--clean"
        )
    }
    "performance" {
        Assert-Environment
        $reportDir = Join-Path $Root "reports\locust"
        New-Item -ItemType Directory -Force -Path $reportDir | Out-Null
        Invoke-Checked "locust" @(
            "-f", (Join-Path $Root "performance\locustfile.py"), "--headless",
            "-u", "20", "-r", "2", "-t", "2m", "--html", (Join-Path $reportDir "report.html"),
            "--csv", (Join-Path $reportDir "metrics")
        )
    }
    "stop" {
        Ensure-Docker
        Invoke-Checked "docker" @("compose", "-f", $ComposeFile, "stop")
    }
    "down" {
        Ensure-Docker
        Invoke-Checked "docker" @("compose", "-f", $ComposeFile, "down", "--remove-orphans")
    }
    "status" {
        Ensure-Docker
        Invoke-Checked "docker" @("compose", "-f", $ComposeFile, "ps")
    }
}
