import sys
import yaml
from odf import teletype
from odf.opendocument import load
from odf.text import P

def replace_constants(text_file, yaml_file, output_filename):
    # Load the YAML file
    with open(yaml_file, 'r') as f:
        constants = yaml.safe_load(f)

    # Open the text document
    doc = load(text_file)

    # Replace constants in the document
    for paragraph in list(doc.getElementsByType(P)):
        old_text = text = teletype.extractText(paragraph)
        for constant, value in constants.items():
            text = text.replace(f"[{constant}]", str(value))
        if text != old_text:
            new_S = P()
            new_S.setAttribute("stylename",paragraph.getAttribute("stylename"))
            new_S.addText(text)
            paragraph.parentNode.insertBefore(new_S,paragraph)
            paragraph.parentNode.removeChild(paragraph)

    # Save the modified document
    doc.save(output_filename)
    #print(output_filename)

# Example usage
replace_constants(*sys.argv[1:])
