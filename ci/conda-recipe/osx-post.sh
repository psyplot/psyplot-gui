#!/bin/bash
# Script to install the Psyplot.app on OSX
#
# This script runs after the installation on of the conda package on OSX.
# It creates a symbolic link name Psyplot.app in the /Applications folder or, if
# that doesn't work, in the $HOME/Applications folder.
#
# This link points to the Psyplot.app folder in this environment.

cp -r "$PREFIX"/psyplotapp "$PREFIX"/Psyplot.app
rm -rf "$PREFIX"/psyplotapp

# set the correct paths in run.sh
cat > "$PREFIX"/Psyplot.app/Contents/MacOS/run.sh << EOF
#!/bin/bash
source "$PREFIX"/bin/activate "$PREFIX"
"$PREFIX"/bin/python "$PREFIX"/bin/psyplot -pwd \$HOME \$@
EOF

exit 0
