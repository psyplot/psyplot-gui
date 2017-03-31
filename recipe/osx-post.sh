#!/bin/bash

PREFIXES_FILE=$HOME/.config/psyplot/psyplot-bins.txt

cp -r $PREFIX/psyplotapp $PREFIX/Psyplot.app
rm -rf $PREFIX/psyplotapp

ln -s -f $PREFIX/Psyplot.app /Applications/ >/dev/null 2>&1
if (( $? )); then
    mkdir -p $HOME/Applications
    ln -s -f $PREFIX/Psyplot.app $HOME/Applications/ || exit 0
fi

mkdir -p $HOME/.config/psyplot > /dev/null 2>&1

echo "$PREFIX" > ${PREFIXES_FILE}_new

if [[ -e $PREFIXES_FILE ]]; then
    cat $PREFIXES_FILE >> ${PREFIXES_FILE}_new
    mv ${PREFIXES_FILE}_new $PREFIXES_FILE
fi
