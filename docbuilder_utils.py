import functools
import hashlib
import textwrap
import tabulate
import re
import requests
import pandas as pd
import os
import re
import diskcache

import json
from bcdf.utils.dataquery_utils import apply_pandas_filters
from bcdf import settings
from bcdf import secrets

GRIST_CACHE_DIR = ".grist_cache"
grist_cache = diskcache.Cache(
    GRIST_CACHE_DIR, eviction_policy="least-recently-used", cull_limit=0
)

GRIST_URL = "https://bmlltech.getgrist.com/"
APIKEY = os.environ.get("BMLL_GRIST_TOKEN", secrets.get_secret(settings.BMLL_ENV_NAME, "BMLL_GRIST_TOKEN"))
GRIST_DOCID = "n1kWpf68Saqo"
TABLEID = "Constants"

HEADERS = {
    "Authorization": "Bearer " + APIKEY,
    "Content-Type": "application/json",
    "Accept": "application/json",
}


solved_tables_schema = {}
solved_tables_data = {}

GRIST_DATA_DIR = "grist_data"

REQUESTS_CACHE_ENABLED = os.environ.get("REQUESTS_CACHE_DISABLED", "") == ""


def cached_get_query(*args, **kwargs):
    #print(args, kwargs)
    key = hashlib.md5(f"{args}|{kwargs}".encode("utf-8")).hexdigest()
    grist_cache.expire()
    if REQUESTS_CACHE_ENABLED and key in grist_cache:
        return grist_cache[key]
    else:
        res = requests.get(*args, **kwargs).json()
        grist_cache.set(key, res, expire=3600)
        return res


def wrap_links_in_markdown(text):
    # Regular expression to find URLs and email addresses
    url_pattern = r"(\bhttp[s]?://[^\s,]+)"
    email_pattern = r'(\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,3})'
    combined_pattern = f"{url_pattern}|{email_pattern}"

    # Function to replace URL or email with Markdown link
    def replace_with_markdown_link(match):
        matched_text = match.group(0)
        if '@' in matched_text:  # It's an email
            return f"[{matched_text}](mailto:{matched_text})"
        else:  # It's a URL
            return f"[{matched_text}]({matched_text})"

    # Process only non-code and non-link parts
    # This regex matches code blocks, inline code, and existing Markdown links
    exclusion_pattern = r'(```.*?```|`[^`]*`|\[[^\]]*\]\([^\)]*\))'

    # Initialize variables
    last_end = 0
    result = []

    # Iterate over exclusion patterns
    for m in re.finditer(exclusion_pattern, text, flags=re.DOTALL):
        start, end = m.span()
        # Process text before the match for exclusion pattern
        non_excluded_segment = text[last_end:start]
        # Replace URLs and emails in the non-excluded text
        processed_segment = re.sub(
            combined_pattern, replace_with_markdown_link, non_excluded_segment
        )
        result.append(processed_segment)
        # Append the excluded part without change
        result.append(text[start:end])
        last_end = end

    # Process any remaining text after the last match
    if last_end < len(text):
        remaining_segment = text[last_end:]
        processed_segment = re.sub(
            combined_pattern, replace_with_markdown_link, remaining_segment
        )
        result.append(processed_segment)

    return "".join(result)

@functools.lru_cache(64)
def get_grist_docid(docname, workspace="Home", orgname="BMLL"):
    qk = {("BMLL", "Home", "DataFeed"): "o8WDevJ47PX63T5V9ravty"}
    if (orgname, workspace, docname) in qk:
        return qk[(orgname, workspace, docname)]
    # print(docname)
    URL = f"{GRIST_URL}api/orgs"
    res = cached_get_query(URL, headers=HEADERS, verify=False)
    org = [d for d in res if d["name"] == orgname][0]

    URL = f"{GRIST_URL}api/orgs/{org['id']}/workspaces"
    res = cached_get_query(URL, headers=HEADERS, verify=False)
    workspace = [d for d in res if d["name"] == workspace][0]
    docs = workspace["docs"]
    doc = [d for d in docs if d["name"] == docname][0]
    return doc["id"]

