import duckdb
import os
import glob
import shutil

# ============================================================
# TASK 2
# MERGE FIRST -> THEN REMOVE DUPLICATES
# MEMORY-SAFE VERSION
# ============================================================

MERGED_FILE = "output/task2/merged_raw.parquet"
BUCKET_DIR = "output/task2/merged_buckets"
DEDUP_DIR = "output/task2/dedup_parts"
FINAL_FILE = "output/task2/final_unique.parquet"

NUM_BUCKETS = 256

# ------------------------------------------------------------
# Create directories
# ------------------------------------------------------------

os.makedirs(BUCKET_DIR, exist_ok=True)
os.makedirs(DEDUP_DIR, exist_ok=True)

print("=" * 70)
print("TASK 2: MERGE FIRST -> THEN REMOVE DUPLICATES")
print("=" * 70)

# ------------------------------------------------------------
# DuckDB connection
# ------------------------------------------------------------

con = duckdb.connect("output/task2/task2.duckdb")

con.execute("SET memory_limit='1.5GB'")
con.execute("SET threads=2")
con.execute("SET preserve_insertion_order=false")
con.execute("SET temp_directory='output/task2/duckdb_temp'")

# ------------------------------------------------------------
# STEP 1: Verify merged raw file
# ------------------------------------------------------------

print()
print("[1/4] Checking merged raw data...")

merged_count = con.execute(
    f"""
    SELECT COUNT(*)
    FROM read_parquet('{MERGED_FILE}')
    """
).fetchone()[0]

print(f"Merged raw records: {merged_count:,}")

expected_count = 54_188_497

if merged_count != expected_count:
    raise RuntimeError(
        f"Unexpected merged count: {merged_count:,}. "
        f"Expected: {expected_count:,}"
    )

print("Merged count verified.")

# ------------------------------------------------------------
# STEP 2: Create physical hash buckets
# ------------------------------------------------------------

print()
print("[2/4] Creating physical hash buckets...")
print(f"Number of buckets: {NUM_BUCKETS}")
print("This may take some time.")

# Remove any old bucket directory contents
if os.path.exists(BUCKET_DIR):
    shutil.rmtree(BUCKET_DIR)

os.makedirs(BUCKET_DIR, exist_ok=True)

con.execute(
    f"""
    COPY (
        SELECT
            *,
            hash(
                md5(
                    concat_ws(
                        chr(31),
                        coalesce(CAST(prefix AS VARCHAR), ''),
                        coalesce(CAST(peer_ip AS VARCHAR), ''),
                        coalesce(CAST(peer_as AS VARCHAR), ''),
                        coalesce(CAST(peer_bgp_id AS VARCHAR), ''),
                        coalesce(CAST(originated_time AS VARCHAR), ''),
                        coalesce(CAST(path_attributes AS VARCHAR), '')
                    )
                )
            ) % {NUM_BUCKETS} AS bucket
        FROM read_parquet('{MERGED_FILE}')
    )
    TO '{BUCKET_DIR}'
    (
        FORMAT PARQUET,
        PARTITION_BY (bucket),
        COMPRESSION ZSTD
    )
    """
)

# Find all physical parquet files
bucket_files = glob.glob(
    os.path.join(BUCKET_DIR, "bucket=*", "*.parquet")
)

print(f"Physical bucket files created: {len(bucket_files)}")

if len(bucket_files) == 0:
    raise RuntimeError("No physical bucket files were created.")

# ------------------------------------------------------------
# STEP 3: Deduplicate each bucket separately
# ------------------------------------------------------------

print()
print("[3/4] Deduplicating buckets one at a time...")
print()

# Clean old dedup output
if os.path.exists(DEDUP_DIR):
    shutil.rmtree(DEDUP_DIR)

os.makedirs(DEDUP_DIR, exist_ok=True)

total_after_dedup = 0
processed = 0

for bucket_number in range(NUM_BUCKETS):

    bucket_path = os.path.join(
        BUCKET_DIR,
        f"bucket={bucket_number}"
    )

    files = glob.glob(
        os.path.join(bucket_path, "*.parquet")
    )

    if not files:
        continue

    processed += 1

    print(
        f"Processing bucket {bucket_number:03d} "
        f"({processed} processed)..."
    )

    output_file = os.path.join(
        DEDUP_DIR,
        f"dedup_{bucket_number:03d}.parquet"
    )

    # One bucket only -> much lower memory usage
    con.execute(
        f"""
        COPY (
            SELECT
                min(timestamp) AS timestamp,
                any_value(source) AS source,
                any_value(peer_index) AS peer_index,
                prefix,
                peer_ip,
                peer_as,
                peer_bgp_id,
                originated_time,
                any_value(path_attributes_length)
                    AS path_attributes_length,
                path_attributes
            FROM read_parquet('{bucket_path}/*.parquet')
            GROUP BY
                prefix,
                peer_ip,
                peer_as,
                peer_bgp_id,
                originated_time,
                path_attributes
        )
        TO '{output_file}'
        (
            FORMAT PARQUET,
            COMPRESSION ZSTD
        )
        """
    )

    bucket_count = con.execute(
        f"""
        SELECT COUNT(*)
        FROM read_parquet('{output_file}')
        """
    ).fetchone()[0]

    total_after_dedup += bucket_count

    print(
        f"  Unique records in bucket: {bucket_count:,}"
    )

print()
print(f"Non-empty buckets processed: {processed}")
print(
    f"Total records after bucket dedup: "
    f"{total_after_dedup:,}"
)

# ------------------------------------------------------------
# STEP 4: Combine deduplicated buckets
# ------------------------------------------------------------

print()
print("[4/4] Combining deduplicated buckets...")

dedup_files = glob.glob(
    os.path.join(DEDUP_DIR, "*.parquet")
)

if not dedup_files:
    raise RuntimeError("No deduplicated bucket files found.")

# Remove old final file if present
if os.path.exists(FINAL_FILE):
    os.remove(FINAL_FILE)

con.execute(
    f"""
    COPY (
        SELECT *
        FROM read_parquet('{DEDUP_DIR}/*.parquet')
    )
    TO '{FINAL_FILE}'
    (
        FORMAT PARQUET,
        COMPRESSION ZSTD
    )
    """
)

final_count = con.execute(
    f"""
    SELECT COUNT(*)
    FROM read_parquet('{FINAL_FILE}')
    """
).fetchone()[0]

print()
print("=" * 70)
print("TASK 2 COMPLETE")
print("=" * 70)

print(f"Merged raw records : {merged_count:,}")
print(f"After dedup        : {final_count:,}")
print(f"Duplicates removed : {merged_count - final_count:,}")
print()
print(f"Final file: {FINAL_FILE}")
print("=" * 70)

con.close()
