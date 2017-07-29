# script to upload files to anaconda


function UploadToAnaconda ($architecture, $python_home) {
    Write-Host "Uploading files for" $architecture "from" $python_home

    $basedir = $pwd.Path + "\"
    $filepath = $python_home + "\conda-bld\win-" + $architecture + "\psyplot-gui-*-py*.tar.bz2"
    $filepath = Resolve-Path $filepath
    Write-Host "Uploading" $filepath
    $anaconda_path = $python_home + "\Scripts\anaconda.exe"
    $args = "-t " + $env:CONDA_REPO_TOKEN +" upload " + $filepath
    Write-Host $filepath $args
    Start-Process -FilePath $anaconda_path -ArgumentList $args -Wait -Passthru
    if (Test-Path $python_home) {
        Write-Host "Upload complete"
    } else {
        Write-Host "Failed."
        Exit 1
    }
}


function main () {
    UploadToAnaconda $env:PYTHON_ARCH $env:PYTHON
}

main
