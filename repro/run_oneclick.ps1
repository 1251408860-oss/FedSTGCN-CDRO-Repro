param(
  [string]$Distro = "Ubuntu1",
  [string]$ProjectDir = "/home/user/FedSTGCN",
  [string]$Script = "repro/run_oneclick_recharge.sh"
)

$cmd = "cd $ProjectDir && bash $Script"
Write-Host "[RUN] wsl -d $Distro bash -lc '$cmd'"
wsl -d $Distro bash -lc $cmd
if ($LASTEXITCODE -ne 0) {
  throw "one-click run failed with exit code $LASTEXITCODE"
}
