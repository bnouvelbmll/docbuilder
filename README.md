The goal of this repository is the generation of the documentation for BMLL.
It should aims at allowing using visual tools to update the documentation.
(GRIST, online markdown editors, get data from our datbases, etc...) 

This is connected to other projects.

For simplicity, the documentation generation process can be runned on the lab.
For this is is sufficient to clone the repo and to run the adequate processes.

```
source activate $STABLE_VENV

# INSTALL BCDF AND DOCBUILDER
cd user; git clone git@github.com:bnouvelbmll/bcdf.git
(cd bcdf;  pip install -r requirements.txt ; pip install -e .)
cd user; git clone git@github.com:bnouvelbmll/docbuilder.git
(cd docbuilder; pip install -r requirements.txt)

# INSTALL PANDOC AND LATEX
bcdf _system dpkg pandoc
ln -sf $HOME/local/usr/share/pandoc ~/.pandoc
echo -e '#!/bin/bash\nPANDOC_DATA_DIR='"$HOME"'/.pandoc/data LD_LIBRARY_PATH='"$HOME"'/local/usr/lib/x86_64-linux-gnu  '"$HOME"'/local/usr/bin/pandoc --data-dir='"$HOME"'/.pandoc/data  --abbreviations='"$HOME"'/.pandoc/data/abbreviations $*' > ~/bin/pandoc
chmod +x ~/bin/pandoc
(cd /;tar -xzf ~/organisation/bertrand/tex.tgz )# generated from  https://tug.org/texlive/quickinstall.html
 ln -s ~/local/usr/share/pandoc/ ~/.local/share/
 
 [ -d docbuilder ] || cd ..
 ln -s $PWD/docbuilder/template.tex ~/.local/share/pandoc/data/templates/bmll_template.latex

# ENSURE BINARIES AND SCRIPTS ARE IN PATH
export PATH=/tmp/tex/bin/x86_64-linux:$HOME/bin:$PATH

# BUILD THE DOCUMENTATION
python update_docs.py
```

NOTE: The docbuilder requires access to grist and to snowflake...
We will get adequate read-only tokens for the lab.
This will allow us to run this as scheduled task.

On clusters, texlive can run via docker and apt-get install can be used for pandoc,
bcdf contains the logic for automating running scripts that are in the repo.

It is not yet finalised but ultimately it should be a case of doing:
```
bcdf ./update_docs.py job install 
```

To set credentials, you can use the following:
```
bcdf secrets set BMLL_GTHUB_TOKEN <token>
bcdf secrets set BMLL_SNOWFLAKE_CREDENTIAL <token>
```
