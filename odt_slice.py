import sys
from odf.opendocument import OpenDocumentText
from odf.opendocument import load
import odf.text

# Get filename and page range from command line arguments
filename = sys.argv[1]
end_page=start_page = int(sys.argv[2])
if len(sys.argv)>3:
    end_page = int(sys.argv[3])

# Open the ODT document
#doc = OpenDocumentText()
doc = load(filename)

# Get the text content
print(dir(doc.text))
content = doc.text.getElementsByType(odf.text.P)

# Filter content by page range
page_count = 1
filtered_content = []
for paragraph in content:
    if page_count >= start_page and page_count <= end_page:
        filtered_content.append(paragraph)

    if paragraph.getAttribute('textwindow:anchortype') == 'page':
        page_count += 1

# Create a new document with the filtered content
new_doc = OpenDocumentText()
for paragraph in filtered_content:
    new_doc.text.addElement(paragraph)

# Save the new document
new_filename = f"output_{start_page}-{end_page}.odt"
new_doc.save(new_filename)