import time

@functools.lru_cache(1)
def get_valid_mics():
    import bmll
    rq=bmll.reference.available_markets()
    return set(rq['MIC'].unique())

def enrich_with_iso(table):
    if table is not False:
        if "MIC" in table.columns:
            isotomic=get_mic_iso_map().rename({"FREF_EXCHANGE_CODE": "ISO"}, axis=1)
            table=table.merge(isotomic[["MIC_NONOP_EXCHANGE_CODE","ISO"]], left_on="MIC", right_on="MIC_NONOP_EXCHANGE_CODE", how="left").drop(columns=["MIC_NONOP_EXCHANGE_CODE"])
            table['ISO']=table['ISO'].fillna(table['MIC'].map(isotomic.set_index("MIC_OP_EXCHANGE_CODE")["ISO"].to_dict()))
            table['ISO']=table['ISO'].fillna('-')
        elif "ISO" in table.columns and "MIC" not in table.columns:
            isotomic=get_mic_iso_map().rename({"FREF_EXCHANGE_CODE": "ISO"}, axis=1)
            valid_mics=get_valid_mics()
            table=table.merge(isotomic[["MIC_NONOP_EXCHANGE_CODE","ISO"]].rename({"MIC_NONOP_EXCHANGE_CODE":"MIC"}, axis=1).query("MIC in @valid_mics"),on="ISO", how="left")
            table['MIC']=table['MIC'].fillna(table['ISO'].map(
                isotomic[["MIC_OP_EXCHANGE_CODE","ISO"]].rename({"MIC_OP_EXCHANGE_CODE":"MIC"}, axis=1).query("MIC in @valid_mics").set_index("ISO")["MIC"].to_dict())
                )
            table['MIC']=table['MIC'].fillna('-')
        else:
            print(f"no MIC in columns : {table.columns}" )
            time.sleep(10)
        idxcols = ( ["MIC"] if "MIC" in table.columns else [])+( ["ISO"] if "ISO" in table.columns else [])
        if idxcols:
            table=table.set_index(idxcols).sort_index().reset_index()
    return table

def solve_coverage_table(p, type="CoverageTable", overwrite=True):
    name = p["Name"].replace(" ", "_")
    if os.path.exists(f"data_model/{type}/{name}.csv") and not overwrite:
        return pd.read_csv(f"data_model/{type}/{name}.csv")
    else:
        expr = p[type]
        res= enrich_with_iso(_solve_coverage_table(expr))
        if res is not False:
            res=res[~pd.isna(res[[c for c in res.columns if "date" in c.lower() or "time" in c.lower()]]).all(axis=1) ]
        if not os.path.exists(f"data_model/{type}"):
            os.makedirs(f"data_model/{type}")
        if res is not False:
            res.to_csv(f"data_model/{type}/{name}.csv", index=False)
        return res 


def _solve_coverage_table(expr):
    expr = expr.strip()
    m = re.match(r"(\w+)(\([^\)]*\))?:(.*)", expr)
    if not m:
        return False
    proto, params, expr = m.groups()
    proto=proto.strip()
    params=params.strip()
    expr=expr.strip()
    # print(proto, params, expr)
    # print("--------------")
    # time.sleep(10)

    if proto == "GRIST":
        filters=json.loads(("{}" if "|" not in expr else expr.strip().split("|")[1]))
        res= get_grist_table(expr.strip().split("|")[0], docid=get_grist_docid(params.strip()[1:-1].strip()) , pandas_filters=filters)
        return res
    elif proto == "SNOWFLAKE":
        sf = snowflake_connection(params)
        with sf.cursor() as cur:
            return cur.execute(expr).fetch_pandas_all()
    else:
        return False

