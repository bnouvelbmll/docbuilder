from bcdf.integrations.rclone import RCloneSyncer
from bcdf import bmll_scheduled_job

#Running as hadoop
CUSTOM_BOOTSTRAP="""
sudo yum install -y pandoc
sudo usermod -a -G docker yarn
"""

# Running as yarn
@bmll_scheduled_job(frequency="@weekly", cluster_name="doc-generator", bootstrap=CUSTOM_BOOTSTRAP)
def main(date):
    import bmll2
    docdir=os.getcwd()
    print("docdir = ", docdir)
    # configure custom pandoc env
    with open(os.path.expanduser("~/bin/pandoc"),'w') as f:
        f.write('#!/bin/bash\nPANDOC_DATA_DIR='"$HOME"'/.pandoc/data  '"$HOME"'/local/usr/bin/pandoc --data-dir='"$HOME"'/.pandoc/data  --abbreviations='"$HOME"'/.pandoc/data/abbreviations $*')
    os.system("chmod +x ~/bin/pandoc")
    os.system("cp -r /usr/share/pandoc/ ~/.local/share/)
    os.system("ln -s $PWD/template.tex ~/.local/share/pandoc/data/templates/bmll_template.latex")

    
    # run and build tje documentation
    os.system("python update_docs.py")
    rc=RCloneSyncer(os.path.join(docdir,'render'), "product_team/docs", area="organisation")
    rc.upload()
    