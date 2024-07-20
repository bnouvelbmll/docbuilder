import sys
import odf.opendocument
from odf.opendocument import load


def show_odt_structure(filename):
    doc = load(filename)

    def print_element(element, indent=0):
        print(" " * indent + element.tagName)
        for attr in element.attributes.items( ):
            #print(attr)
            print(" " * (indent + 2) + str(attr[0][1]) + "=" + attr[1])
        for child in element.childNodes:
            if child.nodeType == child.ELEMENT_NODE:
                print_element(child, indent + 2)

    print_element(doc.body)
    print(dir(doc))


show_odt_structure(sys.argv[1])
