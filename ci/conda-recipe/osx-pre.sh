#!/bin/bash
# Script to uninstall the Psyplot.app on OSX
#
# This script runs after the deinstallation on of the conda package on OSX.
# It deletes the symbolic link named Psyplot.app in the /Applications folder or,
# if that doesn't exist, in the $HOME/Applications folder.


for LINKNAME in "/Applications/Psyplot.app" "$HOME/Applications/Psyplot.app"; do
    if [[ -e $LINKNAME ]]; then
        if [[ -h $LINKNAME ]]; then  # if it is a link, check it
            TARGET=`readlink $LINKNAME`
            if (( $? )); then  # assume GNU readlink
                TARGET=`readlink -f $LINKNAME`
            fi
            if [[ "$TARGET" == "$PREFIX/Psyplot.app" ]]; then
                rm $LINKNAME
            fi
        fi
    fi
done


rm -rf "$PREFIX/Psyplot.app"

exit 0
