# One-off: sync backend-fastapi Cloud Run env from .env (not committed; run locally).
$ErrorActionPreference = 'Stop'
$Service = 'backend-fastapi'
$Region = 'us-central1'
$Project = 'meetstreamiq'
$EnvPath = Join-Path $PSScriptRoot '.env'

function Invoke-SetEnv([string] $Pair) {
  & gcloud run services update $Service --region=$Region --project=$Project --update-env-vars=$Pair
  if ($LASTEXITCODE -ne 0) { throw "gcloud failed for: $Pair" }
}

$map = @{}
Get-Content $EnvPath -Encoding UTF8 | ForEach-Object {
  $line = $_.Trim()
  if ($line -eq '' -or $line.StartsWith('#')) { return }
  $i = $line.IndexOf('=')
  if ($i -lt 0) { return }
  $k = $line.Substring(0, $i).Trim()
  $v = $line.Substring($i + 1).Trim()
  $map[$k] = $v
}

$supabaseUrl = 'https://ppefvkciihgfilyrrmge.supabase.co'
Invoke-SetEnv "SUPABASE_URL=$supabaseUrl"
Invoke-SetEnv "SUPABASE_SERVICE_ROLE_KEY=$($map['SUPABASE_SERVICE_ROLE_KEY'])"
Invoke-SetEnv "SUPABASE_JWT_SECRET=$($map['SUPABASE_JWT_SECRET'])"
Invoke-SetEnv "RECALL_API_KEY=$($map['RECALL_API_KEY'])"
Invoke-SetEnv "RECALL_API_BASE=$($map['RECALL_API_BASE'])"
Invoke-SetEnv 'PUBLIC_API_BASE=https://backend-fastapi-773946290671.us-central1.run.app'
# CORS URLs contain ":" and "," — use flags-file so gcloud parses one key cleanly
$CorsFile = Join-Path $PSScriptRoot '_cors_flags.yaml'
$corsVal = $map['CORS_ORIGINS']
@"
--update-env-vars:
  CORS_ORIGINS: "$corsVal"
"@ | Set-Content -Path $CorsFile -Encoding UTF8
& gcloud run services update $Service --region=$Region --project=$Project --flags-file=$CorsFile
if ($LASTEXITCODE -ne 0) { throw "gcloud CORS flags-file failed" }
Invoke-SetEnv 'GCP_PROJECT=meetstreamiq,GCP_LOCATION=us-central1'

if ($map.ContainsKey('RESEND_API_KEY') -and $map['RESEND_API_KEY']) {
  $ResendFile = Join-Path $PSScriptRoot '_resend_flags.yaml'
  @"
--update-env-vars:
  RESEND_API_KEY: "$($map['RESEND_API_KEY'])"
"@ | Set-Content -Path $ResendFile -Encoding UTF8
  & gcloud run services update $Service --region=$Region --project=$Project --flags-file=$ResendFile
  if ($LASTEXITCODE -ne 0) { throw "gcloud RESEND flags-file failed" }
}

Write-Host 'Cloud Run env vars updated.'
