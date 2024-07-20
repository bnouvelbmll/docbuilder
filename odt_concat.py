import sys
from odf.opendocument import OpenDocumentText, load
import odf.text

def merge_styles(doc1, doc2):
    for style in doc2.styles.childNodes:
        #if style not in doc1.styles.childNodes:
        doc1.styles.appendChild(style)


def concat_odt_files(file1, file2, output_file):
    doc1 = load(file1)
    doc2 = load(file2)

    # Merge styles
    merge_styles(doc1, doc2)

    # Concatenate content
    doc1_body = doc1.text


    doc2_body=doc2.body.childNodes[1].childNodes
    print(doc2_body)
    #doc2_body = doc2.text.childNodes
    #print(dir(doc2.text))
    #print(doc2.text.childNodes)
    for paragraph in doc2_body:
        if paragraph.hasChildNodes():
            doc1_body.addElement(paragraph)
        else:
            print(repr(paragraph))

    doc1.save(output_file)


# Example usage
concat_odt_files(*sys.argv[1:])
