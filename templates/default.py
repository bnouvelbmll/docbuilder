import re
import textwrap
import pandas as pd
from docbuilder_utils import format_table, get_grist_table, solve_coverage_table


schema_type_table = get_grist_table('Schema_types')[["Type_Name","Description","Sample"]] #.iloc[:0]
tsas = get_grist_table('TechnologySubassets')

EXTRA_BLURB="""
# Data Quality

## General policies

To ensure best quality, BMLL performs numerous checks on all the files it produces.

- Files generation processes are monitored and errors are logged.
- All files are checked against schema. 
- Consistency checks are regularly runned on per dataset basis to ensure high-quality data.
  Feed back on data-quality is welcome and is taken in account when working building next version of datasets.
- Row counts and anomaly.

- Our team will provide updates on the date of our data processing pipeline.
  Consult  https://bmll.statuspage.io/ if you have questions about current or previous issues.

## Known issues

BMLL will do best efforts to fix the data when issues are reported. Depending on the complexity
of the issue, and the nature of the fix, some data issues may not be fixed - or may take 
require significant time to fix.

BMLL coverage is also limited by the existence of the data from upstream sources.

Dates with known errors are inventoried by BMLL. 

This inventory is regularly updtated.
Please contact support@bmlltech.com if you have any questions,
if you have questions about known issues on this data.



## Reporting new data issues

If you have identified a new issue, please report it to our team at support@bmlltech.com.
"""

def snake_to_human(s):
    return ' '.join(word.capitalize() for word in s.lower().replace('_', ' ').split())

def generate_documentation_for_table(p, table):
    column_width={"ColumnName": 28, "ColumnType": 14, "Description": 40}
    # math modes in table not supported yet
    table = table.assign(ColumnName=lambda x:x['ColumnName'].apply(lambda s:f'`{s}`'))
    if len(table)>24 and len(table["Subtable"].unique())>1:
        table_schema="This table is large, for clarity, we split the columns in different groups.\n\n"
        for gn, g in table.groupby("Subtable"):
            table_schema+=(f"### {snake_to_human(re.match('[0-9]+-(.*)',gn).group(1))} Columns\n\n")
            table_schema+=(format_table(g[["ColumnName","ColumnType","Description"]],  column_width=column_width))
            table_schema+="\n\n"
        
    else:        
        table_schema = format_table(table[["ColumnName","ColumnType","Description"]],  column_width=column_width)

    #table_schema=":::: landscape\n\n"+table_schema+"\n\n::::"
     
    txt=f"""
# Introduction

{p["DocumentationIntro"]}

# Data Format

## Row 

A row is uniquely identified by the combination of its primary key : {', '.join(['`'+k.strip().strip('`').strip()+'`' for k in p["PrimaryKeys"].split(',') ])}.

{p["Row_Definition"]}

## Table Schema


{"Column names are generally camel cased." if p["PrimaryColumnStandard"]=='CamelCase' else "Column names are generally snake cased." }

{
    table_schema
}

## Data Types

{
    format_table(schema_type_table)
}

"""
    txt=textwrap.dedent(txt)
    if len(table[table["EnumValues"].apply(len)>0]):
        txt+=textwrap.dedent("""## Values used in enumerations""")
    for r,v in table[table["EnumValues"].apply(len)>0].iterrows():    
        ev = pd.DataFrame(
            [ (ccv.split(":")[0], ":".join(ccv.split(":")[1:]))  for ccv in v["EnumValues"].split("\n") if len(ccv.strip()) and ":" in ccv],
            columns=["Name", "Description"]
            )
        txt+=textwrap.dedent(
	 f"""

### {v["ColumnName"].strip('`')}

{v["Description"]}

This column can take one of the following values:

{ format_table(ev) }
	 """
	)

    tsa=p["TechnologySubAssets"]
    if len(tsa) is not False:
        txt += textwrap.dedent("""
                                
                                # Technical aspects of the implementation                                

                                """)
        for ct in tsa:
            try:
                ctt=tsas.query("SubassetPublicName==@ct").iloc[0]
                txt+=f"## {ct}\n\n"
                txt+=ctt["PublicDescription"]
                txt+="\n\n"
            except Exception as e:
                print("Could not find {ct}: {e}")
                

        

    ct=solve_coverage_table(p["CoverageTable"])
    if ct is not False:
        txt += textwrap.dedent("""
                                
                                # Coverage
                                
                                {table}

                                """).format(table=format_table(ct))
        
    ct=solve_coverage_table(p["LandingTimeTable"])
    if ct is not False:
        txt += textwrap.dedent("""
                                
                                # Landing Times
                                
                                ::: vfix

                                {table}
                                
                                :::

                                """).format(table=format_table(ct))

    txt+=textwrap.dedent("""
    # Delivery Mechanisms
                             
    """)


    if "API" in p["DeliveryMechanism"]:
        txt+=textwrap.dedent("""
    ## BMLL DataFeed API
                             
    BMLL provides an API to access this data. Please consult https://data.bmlltech.com/ for more information about the API.
    """
    )    
        
    if "Lab" in p["DeliveryMechanism"]:
        txt+=textwrap.dedent("""
    ## BMLL Data Lab
                             
    This data is directly available in the BMLL Data Lab.                             
    """
    )

    if "Snowflake" in p["DeliveryMechanism"]:
        txt+=textwrap.dedent("""
    ## BMLL Data on Snowflake 
                             
    This data is available via Snowflake.
    
    Please note that the column names used in the Snowflake table may not the same as the ones in the BMLL data model.
    
    The sample dataset is accessible on [Snowflake marketplace](https://app.snowflake.com/marketplace/providers/GZTSZC7NYY4/BMLL%20Technologies?categorySecondary=%5B%227%22%5D&originTab=providers).
    """
    )
                
    if True or "Revolate" in p["DeliveryMechanism"]:
        txt+=textwrap.dedent("""
    ## SFTP, custom deliveries format and samples

    There are many alternative possible formats that we can deliver, if you have custom needs, or would like
    to confirm with solution is the most suited for your needs, please contact our sales team:
    We will help you to get access BMLL data in the format most suited with your needs.
    Contact sales@bmlltech.com for more information.
    
                             
    """
    )        


    if "S3" in p["DeliveryMechanism"]:
        txt+=textwrap.dedent("""
    ## BMLL S3 Partner Connenections
                             
    The data is accessible via shared S3 buckets to BMLL partners.
    """
        )
    txt+=EXTRA_BLURB

    if "DocumentationNotes" in p and p["DocumentationNotes"]:
        txt+=textwrap.dedent("""
        # Notes
        """)

        txt+=p["DocumentationNotes"]

    if "ExtraDocs" in p and p["ExtraDocs"]:
        txt+=p["ExtraDocs"]
     
    
    return txt
