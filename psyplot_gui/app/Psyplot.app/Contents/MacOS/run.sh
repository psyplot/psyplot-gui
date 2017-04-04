#!/bin/bash

# if psyplot-bins.txt is existent, loop through it until an existing binary is
# found
if [[ -e $HOME/.config/psyplot/psyplot-bins.txt ]]; then
    while IFS='' read -r PREFIX; do
        if [[ $PREFIX != '' ]]; then
            BIN=$PREFIX/bin/psyplot
            if [[ -e $BIN ]]; then
                break
            fi
        fi
    done < $HOME/.config/psyplot/psyplot-bins.txt
    source activate $PREFIX
    $BIN -pwd $HOME
else  # otherwise assume psyplot is installed in default python
    python -m psyplot
fi
