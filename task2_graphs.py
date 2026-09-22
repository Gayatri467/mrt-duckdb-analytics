import duckdb
import matplotlib.pyplot as plt
import os

# --------------------------------------------------
# Paths
# --------------------------------------------------

PARQUET = "output/task2/final_unique.parquet"
GRAPH_DIR = "output/task2/graphs"

os.makedirs(GRAPH_DIR, exist_ok=True)

# --------------------------------------------------
# Connect to DuckDB
# --------------------------------------------------

con = duckdb.connect()

print("Reading:", PARQUET)
print("Creating graphs...")

# --------------------------------------------------
# 1. Top 20 prefixes
# --------------------------------------------------

df_prefix = con.execute("""
    SELECT
        prefix,
        COUNT(*) AS updates
    FROM read_parquet(?)
    GROUP BY prefix
    ORDER BY updates DESC
    LIMIT 20
""", [PARQUET]).fetchdf()

plt.figure(figsize=(12, 7))

plt.barh(
    df_prefix["prefix"],
    df_prefix["updates"]
)

plt.xlabel("Number of updates")
plt.ylabel("Prefix")
plt.title("Top 20 BGP Prefixes by Number of Updates")

plt.gca().invert_yaxis()
plt.tight_layout()

plt.savefig(
    f"{GRAPH_DIR}/top_20_prefixes.png",
    dpi=150
)

plt.close()

print("Created: top_20_prefixes.png")


# --------------------------------------------------
# 2. Top 20 Peer AS numbers
# --------------------------------------------------

df_peer = con.execute("""
    SELECT
        peer_as,
        COUNT(*) AS updates
    FROM read_parquet(?)
    GROUP BY peer_as
    ORDER BY updates DESC
    LIMIT 20
""", [PARQUET]).fetchdf()

plt.figure(figsize=(12, 7))

plt.barh(
    df_peer["peer_as"].astype(str),
    df_peer["updates"]
)

plt.xlabel("Number of updates")
plt.ylabel("Peer AS")
plt.title("Top 20 Peer AS Numbers by Number of Updates")

plt.gca().invert_yaxis()
plt.tight_layout()

plt.savefig(
    f"{GRAPH_DIR}/top_20_peer_as.png",
    dpi=150
)

plt.close()

print("Created: top_20_peer_as.png")


# --------------------------------------------------
# 3. Path attribute length distribution
# --------------------------------------------------

df_path = con.execute("""
    SELECT
        path_attributes_length
    FROM read_parquet(?)
    WHERE path_attributes_length IS NOT NULL
""", [PARQUET]).fetchdf()

plt.figure(figsize=(12, 7))

plt.hist(
    df_path["path_attributes_length"],
    bins=50
)

plt.xlabel("Path attributes length")
plt.ylabel("Number of records")
plt.title("Distribution of BGP Path Attribute Length")

plt.tight_layout()

plt.savefig(
    f"{GRAPH_DIR}/path_attribute_length_distribution.png",
    dpi=150
)

plt.close()

print("Created: path_attribute_length_distribution.png")


# --------------------------------------------------
# 4. Updates over time
# --------------------------------------------------

df_time = con.execute("""
    SELECT
        to_timestamp(
            (timestamp / 3600)::BIGINT * 3600
        ) AS hour,
        COUNT(*) AS updates
    FROM read_parquet(?)
    WHERE timestamp IS NOT NULL
    GROUP BY hour
    ORDER BY hour
""", [PARQUET]).fetchdf()

plt.figure(figsize=(14, 7))

plt.plot(
    df_time["hour"],
    df_time["updates"]
)

plt.xlabel("Time")
plt.ylabel("Number of updates")
plt.title("BGP Updates Over Time")

plt.xticks(rotation=45)
plt.tight_layout()

plt.savefig(
    f"{GRAPH_DIR}/updates_over_time.png",
    dpi=150
)

plt.close()

print("Created: updates_over_time.png")


# --------------------------------------------------
# 5. Unique prefixes over time
# --------------------------------------------------

df_unique_prefix = con.execute("""
    SELECT
        to_timestamp(
            (timestamp / 3600)::BIGINT * 3600
        ) AS hour,
        COUNT(DISTINCT prefix) AS unique_prefixes
    FROM read_parquet(?)
    WHERE timestamp IS NOT NULL
    GROUP BY hour
    ORDER BY hour
""", [PARQUET]).fetchdf()

plt.figure(figsize=(14, 7))

plt.plot(
    df_unique_prefix["hour"],
    df_unique_prefix["unique_prefixes"]
)

plt.xlabel("Time")
plt.ylabel("Unique prefixes")
plt.title("Unique BGP Prefixes Over Time")

plt.xticks(rotation=45)
plt.tight_layout()

plt.savefig(
    f"{GRAPH_DIR}/unique_prefixes_over_time.png",
    dpi=150
)

plt.close()

print("Created: unique_prefixes_over_time.png")


# --------------------------------------------------
# Finished
# --------------------------------------------------

con.close()

print()
print("========================================")
print("All graphs created successfully!")
print("Location:", GRAPH_DIR)
print("========================================")
