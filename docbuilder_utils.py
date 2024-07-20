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

GRIST_CACHE_DIR = ".grist_cache"
grist_cache = diskcache.Cache(
    GRIST_CACHE_DIR, eviction_policy="least-recently-used", cull_limit=0
)

GRIST_URL = "https://bmlltech.getgrist.com/"
APIKEY = os.environ.get("BMLL_GRIST_TOKEN")
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
    print(args, kwargs)
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
    print(docname)
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
def solve_coverage_table(expr):
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
        return get_grist_table(
            expr.strip(), docid=get_grist_docid(params.strip()[1:-1].strip())
        )
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
):
    import snowflake
    import snowflake.connector
    connargs = dict(
        user=os.environ.get("SNOWFLAKE_USER", "bertrandnouvel"),
        password=os.environ.get("SNOWFLAKE_PASSWORD"),
        account=os.environ.get("SNOWFLAKE_ACCOUNT", "tib96089"),
        region=os.environ.get("SNOWFLAKE_REGION", "us-east-1"),
        role="PROD_SALES_RO_ROLE",
        database=database,
        schema=schema,
        warehouse=warehouse,
    )
    return snowflake.connector.connect(**connargs)



PROD_OFFLINE_MODE = os.environ.get(
    "PROD_OFFLINE_MODE"
)  # only takes what's inside the repo


def get_grist_table(
    tableid=TABLEID, filter={}, sort="", docid=GRIST_DOCID, get_cols=True, refq={}
):
    filename = os.path.join(GRIST_DATA_DIR, f"{docid}", f"{tableid}.json")
    if os.path.exists(filename) and PROD_OFFLINE_MODE:
        return pd.read_json(open(filename, "r"), orient="records", lines=True)

    internal_cols = []
    if get_cols:
        if tableid not in solved_tables_schema:
            URL = f"{GRIST_URL}api/docs/{docid}/tables/{tableid}/columns"
            res = cached_get_query(URL, headers=HEADERS, verify=False)["columns"]
            columns = pd.DataFrame(
                [f["fields"] for f in res], index=[f["id"] for f in res]
            )
            solved_tables_schema[tableid] = columns
        columns = solved_tables_schema[tableid]
        columns.to_json( os.path.join(GRIST_DATA_DIR, f"{docid}", f"{tableid}.schema.json"),orient="records", lines=True)
        internal_cols = columns[columns["description"].str.lower().str.startswith("internal")]["label"].tolist()
        if internal_cols:
            import time
            print(internal_cols)
            time.sleep(3)
        date_cols = columns[columns["type"].str.startswith("Date")]
        ref_cols = columns[columns["type"].str.startswith("Ref:")]
        reflist_cols = columns[columns["type"].str.startswith("RefList:")]
        choicelist_cols = columns[columns["type"].str.startswith("ChoiceList")]
        for c in ref_cols["type"].unique():
            if c.split(":")[1] not in solved_tables_schema:
                get_grist_table(c.split(":")[1])
        for c in reflist_cols["type"].unique():
            if c.split(":")[1] not in solved_tables_schema:
                get_grist_table(c.split(":")[1])

    tablehash = hashlib.md5(str(f"{tableid}{filter}{sort}").encode("utf8")).hexdigest()
    if tablehash not in solved_tables_data:
        URL = f"{GRIST_URL}api/docs/{docid}/tables/{tableid}/records"
        args = {}
        args["filter"] = filter
        args["sort"] = sort
        res = cached_get_query(URL, json=args, headers=HEADERS, verify=False)
        # if "records" not in res:
        #     print(res)
        res = res["records"]
        solved_tables_data[tablehash] = pd.DataFrame(
            [f["fields"] for f in res], index=[f["id"] for f in res]
        )

    res = solved_tables_data[tablehash]
    if get_cols:
        for i, c in ref_cols.iterrows():
            tn = c["type"].split(":")[1]
            th = hashlib.md5(str(f"{tn}{{}}").encode("utf8")).hexdigest()
            if i in refq:
                q = refq[i]
                if isinstance(q, list):
                    res = res.query(i + "in @q").copy()
                else:
                    res = res.query(i + "==@q").copy()
            if th in solved_tables_data:
                displayCol = c["displayCol"]
                # print (displayCol)
                # print(solved_tables_schema[tn])
                try:
                    colname = (
                        solved_tables_schema[tn].query("colRef==@displayCol").index[0]
                    )
                except IndexError:
                    colname = solved_tables_schema[tn].index[0]
                # print(colname)
                res[i] = res[i].map(solved_tables_data[th][colname])

        for i, c in reflist_cols.iterrows():
            tn = c["type"].split(":")[1]
            th = hashlib.md5(str(f"{tn}{{}}").encode("utf8")).hexdigest()
            if i in refq:
                q = refq[i]
                if isinstance(q, (list, tuple)):
                    q = set(refq[i])
                else:
                    q = set([refq[i]])
                res = res[
                    res[i].apply(
                        lambda c: (bool(len(set(c).intersection(q))) if c else False)
                    )
                ].copy()

            if th in solved_tables_data:
                displayCol = c["displayCol"]
                # print (displayCol)
                # print(solved_tables_schema[tn])
                try:
                    colname = (
                        solved_tables_schema[tn].query("colRef==@displayCol").index[0]
                    )
                except IndexError:
                    colname = solved_tables_schema[tn].index[0]

                # print(i, th, colname, res[i])
                res[i] = res[i].apply(
                    lambda c: (
                        [solved_tables_data[th][colname].get(cc, None) for cc in c[1:]]
                        if c
                        else c
                    )
                )
        for i, c in choicelist_cols.iterrows():
            res[i] = res[i].apply(
                lambda c: (", ".join([cc for cc in c[1:]]) if c else c)
            )
        for i, c in date_cols.iterrows():
            res[i] = pd.to_datetime(res[i] * 10**9)

    res = res.drop(internal_cols, axis=1, errors="ignore")
    os.makedirs(os.path.join(GRIST_DATA_DIR, f"{docid}"), exist_ok=True)
    filename = os.path.join(GRIST_DATA_DIR, f"{docid}", f"{tableid}.csv")
    res.to_csv(filename, index=False, header=True)
    filename = os.path.join(GRIST_DATA_DIR, f"{docid}", f"{tableid}.json")
    res.to_json(filename, orient="records", lines=True)

    return res


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
        print(res.status_code)
        print(res.text)

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

    header_format = lambda s: (
        " ".join(re.sub(r"(?<!^)(?=[A-Z])", " ", re.sub("^" + prefix, "", s.replace('_', ' '))).split())
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
