from bcdf.integrations.rclone import RCloneSyncer
from bcdf.analytics import schedulable_job
import os

#Running as hadoop
CUSTOM_BOOTSTRAP="""
sudo yum install -y pandoc
sudo usermod -a -G docker yarn
"""

# Running as yarn
@schedulable_job(schedule="10 11 ? * MON-FRI *", cluster_name="doc-generator", bootstrap=CUSTOM_BOOTSTRAP, job_queue='doc')
def main(date):
    import bmll2
    docdir=os.getcwd()
    print("docdir = ", docdir)
    # configure custom pandoc env
    with open(os.path.expanduser("~/bin/pandoc"),'w') as f:
        f.write('#!/bin/bash\nPANDOC_DATA_DIR='"$HOME"'/.pandoc/data /usr/bin/pandoc --data-dir='"$HOME"'/.pandoc/data  --abbreviations='"$HOME"'/.pandoc/data/abbreviations $*')
    os.system("chmod +x ~/bin/pandoc")
    os.system("cp -r /usr/share/pandoc/ ~/.local/share/")
    os.system("ln -s $PWD/template.tex ~/.local/share/pandoc/data/templates/bmll_template.latex")

    # run and build tje documentation
    os.system("INTERNAL_DOCS=0 python update_docs.py")
    rc=RCloneSyncer(os.path.join(docdir,'render'), "product_team/docs", area="organisation")
    os.system("rm -r render;INTERNAL_DOCS=1 python update_docs.py")
    rc=RCloneSyncer(os.path.join(docdir,'render'), "product_team/internal-docs", area="organisation")
    rc.upload()


