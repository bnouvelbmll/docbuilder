import re
import textwrap
import pandas as pd
from docbuilder_utils import format_table, get_grist_table, solve_coverage_table


schema_type_table = get_grist_table("Schema_types")[
    ["Type_Name", "Description", "Sample"]
]  # .iloc[:0]

print(schema_type_table)

tsas = get_grist_table("TechnologySubassets")
monitoring = get_grist_table("MonitoringMetrics")
assertions = get_grist_table("Assertions")
specifications = get_grist_table("Specifications")


INTERNAL_SPECS = True

EXTRA_BLURB = """
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
    return " ".join(word.capitalize() for word in s.lower().replace("_", " ").split())


def generate_documentation_for_table(p, table):
    column_width = {"ColumnName": 28, "ColumnType": 14, "Description": 40}
    # math modes in table not supported yet
    table=table.copy()
    product_name=p["Name"]
    pmonitoring = monitoring.query("Dataset == @product_name")
    passertions = assertions.query("Dataset == @product_name")
    pspecifications = specifications.query("Dataset == @product_name")
    footnotes=""

    if INTERNAL_SPECS:
        ndesc= []
        for i in range(len(table)):
            if table.iloc[i]["Notes"]:
                # ndesc.append(table.iloc[i]["Description"]+f"""[NOTE]{{.pill}} [^col{table.iloc[i]["ColumnName"]}]""")
                # footnotes+=f"""\n[^col{table.iloc[i]["ColumnName"]}]: """+table.iloc[i]["Notes"].replace("\n", " ")   

                footnote=f"""\n[^col{table.iloc[i]["ColumnName"]}]: """+table.iloc[i]["Notes"].replace("\n", " ")   
                ndesc.append(table.iloc[i]["Description"]+f"""[NOTE]{{.pill}} [{footnote}]{{.xfinternalnote}}""")

            else:
                ndesc.append(table.iloc[i]["Description"])
        table["Description"]=pd.Series(ndesc, index=table.index)


    reserved_table = table.assign(
        ColumnName=lambda x: x["ColumnName"].apply(lambda s: f"`{s}`")
    ).query("Reserved")
    table = table.assign(
        ColumnName=lambda x: x["ColumnName"].apply(lambda s: f"`{s}`")
    ).query("~Reserved")

    todrop=[]
    for c in table.columns:
        if (table[c].astype(str).map(len)==0).all():
            todrop.append(c)
    if len(todrop):
        table=table.drop(columns=c)

    if len(table) > 24 and len(table["Subtable"].unique()) > 1:
        table_schema = "This table is large, for clarity, we split the columns in different groups.\n\n"
        for gn, g in table.groupby("Subtable"):
            try:
                table_schema += f"### {snake_to_human(re.match('[0-9]+-(.*)',gn).group(1))} Columns\n\n"
            except AttributeError:
                if gn:
                    table_schema += f"### {gn} Columns\n\n"
                else:
                    table_schema += f"### Other Columns\n\n"
            table_schema += format_table(
                g[["ColumnName", "ColumnType", "Description"]],
                column_width=column_width,
            )
            table_schema += "\n\n"

    else:
        table_schema = format_table(
            table[["ColumnName", "ColumnType", "Description"]],
            column_width=column_width,
        )

    reserved_table_schema = ""
    if INTERNAL_SPECS:
        if reserved_table is not None and not len(reserved_table):
            reserved_table_schema = """### Reserved fields\n\n"""
            reserved_table_schema += """::::internaldocs\n\n"""
            reserved_table_schema += format_table(
                reserved_table[["ColumnName", "ColumnType", "Description"]],
                column_width=column_width,
            )
            reserved_table_schema += "\n\n::::\n"
    

    # table_schema=":::: landscape\n\n"+table_schema+"\n\n::::"

    txt = f"""
# Introduction

{p["DocumentationIntro"]}

# Data Format

## Rows and Data Partitions 

"""
    if p["PartitionnedBy"]:
        txt += f"""
The data is partitioned by {', '.join(['`'+k.strip().strip('`').strip()+'`' for k in p["PartitionnedBy"] ])}. Depending on the technology that you are using to access the data, you 
will may need to specify which partition you want to access. If you specify a partition to use the columns that are explicitely specified won't be returned in the schema.
"""

    txt += f"""

A row is uniquely identified by the combination of its primary key : {', '.join(['`'+k.strip().strip('`').strip()+'`' for k in (p["PartitionnedBy"]+p["PrimaryKeys"]) ])}.

{p["Row_Definition"]}

## Table Schema


{"Column names are generally camel cased." if p["PrimaryColumnStandard"]=='CamelCase' else "Column names are generally snake cased." }

{
    table_schema
}



{
    reserved_table_schema
}



## Data Types

{
    format_table(schema_type_table)
}

"""
    txt = textwrap.dedent(txt)
    if len(table[table["EnumValues"].apply(len) > 0]):
        txt += textwrap.dedent("""## Values used in enumerations""")
    for r, v in table[table["EnumValues"].apply(len) > 0].iterrows():
        ev = pd.DataFrame(
            [
                (ccv.split(":")[0], ":".join(ccv.split(":")[1:]))
                for ccv in v["EnumValues"].split("\n")
                if len(ccv.strip()) and ":" in ccv
            ],
            columns=["Name", "Description"],
        )
        txt += textwrap.dedent(
            f"""

### {v["ColumnName"].strip('`')}

{v["Description"]}

This column can take one of the following values:

{ format_table(ev) }
	 """
        )

    tsa = p["TechnologySubAssets"]
    if tsa is not None and len(tsa):
        txt += textwrap.dedent(
            """
                                
                                # Technical aspects of the implementation                                

                                """
        )
        if not isinstance(tsa, (list, tuple)):
            tsa = [tsa]
        for ct in tsa:
            try:
                ctt = tsas.query("SubassetPublicName==@ct").iloc[0]
                txt += f"## {ct}\n\n"
                txt += ctt["PublicDescription"]
                txt += "\n\n"
            except Exception as e:
                print(f"Could not find {ct}: {e}")

    ct = solve_coverage_table(p, "CoverageTable")
    if ct is not False:
        txt += textwrap.dedent(
            """
                                
                               # Coverage
                                
                               ::: vfix

                               {table}
                               
                               :::

                                """
        ).format(table=format_table(ct))

    ct = solve_coverage_table(p, "LandingTimeTable")
    if ct is not False:
        txt += textwrap.dedent(
            """
                                
                                # Landing Times
                                
                                ::: vfix

                                {table}
                                
                                :::

                                """
        ).format(table=format_table(ct))

    txt += textwrap.dedent(
        """
    # Delivery Mechanisms
                             
    """
    )

    if "API" in p["DeliveryMechanism"]:
        txt += textwrap.dedent(
            """
    ## BMLL DataFeed API
                             
    BMLL provides an API to access this data. Please consult https://data.bmlltech.com/ for more information about the API.
    """
        )

    if "Lab" in p["DeliveryMechanism"]:
        txt += textwrap.dedent(
            """
    ## BMLL Data Lab
                             
    This data is directly available in the BMLL Data Lab.                             
    """
        )

    if "Snowflake" in p["DeliveryMechanism"]:
        txt += textwrap.dedent(
            """
    ## BMLL Data on Snowflake 
                             
    This data is available via Snowflake.
    
    Please note that the column names used in the Snowflake table may not the same as the ones in the BMLL data model.
    
    The sample dataset is accessible on [Snowflake marketplace](https://app.snowflake.com/marketplace/providers/GZTSZC7NYY4/BMLL%20Technologies?categorySecondary=%5B%227%22%5D&originTab=providers).
    """
        )

    if True or "Revolate" in p["DeliveryMechanism"]:
        txt += textwrap.dedent(
            """
    ## Custom deliveries format and samples

    There are many mechanisms through which that we can deliver data, if you have custom needs, or would like
    to confirm with solution is the most suited for your needs, please contact our sales team.
    We will help you to get access BMLL data in the format most suited with your needs.
    Contact sales@bmlltech.com for more information.
    
                             
    """
        )

    if "S3" in p["DeliveryMechanism"]:
        txt += textwrap.dedent(
            """

    ## BMLL S3 Partner Connenections
                             
    The data is accessible via shared S3 buckets to BMLL partners.

    """
        )
    txt += EXTRA_BLURB
    if INTERNAL_SPECS and passertions is not None and len(passertions):
        txt += textwrap.dedent(
            """

    ::: landscape

    # Specification

    :::: internaldocs
    
    The following specifications has been set. The following table is internal.
     
    ::::

    """
        )
        txt += format_table(pspecifications[["Case","Specification","Handling"]])

        txt += textwrap.dedent("""

        :::
                               
        """
        )


    if pmonitoring is not None and len(pmonitoring):
        txt += textwrap.dedent(
            """
            
    # Monitoring

    ::: internaldocs

    The following monitoring is available for this data.

    """
    )
        txt+=format_table(pmonitoring[["MetricName","Query","GroupBy"]])

        txt += textwrap.dedent("""

        :::
                               
        """
        )

    if INTERNAL_SPECS and passertions is not None and len(passertions):
        txt += textwrap.dedent(
            """
    # Data Quality Assertions
    
    The following assertions are available for this data.

    ::: internaldocs

    """
        )
        txt += format_table(passertions.query("~Disabled")[["MetricName","Implies","Conditions","GroupBy"]])

        txt += textwrap.dedent("""

        :::
                               
        """
        )

    if INTERNAL_SPECS and p["InternalNotes"]:
        txt += textwrap.dedent(
            """
        # Internal Notes

        ::: internaldocs

        """
        )
        txt += p["InternalNotes"]
        txt += "\n:::\n\n"

    if "DocumentationNotes" in p and p["DocumentationNotes"]:
        txt += textwrap.dedent(
            """
        # Notes
        """
        )

        txt += p["DocumentationNotes"]

    if "ExtraDocs" in p and p["ExtraDocs"]:
        txt += p["ExtraDocs"]

    txt+="\n"
    txt+=footnotes
    return txt
