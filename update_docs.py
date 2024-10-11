import tempfile
import shutil
import subprocess

import os
import sys
import time
import pandas as pd


import yaml


from docbuilder_utils import get_grist_table, wrap_links_in_markdown

from templates.default import generate_documentation_for_table


def generate_md(p, table, temp_dir):
    NL = "\n"
    txt = wrap_links_in_markdown(generate_documentation_for_table(p, table))
    doc_md_path = os.path.join(temp_dir, "doc.md")
    open(doc_md_path, "w").write(txt)
    return doc_md_path


def generate_odt_pdf_and_html_from_odf(p, temp_dir, doc_md_path, reference_odt):

    os.system(
        f"pandoc {doc_md_path} --from=markdown+grid_tables+footnotes --reference-doc='{reference_odt}' -o {os.path.join(temp_dir, 'doc.odt')}"
    )
    subprocess.Popen(
        f"libreoffice --convert-to pdf {os.path.join(temp_dir, 'doc.odt')}",
        cwd=temp_dir,
        shell=True,
    ).communicate()
    constants = {
        "PRODUCT_NAME": p["Name"],
        "DATE": pd.Timestamp.now().strftime("%Y-%m-%d"),
    }
    yaml.dump(
        constants,
        open(os.path.join(temp_dir, "doc.yaml"), "w"),
        default_flow_style=False,
    )
    os.system(
        f"python odt_subst.py {reference_odt} {os.path.join(temp_dir, 'doc.yaml')} {os.path.join(temp_dir, 'page1.odt')}"
    )
    os.system(
        f"python odt_concat.py {os.path.join(temp_dir, 'page1.odt')} {os.path.join(temp_dir, 'doc.odt')} {os.path.join(temp_dir, 'out.odt')}"
    )
    subprocess.Popen(
        f"libreoffice --convert-to pdf {os.path.join(temp_dir, 'out.odt')}",
        cwd=temp_dir,
        shell=True,
    ).communicate()
    subprocess.Popen(
        f"libreoffice --convert-to \"html:XHTML Writer File:UTF8\" --convert-images-to jpg {os.path.join(temp_dir, 'out.html')}",
        cwd=temp_dir,
        shell=True,
    ).communicate()


def generate_pdf_html_from_latex(p, temp_dir, doc_md_path, reference_tex, output_filename, quiet=True):
    # Generate LaTeX template
    print(doc_md_path)
    os.makedirs(f"{temp_dir}/.local/share/pandoc/templates", exist_ok=True)
    shutil.copy(
        reference_tex, f"{temp_dir}/.local/share/pandoc/templates/bmll_template.latex"
    )

    shutil.copy(
        os.path.join(os.path.dirname(__file__), "latex-tabularx.lua"),
        f"{temp_dir}/latex-tabularx.lua",
    )

    if not os.path.exists(f"{temp_dir}/Pictures"):
        shutil.copytree(
            os.path.join(os.path.dirname(__file__), "Pictures"),
            os.path.join(temp_dir, "Pictures"),
            dirs_exist_ok=True,
        )

    txt = open(doc_md_path).read()
    constants = {
        "title": p["Name"],
        # "author": "BMLL",
        "date": pd.Timestamp.now().strftime("%Y-%m-%d"),
        "titlepage": True,
        "titlepage-color": "ffffff",
        "titlepage-text-color": "4040ff",
        "table-use-row-colors": True,
        "titlepage-logo": "./Pictures/100002010000024F000000942B5A1837872C8AB1.png",
        "logo": "./Pictures/100002010000024F000000942B5A1837872C8AB1.png",
        "toc": True
    }

    HEADERS = f"""---\n{yaml.dump(constants)}\n..."""

    open(doc_md_path, "w").write(HEADERS + txt)
    os.system(
        f"HOME={temp_dir} pandoc {os.path.join(temp_dir, 'doc.md')}  --lua-filter=latex-tabularx.lua --from=markdown+grid_tables+footnotes+fenced_divs+bracketed_spans  --template bmll_template -o {os.path.join(temp_dir, 'doc.tex')}"
    )

    # os.system(f"cat  {os.path.join(temp_dir, 'doc.tex')}")
    # Render LaTeX to PDF using Docker
    shutil.copy(os.path.join(temp_dir, "doc.tex"), f"{output_filename}.tex")
    if os.environ.get("HOME")!='/home/bmll':
        docker_cmd = f"docker run --rm -v {temp_dir}:/workdir  texlive/texlive:latest /bin/sh -c 'pdflatex /workdir/doc.tex;pdflatex /workdir/doc.tex' 2>&1 | tee {temp_dir}/doc.err"
        if quiet:
            docker_cmd += " > /dev/null"
        os.system(docker_cmd)
    else:
        cmd =  f"cd {temp_dir};(pdflatex doc.tex;pdflatex doc.tex) 2>&1 | tee {temp_dir}/doc.err"
        if quiet:
            cmd += " > /dev/null"

        os.system(cmd)
        
    # Copy the generated PDF to the desired location
    shutil.copy(os.path.join(temp_dir, "doc.pdf"), f"{output_filename}.pdf")
    shutil.copy(os.path.join(temp_dir, "doc.log"), f"{output_filename}.log")
    shutil.copy(os.path.join(temp_dir, "doc.err"), f"{output_filename}.err")