@functools.lru_cache(5)
def snowflake_connection(
    database="PROD_DERIVED_DATA_DB",
    schema="PUBLIC",
    warehouse="PROD_DERIVED_DEFAULT_WH",
    role="PROD_SALES_RO_ROLE",
):
    import snowflake
    import snowflake.connector
    connargs = dict(
        user=os.environ.get("SNOWFLAKE_USER", "bertrandnouvel"),
        password=os.environ.get("SNOWFLAKE_PASSWORD"),
        account=os.environ.get("SNOWFLAKE_ACCOUNT", "tib96089"),
        region=os.environ.get("SNOWFLAKE_REGION", "us-east-1"),
        role=role,
        database=database,
        schema=schema,
        warehouse=warehouse,
    )
    return snowflake.connector.connect(**connargs)

@functools.lru_cache(1)
def get_mic_iso_map():
    sf = snowflake_connection("FACTSET_FACTSET_FDS_TH_REF_BMLL", schema='REF_V2',role="DEV_BMLL_RO", warehouse='DEV_BMLL_WH')
    with sf.cursor() as cur:
            return cur.execute("SELECT * FROM MIC_EXCHANGE_MAP").fetch_pandas_all()

PROD_OFFLINE_MODE = os.environ.get(
    "PROD_OFFLINE_MODE"
)  # only takes what's inside the repo


def get_grist_table(
    tableid=TABLEID, filters={}, sort="", docid=GRIST_DOCID, get_cols=True, query=None, pandas_filters=None
):
    query=query or {}
    print("get_grist_table", PROD_OFFLINE_MODE, tableid, get_cols, query)
    # if PROD_OFFLINE_MODE: # FIXME: CARE FUL OF QUERY
    #     return load_from_local_file(docid, tableid)

    internal_cols = []
    if get_cols:
        columns = get_table_schema(docid, tableid)
        internal_cols = get_internal_columns(columns)
        preload_column_types(columns, docid)

    table_data = get_table_data(docid, tableid, filters, sort)
    
    if ('ColumnType' in table_data):
        print(table_data['ColumnType'])

    
    if get_cols:
        # FIXME: Split query from resolve ref
        table_data = process_reference_columns(table_data, columns, query, tableid)
        table_data = process_reflist_columns(table_data, columns, query, tableid)
        table_data = process_choicelist_columns(table_data, columns)
        table_data = process_date_columns(table_data, columns)

    if pandas_filters is not None:
        table_data = apply_pandas_filters(table_data, **pandas_filters)

    print("Internal cols", internal_cols)
    table_data = table_data.drop(internal_cols, axis=1, errors="ignore")
    # save_to_local_files(docid, tableid, table_data)

    if ('ColumnType' in table_data):
        print("RETURNED")
        print(table_data['ColumnType'])
        print(table_data.columns)
        print(len(table_data))

    return table_data.copy()

def load_from_local_file(docid, tableid):
    filename = os.path.join(GRIST_DATA_DIR, f"{docid}", f"{tableid}.json")
    if os.path.exists(filename):
        return pd.read_json(open(filename, "r"), orient="records", lines=True)
    return None

def get_table_schema(docid, tableid):
    if tableid not in solved_tables_schema:
        URL = f"{GRIST_URL}api/docs/{docid}/tables/{tableid}/columns"
        res = cached_get_query(URL, headers=HEADERS, verify=False)["columns"]
        columns = pd.DataFrame(
            [f["fields"] for f in res], index=[f["id"] for f in res]
        )
        solved_tables_schema[tableid] = columns
    columns = solved_tables_schema[tableid]
    if not os.path.exists(os.path.join(GRIST_DATA_DIR, f"{docid}")):
        os.makedirs(os.path.join(GRIST_DATA_DIR, f"{docid}"))
    columns.to_json(os.path.join(GRIST_DATA_DIR, f"{docid}", f"{tableid}.schema.json"), orient="records", lines=True)
    return columns

def get_internal_columns(columns):
    internal_cols = columns[columns["description"].str.lower().str.startswith("internal")]["label"].tolist()
    if internal_cols:
        import time
        print("INTERNAL COLUMNS:")
        print(internal_cols)
        time.sleep(3)
    return internal_cols

