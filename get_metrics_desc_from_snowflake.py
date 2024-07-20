
import pandas as pd
import functools
import os


from docbuilder_utils import get_grist_table, update_grist_table, get_grist_docid, snowflake_connection

schema_type_table = get_grist_table('Schema_types') # [["Type_Name","Description","Sample"]]

@functools.lru_cache(10)
def get_st(k):
    return int(schema_type_table[schema_type_table['Type_Name'] == k].index[0])

if __name__ == "__main__":
    con = snowflake_connection()

    with con.cursor() as cur:
        columns = (
            cur.execute(
                """
            SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE, "COMMENT" FROM INFORMATION_SCHEMA.COLUMNS WHERE (TABLE_SCHEMA='PUBLIC' AND TABLE_NAME IN (
                'DAILY_ENHANCED_BARS',
                'DAILY_VENUE_QUALITY',
                'DAILY_VENUE_STATISTICS'
                )
            )
            """
            )
        )
        columns=(columns.fetch_pandas_all()
            .rename(
                columns={
                    "TABLE_NAME": "Subtable",
                    "DATA_TYPE": "ColumnType",
                    "IS_NULLABLE": "Optional",
                    "COLUMN_NAME": "ColumnName",
                    "COMMENT": "Description"
                }
            )
            .assign(Notes="Imported from Snowflake")
        )

        columns["Optional"] = columns["Optional"].map(lambda s: s.lower() == "yes")
        
        columns = columns.query('ColumnType!="TEXT"')
        columns=columns.assign(Subtable=lambda x: "800-"+x['Subtable'])
        columns["ColumnType"] = columns["ColumnType"].map({
            'INTEGER': get_st('integer'),
            'FLOAT': get_st('double'),
            'TEXT': get_st('varchar (utf8)'),
            'DATE': get_st('date'),
            'TIMESTAMP_NTZ': get_st('timestamp[ns]'),
        })

        print(columns)
        #print(schema_type_table)
        

        update_grist_table(
            tableid="Schema",
            dataframe=columns,
            key_columns=["ColumnName", "Subtable"],
            docid = get_grist_docid("ProdSchemaMaster")
        )
        