def generate_direct_html(p, temp_dir, doc_md_path, reference_docx):
    import output_format_html

    ncss = output_format_html.docx_style_to_css(reference_docx)
    open(os.path.join(temp_dir, "doc2.css"), "w").write(output_format_html.CSS + ncss)
    open(os.path.join(temp_dir, "doc2.md"), "w").write(
        output_format_html.bmll_header_and_footer(p, txt)
    )
    os.system(
        f"pandoc {os.path.join(temp_dir, 'doc2.md')} --css {os.path.join(temp_dir, 'doc2.css')} --self-contained --from=markdown+grid_tables+footnotes -o {os.path.join(temp_dir, 'doc.html')}"
    )


def main_md(p, table, output_filename, output_method="latex"):
    with tempfile.TemporaryDirectory() as temp_dir:
        doc_md_path = generate_md(p, table, temp_dir)
        shutil.copy(os.path.join(temp_dir, "doc.md"), f"{output_filename}.md")

        if output_method == "odt":
            reference_odt = os.path.join(os.path.dirname(__file__), "ref.odt")
            generate_odt_pdf_and_html_from_odf(p, temp_dir, doc_md_path, reference_odt)
            shutil.copy(os.path.join(temp_dir, "out.odt"), f"{output_filename}.odt")
            shutil.copy(os.path.join(temp_dir, "doc.odt"), f"{output_filename}-s.odt")
            shutil.copy(
                os.path.join(temp_dir, "page1.odt"), f"{output_filename}-p1.odt"
            )
            shutil.copy(os.path.join(temp_dir, "doc.pdf"), f"{output_filename}-m.pdf")
            shutil.copy(os.path.join(temp_dir, "out.pdf"), f"{output_filename}.pdf")
            shutil.copy(os.path.join(temp_dir, "out.html"), f"{output_filename}.html")

        if output_method == "latex":
            generate_pdf_html_from_latex(
                p,
                temp_dir,
                doc_md_path,
                os.path.join(os.path.dirname(__file__), "template.tex"),
                output_filename
            )

        if output_method == "html":
            reference_docx = "/home/bnouvel/bmll/Downloads/Ref - BMLL Doc Template.docx"
            generate_direct_html(p, temp_dir, doc_md_path, reference_docx)
            shutil.copy(os.path.join(temp_dir, "out.html"), f"{output_filename}.html")


if __name__ == "__main__":
    products = get_grist_table("Data_products")
    docfilter = (sys.argv[1] if len(sys.argv)>1 else "")
    for pi, p in products.iterrows():
        if docfilter not in p["Name"].lower():
            continue
        try:
            res = get_grist_table("Schema", query={"Tables": pi})
            print(res[["ColumnName", "ColumnType"]])
            tname = "".join(
                c
                for c in p["Name"].lower().replace(" ", "_").replace("_", "-")
                if c.isalnum() or c == "-"
            )
            print("TNAME", tname)
            if tname:
                res.to_csv("schema.csv")
                pkeys=p["PrimaryKeys"]
                pakeys=p["PartitionnedBy"]
                # pkeys = [s.strip() for s in p["PrimaryKeys"].split(",")]

                res["NColumnName"] = res[("ColumnNameCamelCase" if p["PrimaryColumnStandard"]=="CamelCase" else "ColumnNameSnakeCase")].fillna(res["ColumnName"])
                c2n = res.set_index("ColumnName")["NColumnName"].copy()
                res["ColumnName"] = res["NColumnName"]
                res = res.drop(columns=["NColumnName"])

                pkeys = [c2n.get(col,col) for col in pkeys]
                pakeys = [c2n.get(col,col) for col in pakeys]

                p["PrimaryKeys"] = pkeys
                p["PartitionnedBy"] = pakeys

                for k in pkeys:
                    if k not in res["ColumnName"].values:
                        print (res["ColumnName"].values)
                        print((f"Primary key {k} not found in schema for product "+p["Name"]))
                        time.sleep(10)
                        #raise Exception(f"Primary key {k} not found in schema")

                res=res.assign(IsNotPartitionKey=lambda x:~x["ColumnName"] .isin(pakeys))
                res=res.assign(IsNotPrimaryKey=lambda x:~x["ColumnName"] .isin(pkeys))
                print(res[["ColumnName", "ColumnType"]])
                res = res.assign(Subtable=lambda x:x["Subtable"].fillna("999-Other")).sort_values(["IsNotPartitionKey", "IsNotPrimaryKey","Subtable", "ColumnName"]).query("~Deprecated")[
                    [
                        "ColumnName",
                        "ColumnType",
                        "PrimaryKey",
                        "Optional",
                        "Description",
                        "EnumValues",
                        "Subtable",
                    ]
                ]
                res["ColumnType"] = (
                    res["ColumnType"].astype(str)
                    + res["PrimaryKey"].map({True: " (pk)", False: ""})
                    + res["Optional"].map({True: " (opt)", False: ""})
                )
                res = res.drop(["PrimaryKey", "Optional"], axis=1)

                if not os.path.exists("render/" + tname):
                    os.makedirs("render/" + tname)
                main_md(p, res, "render/" + tname + "/" + tname)
        except Exception as e:
            print(e)
            raise