def preload_column_types(columns, docid):
    ref_cols = columns[columns["type"].str.startswith("Ref:")]
    reflist_cols = columns[columns["type"].str.startswith("RefList:")]
    for c in ref_cols["type"].unique():
        if c.split(":")[1] not in solved_tables_schema:
            get_grist_table(c.split(":")[1])
    for c in reflist_cols["type"].unique():
        if c.split(":")[1] not in solved_tables_schema:
            get_grist_table(c.split(":")[1])

def get_table_data(docid, tableid, filter, sort):
    tablehash = hashlib.md5(str(f"{tableid}{filter}{sort}").encode("utf8")).hexdigest()
    if tablehash not in solved_tables_data:
        URL = f"{GRIST_URL}api/docs/{docid}/tables/{tableid}/records"
        args = {"filter": filter, "sort": sort}
        res = cached_get_query(URL, json=args, headers=HEADERS, verify=False)
        res = res["records"]
        solved_tables_data[tablehash] = pd.DataFrame(
            [f["fields"] for f in res], index=[f["id"] for f in res]
        )
    return solved_tables_data[tablehash]

def process_reference_columns(table_data, columns, refq, tableid=None):
    ref_cols = columns[columns["type"].str.startswith("Ref:")]
    print(ref_cols)
    for i, c in ref_cols.iterrows():
        tn = c["type"].split(":")[1]
        th = hashlib.md5(str(f"{tn}{{}}").encode("utf8")).hexdigest()
        if i in refq:
            q = refq[i]
            if isinstance(q, list):
                table_data = table_data.query(i + "in @q").copy()
            else:
                table_data = table_data.query(i + "==@q").copy()
    
    for i, c in ref_cols.iterrows():
        print(i)
        tn = c["type"].split(":")[1]
        th = hashlib.md5(str(f"{tn}{{}}").encode("utf8")).hexdigest()
        if th in solved_tables_data:
            displayCol = c["displayCol"]
            try:
                colname = solved_tables_schema[tn].query("colRef==@displayCol").index[0]
            except IndexError:
                colname = solved_tables_schema[tn].index[0]
            print(colname, displayCol)
            try:
                table_data[i] = table_data[i].fillna(-1).astype(int).map(solved_tables_data[th][colname])
            except Exception as e:
                print(e)
                print("Failing to map (already mapped ?): ", colname, displayCol, table_data[i])
                #table_data[i] = table_data[i].map(solved_tables_data[th][colname])
        else:
            print(f"{tn} not solved")
    return table_data

def process_reflist_columns(table_data, columns, query, tableid):
    reflist_columns = columns[columns["type"].str.startswith("RefList:")]
    for column_name, column_info in reflist_columns.iterrows():
        table_name = column_info["type"].split(":")[1]
        table_hash = hashlib.md5(str(f"{table_name}{{}}").encode("utf8")).hexdigest()
        if column_name in query:
            query_set = set(query[column_name]) if isinstance(query[column_name], (list, tuple)) else set([query[column_name]])
            table_data = table_data[
                table_data[column_name].apply(
                    lambda cell: (bool(len(set(cell).intersection(query_set))) if cell else False)
                )
            ].copy()
    #print(reflist_columns)
    for column_name, column_info in reflist_columns.iterrows():
        table_name = column_info["type"].split(":")[1]
        table_hash = hashlib.md5(str(f"{table_name}{{}}").encode("utf8")).hexdigest()
        if table_hash in solved_tables_data:
            display_column = column_info["displayCol"]
            try:
                column_name_to_display = solved_tables_schema[table_name].query("colRef==@display_column").index[0]
            except IndexError:
                column_name_to_display = solved_tables_schema[table_name].index[0]
            #print(f"Resolving {table_name}  display_column: {display_column} {column_name} -> mapped via {column_name_to_display} ")                
            table_data[column_name] = table_data[column_name].apply(
                lambda cell: (
                    [solved_tables_data[table_hash][column_name_to_display].get(cell_value, f"Not resolved - {cell_value}") for cell_value in cell[1:]]
                    if cell
                    else cell
                )
            )
        else:
            print(f"missing table name  : {table_name}")
            # time.sleep(10)
    return table_data

