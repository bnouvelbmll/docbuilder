import json 
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import markdown2


# OAUTHLIB_RELAX_TOKEN_SCOPE=1 HOME=~/bmll google-oauthlib-tool --client-secrets ~/bmll/Downloads/client_secret_1053002847428-gofqrei990bkqf72n63ckg3716sobobk.apps.googleusercontent.com.json --scope  "https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/documents openid"

# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/documents',
          'https://www.googleapis.com/auth/drive'
          ]

def service_build():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('docs', 'v1', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    return service, drive_service



from bs4 import BeautifulSoup  # You need to install BeautifulSoup

def apply_styles_to_text(service, document_id, text, start_index):
    requests = []

    # Use BeautifulSoup to parse the HTML
    soup = BeautifulSoup(text, 'html.parser')

    current_index = start_index

    # Iterate through the elements and create requests based on tags
    for element in soup.descendants:
        if element.name == 'strong':
            # Bold text
            requests.append({
                'updateTextStyle': {
                    'range': {
                        'startIndex': current_index,
                        'endIndex': current_index + len(element.text)
                    },
                    'textStyle': {
                        'bold': True
                    },
                    'fields': 'bold'
                }
            })
        elif element.name == 'em':
            # Italic text
            requests.append({
                'updateTextStyle': {
                    'range': {
                        'startIndex': current_index,
                        'endIndex': current_index + len(element.text)
                    },
                    'textStyle': {
                        'italic': True
                    },
                    'fields': 'italic'
                }
            })

        if element.string:
            current_index += len(element.string)

    # Execute the batchUpdate to apply styles
    service.documents().batchUpdate(documentId=document_id, body={'requests': requests}).execute()

def create_table_with_dataframe(service, document_id, dataframe, start_index):
    rows, cols = dataframe.shape
    requests = []

    # Create table request
    requests.append({
        'insertTable': {
            'location': {'index': start_index},
            'rows': rows + 1,  # Adding one row for headers
            'columns': cols
        }
    })

    # Execute the request to create the table
    result = service.documents().batchUpdate(documentId=document_id, body={'requests': requests}).execute()

    # Assuming the table is the last element, get its start index
    # This is a simplification and might need adjustment in a real scenario
    print("O")
    #table_start_index = result['replies'][0]['insertTable']['endIndex'] - 1
    #print(table_start_index)
    # print(result['replies'][0])
    table_start_index = 0# start_index

    # Prepare requests to populate the table
    requests = []
    for col_index, col_name in enumerate(dataframe.columns):
        # Header row
        cell_index = table_start_index + 1 + col_index  # Calculate cell start index
        requests.append({
            'insertText': {
                'location': {'index': cell_index},
                'text': col_name + '\n'  # Insert header text
            }
        })

    for row_index, row in dataframe.iterrows():
        for col_index, item in enumerate(row):
            # Data rows
            cell_index = table_start_index + 1 + (row_index + 1) * cols + col_index  # Calculate cell start index
            requests.append({
                'insertText': {
                    'location': {'index': cell_index},
                    'text': str(item) + '\n'  # Insert data text
                }
            })

    # Execute the batchUpdate to populate the table
    service.documents().batchUpdate(documentId=document_id, body={'requests': requests}).execute()

def  create_table_with_dataframe(service, document_id, table, start_index):
    # 1 : insert a table at the end of the file
    requests = [{
        'insertTable': {
            'location': {'index': start_index},
            'rows': len(table),
            'columns': len(table.columns),
            # 'endOfSegmentLocation': {
            #     'segmentId': ''
            # }
        },
    }
    ]

    service.documents().batchUpdate(documentId=document_id, body={'requests': requests}).execute()

    content = service.documents().get(documentId=document_id, fields='body').execute().get('body').get('content')
    tables = [c for c in content if c.get('table')]
    last_table_start_index = tables[-1]['startIndex']

    # Building requests
    requests_l, index = [], last_table_start_index
    for i_row, row in table.iterrows():
        index += 1
        for i_cell, cell in enumerate(row.to_dict().values()):
            index += 2
            if cell=='' or cell is None:
                cell=' '
            requests_l.append(
                {
                    'insertText': {
                        'location': {
                            'index': index
                        },
                        'text': str(cell)
                    }
                }
            )
    requests_l.reverse()
    result = service.documents().batchUpdate(documentId=document_id, body={'requests': requests_l}).execute()

def create_table_request_from_dataframe_old(dataframe, start_index):
    rows, cols = dataframe.shape
    table_request = {
        'insertTable': {
            'location': {'index': start_index},
            'rows': rows + 1,  # Adding one row for headers
            'columns': cols
        }
    }

    # List to hold each row's requests
    table_rows = []

    # Create header row
    header_cells = []
    for col_name in dataframe.columns:
        header_cells.append({
            'tableCells': [{
                'content': [{
                    'paragraph': {
                        'elements': [{
                            'textRun': {
                                'content': col_name + '\n'
                            }
                        }]
                    }
                }]
            }]
        })
    table_rows.append({'tableCells': header_cells})

    # Create data rows
    for _, row in dataframe.iterrows():
        row_cells = []
        for item in row:
            row_cells.append({
                'tableCells': [{
                    'content': [{
                        'paragraph': {
                            'elements': [{
                                'textRun': {
                                    'content': str(item) + '\n'
                                }
                            }]
                        }
                    }]
                }]
            })
        table_rows.append({'tableCells': row_cells})

    # Add the rows to the table request
    table_request['insertTable']['tableRows'] = table_rows

    return table_request




def replace_placeholder_with_table(service, document_id, placeholder, csv_data):
    # Fetch the document
    document = service.documents().get(documentId=document_id).execute()
    content = document.get('body').get('content')

    # Find the placeholder
    for element in content:
        try:
            elmnt = element['paragraph']['elements'][0]
            text_run = elmnt['textRun']
            if text_run['content'].strip() == placeholder:
                start_index = elmnt['startIndex']
                end_index = elmnt['endIndex']

                # Delete the placeholder text
                requests = [{
                    'deleteContentRange': {
                        'range': {
                            'startIndex': start_index,
                            'endIndex': end_index
                        }
                    }
                }]

                # # Insert table at the placeholder position
                # table_request = {
                #     'insertTable': {
                #         'location': {'index': start_index},
                #         'rows': len(csv_data),
                #         'columns': len(csv_data.columns)
                #     }
                # }
                #table_request=create_table_request_from_dataframe(csv_data, start_index)
                #requests.append(table_request)

                # # Fill the table with CSV data
                # for row_idx, row in csv_data.iterrows():
                #     for col_idx, text in enumerate(row.to_dict().values()):
                #         print(row_idx, col_idx, text)
                #         cell_location = {
                #             'tableCellLocation': {
                #                 'tableStartLocation': {'index': start_index},
                #                 'rowIndex': row_idx,
                #                 'columnIndex': col_idx,
                #             }
                #         }
                #         insert_text_request = {
                #             'insertText': {
                #                 'location': cell_location,
                #                 'text': text
                #             }
                #         }
                #         requests.append(insert_text_request)
                #
                #service.documents().batchUpdate(documentId=document_id, body={'requests': requests}).execute()
                create_table_with_dataframe(service, document_id, csv_data, start_index)
                break
        except KeyError:
            continue



def replace_placeholder_with_markdown(service, document_id, placeholder, markdown_text):
    # Convert Markdown to HTML
    html = markdown2.markdown(markdown_text)

    # Fetch the document
    document = service.documents().get(documentId=document_id).execute()
    content = document.get('body').get('content')

    # Find the placeholder
    for element in content:
        try:
            elmnt = element['paragraph']['elements'][0]
            text_run = element['paragraph']['elements'][0]['textRun']
            if text_run['content'].strip() == placeholder:
                start_index = elmnt['startIndex']
                end_index = elmnt['endIndex']

                # Replace the placeholder with plain text
                requests = [{
                    'deleteContentRange': {
                        'range': {
                            'startIndex': start_index,
                            'endIndex': end_index
                        }
                    }
                }, {
                    'insertText': {
                        'location': {'index': start_index},
                        'text': BeautifulSoup(html, 'html.parser').get_text()
                    }
                }]

                service.documents().batchUpdate(documentId=document_id, body={'requests': requests}).execute()

                # Apply styles to the inserted text
                apply_styles_to_text(service, document_id, html, start_index)

                break
        except KeyError as e:
            print("EXC", e)
            continue

def replace_placeholder_with_markdown_old(service, document_id, placeholder, markdown_text):
    # Convert Markdown to HTML
    html = markdown2.markdown(markdown_text)

    # Fetch the document
    document = service.documents().get(documentId=document_id).execute()
    content = document.get('body').get('content')

    # Find the placeholder
    for element in content:
        try:
            #print(element)
            elmnt = element['paragraph']['elements'][0]
            # print(elmnt)
            text_run = elmnt['textRun']
            # print(text_run['content'])
            if text_run['content'].strip() == placeholder:
                # print(dir(text_run))
                # print(text_run.keys())
                start_index = elmnt['startIndex']
                end_index = elmnt['endIndex']

                # Replace the placeholder with HTML
                requests = [{
                    'deleteContentRange': {
                        'range': {
                            'startIndex': start_index,
                            'endIndex': end_index
                        }
                    }
                }, {
                    'insertText': {
                        'location': {'index': start_index},
                        'text': html
                    }
                }
                ]

                service.documents().batchUpdate(documentId=document_id, body={'requests': requests}).execute()
                break
        except KeyError as e:
            print("EXC",e)
            continue



def main_google_docs(p, csv_data):
    from google_docs_integ import (
        service_build,
        replace_placeholder_with_table,
        replace_placeholder_with_markdown,
        replace_placeholder_with_markdown_old,
    )

    # Build the service
    service, drive_service = service_build()

    # Your Google Docs template ID
    template_id = "1_dE8uBWBJiwro-DnzgHJt5g0SeDyKlyLS9RCr4XNau8"

    # Copy the template document
    copy = (
        drive_service.files()
        .copy(
            fileId=template_id,
            body={
                "name": "BMLL "
                + p["Name"]
                + " (draft "
                + str(pd.Timestamp("now"))
                + ")"
            },
        )
        .execute()
    )
    new_document_id = copy.get("id")

    # Replace placeholder with table
    replace_placeholder_with_table(service, new_document_id, "[SCHEMA_TABLE]", csv_data)

    # Replace placeholder with Markdown
    replace_placeholder_with_markdown_old(
        service, new_document_id, "[PRODUCT_NAME]", p["Name"]
    )
    replace_placeholder_with_markdown_old(
        service,
        new_document_id,
        "[DATE]",
        str(pd.Timestamp("now").date().isoformat()) + ")",
    )
    replace_placeholder_with_markdown(
        service, new_document_id, "[INTRO]", p["DocumentationIntro"]
    )

