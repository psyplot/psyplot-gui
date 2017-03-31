#!/bin/bash
set -e

PREFIXES_FILE=$HOME/.config/psyplot/psyplot-bins.txt

if [[ -e ${PREFIXES_FILE}_new ]]; then
    rm ${PREFIXES_FILE}_new
fi

while IFS='' read -r CURRENT_PREFIX; do
    if [[ $CURRENT_PREFIX != $PREFIX ]]; then
        echo $CURRENT_PREFIX > ${PREFIXES_FILE}_new
    fi
done < $PREFIXES_FILE

if [[ -e ${PREFIXES_FILE}_new ]]; then
    mv ${PREFIXES_FILE}_new $PREFIXES_FILE
else

    rm -rf $PREFIX/Psyplot.app
    rm -f /Applications/Psyplot.app
    rm -f $HOME/Applications/Psyplot.app
fi
