from pg_utils import get_all_data,get_today_data
from sentence_transformers import SentenceTransformer
import chromadb
#from chromadb.config import Settings
CHROMA_DIR = "chroma_store"
MONTH_MAP = {
    "01":"January" ,
    "02":"February",
    "03":"March",
    "04":"April",
    "05":"May",
    "06":"June",
    "07":"July",
    "08":"August",
    "09":"September",
    "10":"October",
    "11":"November",
    "12":"December"
}


def get_records(dedup: bool = False):
    if dedup:
        return get_all_data()      # full dataset
    else:
        return get_today_data()    # fast path

def filter_existing(collection, rows):
    existing_ids = set()

    CHUNK = 500
    for i in range(0, len(rows), CHUNK):
        batch_ids = [r["hashcode"] for r in rows[i:i+CHUNK]]
        result = collection.get(ids=batch_ids)
        existing_ids.update(result["ids"])

    return [r for r in rows if r["hashcode"] not in existing_ids]

def validate_metadata(row):
    for k, v in row.items():
        if v is None:
            print(f"⚠️ None metadata: {k}")

def clean_metadata(row: dict):
    cleaned = {}
    for k, v in row.items():
        if v is None:
            cleaned[k] = "Unknown"              # safest default
        elif isinstance(v, (int, float, str, bool)):
            cleaned[k] = v
        else:
            cleaned[k] = str(v)          # fallback safety
    if cleaned['txn_date'] != "Unknown":
        date = cleaned['txn_date'].split("-")
        month = date[1]
        year = date[0]
        cleaned['txn_month']=MONTH_MAP[month]
        cleaned['txn_year']=int(year)
    else:
        cleaned['txn_month'] = "Unknown"
        cleaned['txn_year'] = "Unknown"
    return cleaned


def run_embedding_pipeline(dedup=False):
    rows = get_records(dedup=dedup)

    if not rows:
        print("ℹ️ No records to process")
        return
    client = chromadb.PersistentClient(path=CHROMA_DIR)

    collection = client.get_or_create_collection("expenses")

    if dedup:
        rows = filter_existing(collection, rows)
        if not rows:
            print("ℹ️ All records already embedded")
            return

    model = SentenceTransformer("all-MiniLM-L6-v2")
    cleaned_rows = [clean_metadata(r) for r in rows]
    texts = [
        f"On {r['txn_date']} you made a {r['txn_type']} transaction "
        f"of ₹{r['amount']} for {r['category']}  to {r['paid_to']}."
        for r in cleaned_rows
    ]

    embeddings = model.encode(texts).tolist()

    collection.add(
        documents=texts,
        embeddings=embeddings,
        metadatas=cleaned_rows,
        ids=[r["hashcode"] for r in rows]
    )

    print(f"✅ Embedded {len(rows)} records")


model = SentenceTransformer("all-MiniLM-L6-v2")

client = chromadb.PersistentClient(path="./chroma_store")
collection = client.get_collection("expenses")


def semantic_search(query,filter_query):
    #run_embedding_pipeline()
    filtered = collection.get(where=filter_query)
    total = len(filtered["ids"])

    query_embedding = model.encode(query).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        where = filter_query,
        n_results=total
    )

    return results['documents']

# run_embedding_pipeline(dedup=True)

# sample = collection.get(limit=1)
# print(sample["metadatas"])
