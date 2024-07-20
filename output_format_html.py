def bmll_header_and_footer(p, content, wt=True):
    if wt:
        content="""
<table  style="boder: 0px;">
<thead><tr><td>
    <div class="header-space"> </div>
</td></tr></thead>
<tbody><tr><td>
    <div class="content">\n""" + content + """\n</div>
</td></tr></tbody>
<tfoot><tr><td>
    <div class="footer-space"> </div>
</td></tr></tfoot>
</table>
"""
    return f"""
<script src="https://unpkg.com/pagedjs/dist/paged.polyfill.js"></script>

<section class="frontmatter">
<div style="text-align: right;">
<img src="Pictures/10000201000001270000004ABC8086638F59356A.png"/>
</div>

<p style='font-size:4em;'>{'BMLL Data Feed'}</p>
<img src="Pictures/10000201000008690000004BC47A7217E5B4CCCB.png"/>
<p style='font-size:3em;'>{p["Name"]}</p>
<p>
Date: {str(pd.Timestamp('now').date().isoformat())}
</p>
</section>
<div class="pagebreak"> </div>
<section class="content">
<div>

<div class="c2">

<div class="pheader"> BMLL Data Feed - OPRA Raw Data
    <img src="Pictures/10000201000008690000004BC47A7217E5B4CCCB.png"/>
</div>

<div class="pfooter">
<table style="boder: 0px;">
<tr>
<td class='.wt'>T:</td><td> +44 (0)20 3828 9000</td>
<td class='.wt'>E:</td><td> info@bmlltech.com</td>
<td class='.wt'>W:</td><td> www.bmlltech.com</td>
<td><div style="font-size:0.6em">Copyright © 2023 BMLL Technologies. All rights reserved.<div></td></table>
<hr/>
<img style= "" src="Pictures/10000201000001270000004ABC8086638F59356A.png" height=60/>

 - <div id="pageFooter">Page </div>
</div>
</div>


"""+content+"""

</div>
</section>
    """

CSS="""


@import url('https://fonts.cdnfonts.com/css/exo-4');

.pheader, .header-space,
.pfooter, .footer-space {
height: 200px;
display: none;
}
.pheader {
position: fixed;
top: 0;
}
.pfooter {
position: fixed;
bottom: 0;
}

thead .header{
background-color: rgb(224,224,224);
}

.even {
background-color: rgb(240,240,240);
color: rgb(48,48,48);
}

.odd {
color: rgb(48,48,48);
}

.wt {
color: #4040ff;
}

#content {
    display: table;
}

#pageFooter {
    display: table-footer-group;
}

#pageFooter:after {
    content: counter(page);
    counter-increment: page;
}


    h1 {
        counter-reset: h2counter;
    }
    h1:before {
        counter-increment: h1counter;
        content: counter(h1counter) " : ";

    }
    h2 {
        counter-reset: h3counter;
    }
    h2:before {
        content: counter(h1counter) "." counter(h2counter) " : ";
        counter-increment: h2counter;
    }
    h3:before {
        content: counter(h1counter) "." counter(h2counter)"." counter(h3counter) " : ";
        counter-increment: h3counter;
    }

@media print {
    .pagebreak {
        height:1px;
        background-color: rgb(224,224,224);
    }
}
@media print {
    .pagebreak {
        clear: both;
        page-break-after: always;
    }
    .frontmatter {
  page: frontmatterpage;
}

.content {
  page: contentpage;
}

    .pheader, .header-space,
    table.report { page-break-after:auto }
    table.report tr    { page-break-inside:avoid; page-break-after:auto }
    table.report td    { page-break-inside:avoid; page-break-after:auto }
    table.report thead { display:table-header-group }
    table.report tfoot { display:table-footer-group }

.pfooter, .footer-space {
    height: 200px;
    display: block;
}

@page contentpage {
  size: A4;
}

@page frontmatterpage {
  size: A4;

.pheader {
position: fixed;
top: 0;
display:none;
}
.pfooter {
display: table-footer-group;
position: fixed;
bottom: 0;
display:none;
}
}
}
.frontmatter {

}

.pagejs_page_content .content {

.pheader {
position: fixed;
top: 0;
}
.pfooter {
display: table-footer-group;
position: fixed;
bottom: 0;
}
}
}

table {
  border: 1px solid black;
  width: 100% !important;
  border-collapse: collapse;
  border-spacing: 0px;
}

table td, table th {
    border: 1px solid rgb(16,16,16);
}

.pfooter table {
  border: 0px solid black;
  width: 100% !important;
  border-collapse: collapse;
}

.pfooter table td, table th {
    border: 0px solid rgb(16,16,16);
}


.outert {
    border: 0px ;
}

body {
    counter-reset: h1counter page;
    font-size: 11pt;
    font-family: 'Exo', sans-serif;
}

#c2 {
    display: table;
}

"""



from docx import Document

def docx_style_to_css(docx_file):
    # Open the DOCX file
    doc = Document(docx_file)
    css_styles = []

    # Define the styles you're interested in
    # 'Heading 1' to 'Heading 6' for headers, 'Normal' for classic text
    styles_of_interest = {'Heading 1':"h1",
                          'Heading 2':"h2",
                          'Heading 3':"h3",
                          'Heading 4':"h4",
                          'Heading 5':"h5",
                          'Heading 6':"h6",
                          'Normal':None
                          }

    # Iterate through the styles of interest
    for style_name in styles_of_interest.keys():
        hs=styles_of_interest[style_name]
        style = doc.styles[style_name]
        css = f"/* {style_name} */\n"

        if hs:
            css+=hs + " {\n"
        # Weight and slantness are part of font style, size is part of font size, color is part of font color
        if hasattr(style.font, 'bold') and style.font.bold:
            css += "font-weight: bold;\n"
        if hasattr(style.font, 'italic') and style.font.italic:
            css += "font-style: italic;\n"
        if hasattr(style.font, 'size') and style.font.size:
            # Convert font size from TWIPs to points (1 point = 20 TWIPs)
            size_pt = style.font.size / 100_000
            css += f"font-size: {size_pt}em;\n"
        if hasattr(style.font, 'color') and style.font.color and style.font.color.rgb:
            css += f"color: #{style.font.color.rgb};\n"
        if hs:
            css+="}\n"
        # Add the CSS style to the list
        css_styles.append(css)

    return "\n".join(css_styles)