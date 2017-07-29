# script to upload files to anaconda


function UploadToAnaconda ($architecture, $python_home) {
    Write-Host "Uploading files for" $architecture "from" $python_home

    if ($architecture -match "32") {
        $architecture2 = "64"
    } else {
        $architecture2 = "32"
    }

    $basedir = $pwd.Path + "\"
    $filepath = $python_home + "\conda-bld\win-" + $architecture + "\psyplot-gui-*-py*.tar.bz2"
    $filepath = Resolve-Path $filepath
    $conda_path = $python_home + "\Scripts\conda.exe"

    Write-Host "Converting to win-" + $architecture2
    $args = "-p " + "win-" + $architecture2 + " $filepath"
    Write-Host $conda_path $args
    $proc = (Start-Process -FilePath $conda_path -ArgumentList $args -Wait -Passthru)
    if ($proc.ExitCode -ne 0) {
        Write-Host "Failed."
        Exit 1
    } else {
        Write-Host "Upload complete"
    }

    $filepath2 = $basedir + "win-" + $architecture2 + "\psyplot-gui*.tar.bz2"
    $filepath2 = Resolve-Path $filepath2

    Write-Host "Uploading" $filepath
    $anaconda_path = $python_home + "\Scripts\anaconda.exe"
    $args = "-t " + $env:CONDA_REPO_TOKEN +" upload " + $filepath + " " + $filepath2
    Write-Host $anaconda_path $args
    $proc = (Start-Process -FilePath $anaconda_path -ArgumentList $args -Wait -Passthru)
    if ($proc.ExitCode -ne 0) {
        Write-Host "Failed."
        Exit 1
    } else {
        Write-Host "Upload complete"
    }
}


function main () {
    UploadToAnaconda $env:PYTHON_ARCH $env:PYTHON
}

main