def process_choicelist_columns(table_data, columns):
    choicelist_cols = columns[columns["type"].str.startswith("ChoiceList")]
    for i, c in choicelist_cols.iterrows():
        table_data[i] = table_data[i].apply(
            lambda c: (", ".join([cc for cc in c[1:]]) if c else c)
        )
    return table_data

def process_date_columns(table_data, columns):
    lc=None
    try:
        date_cols = columns[columns["type"].str.startswith("Date")]
        for i, c in date_cols.iterrows():
            lc = c
            table_data[i] = pd.to_datetime(table_data[i] * 10**9)
        fdate_cols = columns[columns["type"].str.startswith("Any")]
        for i, c in fdate_cols.iterrows():
            lc = c
            table_data[i] = table_data[i].map(lambda x:(pd.to_datetime(x[1]* 10**9) if x is not None and isinstance(x, (list, tuple)) and x[0]=='d' else x) )
    except Exception as e:
        print("Error whil processing date column",lc,e)

    return table_data

def save_to_local_files(docid, tableid, table_data):
    os.makedirs(os.path.join(GRIST_DATA_DIR, f"{docid}"), exist_ok=True)
    csv_filename = os.path.join(GRIST_DATA_DIR, f"{docid}", f"{tableid}.csv")
    table_data.to_csv(csv_filename, index=False, header=True)
    json_filename = os.path.join(GRIST_DATA_DIR, f"{docid}", f"{tableid}.json")
    table_data.to_json(json_filename, orient="records", lines=True)


def query_chat_gpt(query_text):
    OPENAI_HEADERS = {"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"}
    URL = f"https://api.openai.com/v1/engines/davinci/completions"
    data = {
        "prompt": f'"{query_text}"',
        "temperature": 0.9,
        "max_tokens": 100,
        "top_p": 1,
        "frequency_penalty": 0,
        "presence_penalty": 0,
        "stop": ["\n"],
    }
    res = requests.post(URL, json=data, headers=OPENAI_HEADERS, verify=False).json()
    return res["choices"][0]["text"]


def update_grist_table(tableid, dataframe, key_columns, docid=GRIST_DOCID):
    URL = f"{GRIST_URL}api/docs/{docid}/tables/{tableid}/records"
    keys = set()

    records = []
    for i, r in dataframe.iterrows():
        key = {k: r[k] for k in key_columns}

        if str(key) not in keys:
            keys.add(str(key))
            record = {
                "require": key,
                "fields": {c: r[c] for c in dataframe.columns if c not in key_columns},
            }
            records.append(record)
    if len(records):
        res = requests.put(
            URL, json={"records": records}, headers=HEADERS, verify=False
        )
        #print(res.status_code)
        #print(res.text)

        # if res.status_code==400:


def format_table(
    table,
    TABLE_FMT="grid",
    column_width=None,
    prefix="Column",
    default_width=40,
    MUL=10,
) -> str:
    column_width = column_width or {}
    table_schema = table.copy()
    for c in table_schema.columns:
        table_schema[c] = (
            table_schema[c]
            .astype(str)
            .apply(
                lambda x: textwrap.fill(
                    x, width=MUL * column_width.get(c, default_width)
                ).ljust(MUL * column_width.get(c, default_width))
            )
        )
    cap_first=lambda s: s[0].upper()+s[1:] if s else s
    header_format = lambda s: (
        " ".join(re.sub(r"([a-z])([A-Z])(?=[A-Z])",  lambda x: x.group(1)+" "+x.group(2) ,
                        re.sub(r"(?<!^)([A-Z])(?=[a-z])", lambda x: " "+x.group(1),
                                cap_first(re.sub("^" + prefix, "", s.replace('_', ' '))))).split())
        if isinstance(s, str)
        else s
    )

    table_schema = tabulate.tabulate(
        table_schema,
        headers=["**%s**" % (header_format(col),) for col in table_schema.columns],
        tablefmt=TABLE_FMT,
        showindex=False,
    )
    return table_schema


if __name__ == "__main__":
    print(get_mic_iso_map())
