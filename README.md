The goal of this repository is the generation of the documentation for BMLL.
It should aims at allowing using visual tools to update the documentation.
(GRIST, online markdown editors, get data from our datbases, etc...) 

This is connected to other projects.

For simplicity, the documentation generation process can be runned on the lab.
For this is is sufficient to clone the repo and to run the adequate processes.

```
cd user; git clone git@github.com:bnouvelbmll/docbuilder.git

echo -e '#!/bin/bash\nexec TEXMFHOME=~/local/usr/share/texlive/texmf-dist/ LD_LIBRARY_PATH=~/local/usr/lib/x86_64-linux-gnu/ ~/local/usr/bin/latex' &> ~/bin/pdflatex
chmod +x ~/bin/pdflatex

python update_docs
```