"""Shared, sticky data-source declarations across modeling and experiments."""
import pandas as pd


def resolve_data_kind(data_kind=None, *, frames=(), manifest=None):
    declarations = []

    def add(source, values):
        values = sorted({str(value).strip() for value in values if pd.notna(value)})
        if values:
            declarations.append({"source": source, "values": values})

    if data_kind is not None:
        add("explicit", [data_kind])
    for source, frame in frames:
        if "data_kind" in frame:
            add(source, frame["data_kind"].dropna().unique().tolist())
    if isinstance(manifest, dict):
        if manifest.get("data_kind") is not None:
            add("manifest.data_kind", [manifest["data_kind"]])
        if manifest.get("simulation_only") is True:
            add("manifest.simulation_only", ["simulated"])
        for previous in manifest.get("data_kind_sources", []):
            if isinstance(previous, dict) and isinstance(previous.get("values"), list):
                add("manifest." + str(previous.get("source", "declaration")), previous["values"])
    values = [value.lower() for declaration in declarations for value in declaration["values"]]
    # "模拟" matches the Chinese metadata label for simulated data; keep it so
    # Chinese-labeled provenance values remain detected.
    simulated = any(value.startswith(("simulat", "synthetic")) or "模拟" in value for value in values)
    resolved = "simulated" if simulated else "real" if "real" in values else "unknown"
    return {"data_kind": resolved, "simulation_only": simulated, "data_kind_sources": declarations}


def csv_data_kind(path, data_kind=None):
    """Scan only provenance when present, without loading an event export twice."""
    columns = pd.read_csv(path, nrows=0).columns
    values = set()
    if "data_kind" in columns:
        for chunk in pd.read_csv(path, usecols=["data_kind"], chunksize=100000):
            values.update(str(value) for value in chunk["data_kind"].dropna().unique())
    declarations = pd.DataFrame({"data_kind": sorted(values)})
    return resolve_data_kind(data_kind, frames=[(str(path), declarations)])
