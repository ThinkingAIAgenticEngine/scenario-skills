#!/usr/bin/env bash
#
# company-scaffold.sh — company onboarding: deterministic part
#
# Initialize a complete KB directory (single directory) for a "new customer (company / caliber subject)":
#   company-level abstraction layer (index.md / reference / metrics / rules) + an empty projects/.
# Each subsequent project uses scaffold.sh --company-layer to point at this directory and
# append a project-<N>/ under projects/, without creating another directory or copying company-layer files.
#
# This script only does deterministic mechanical work (copy templates to create company-level files + empty projects/).
# "Caliber judgments" are done by the agent during the "company onboarding" stage: confirm/rewrite
# the "applicable sub-metrics" and "recommended machine-readable definition" in metrics/*.md per family,
# and write the company name into index.md.
#
# Usage:
#   bash company-scaffold.sh --company acme --company-name "Acme Inc."
#   bash company-scaffold.sh --company acme --company-name "Acme Inc." --families event,retention,prop
#   bash company-scaffold.sh --list
#
set -euo pipefail

# ---- default template source: the company-layer skeleton (index.md / reference / metrics / rules) lives in this same scripts/ dir ----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_TEMPLATE_DIR="$SCRIPT_DIR"

COMPANY=""
COMPANY_NAME=""
OUT_DIR=""
TEMPLATE_DIR="$DEFAULT_TEMPLATE_DIR"
FAMILIES=""          # comma-separated; empty = all 9 families
LIST=0

usage() {
  cat <<'USAGE'
Usage: company-scaffold.sh --company <slug> --company-name "<name>" [options]

  --company slug         required, customer/company slug (directory name prefix, e.g. acme)
  --company-name name    required, company display name
  --out-dir dir          output directory, default ./kb-<slug>
  --template-dir dir     company-layer template source, default <skill>/scripts
  --families a,b,c       seed only these metric families (default: all 9 families)
  --list                 list existing company KBs, do not create
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --company)      [[ $# -ge 2 ]] || { echo "error: --company requires a value" >&2; exit 1; }; COMPANY="$2"; shift 2 ;;
    --company-name) [[ $# -ge 2 ]] || { echo "error: --company-name requires a value" >&2; exit 1; }; COMPANY_NAME="$2"; shift 2 ;;
    --out-dir)      [[ $# -ge 2 ]] || { echo "error: --out-dir requires a value" >&2; exit 1; }; OUT_DIR="$2"; shift 2 ;;
    --template-dir) [[ $# -ge 2 ]] || { echo "error: --template-dir requires a value" >&2; exit 1; }; TEMPLATE_DIR="$2"; shift 2 ;;
    --families)     [[ $# -ge 2 ]] || { echo "error: --families requires a value" >&2; exit 1; }; FAMILIES="$2"; shift 2 ;;
    --list)         LIST=1; shift ;;
    -h|--help)      usage; exit 0 ;;
    *) echo "unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

# ---- --list: list existing company KBs ----
if [[ "$LIST" -eq 1 ]]; then
  found=0
  for d in ./kb-*/; do
    [[ -d "$d" ]] || continue
    slug="$(basename "$d")"
    name=""
    [[ -f "$d/index.md" ]] && name="$(sed -n '1s/^# //p' "$d/index.md" 2>/dev/null | sed 's/ Business Metrics Definition Library$//')"
    echo "  - ${slug#kb-}${name:+  ($name)}"
    found=1
  done
  [[ "$found" -eq 0 ]] && echo "no company KB found (./kb-* does not exist)"
  exit 0
fi

if [[ -z "$COMPANY" || -z "$COMPANY_NAME" ]]; then
  echo "error: --company and --company-name are required (or use --list to see existing company KBs)" >&2
  usage
  exit 1
fi
if [[ ! "$COMPANY" =~ ^[a-z0-9][a-z0-9-]*$ ]]; then
  echo "error: --company must be a lowercase slug containing only letters, digits, and hyphens" >&2
  exit 1
fi

[[ -z "$OUT_DIR" ]] && OUT_DIR="./kb-$COMPANY"

# ---- validate the template source ----
for f in index.md reference/metric-registry.md rules/caveats-checklist.md; do
  if [[ ! -f "$TEMPLATE_DIR/$f" ]]; then
    echo "error: template source missing $TEMPLATE_DIR/$f" >&2
    exit 1
  fi
done
if ! ls "$TEMPLATE_DIR/metrics/"*.md >/dev/null 2>&1; then
  echo "error: template source missing $TEMPLATE_DIR/metrics/*.md" >&2
  exit 1
fi

# ---- validate requested metric families before creating any output ----
if [[ -n "$FAMILIES" ]]; then
  IFS=',' read -r -a requested_families <<< "$FAMILIES"
  for family in "${requested_families[@]}"; do
    family="${family// /}"
    [[ -z "$family" ]] && continue
    if [[ ! "$family" =~ ^[a-z0-9][a-z0-9_-]*$ ]]; then
      echo "error: invalid metric family: $family" >&2
      exit 1
    fi
    if [[ ! -f "$TEMPLATE_DIR/metrics/${family}.md" ]]; then
      echo "error: template source has no metric family ${family}.md" >&2
      exit 1
    fi
  done
fi

# ---- output directory safety check ----
if [[ -d "$OUT_DIR" ]] && [[ -n "$(ls -A "$OUT_DIR" 2>/dev/null)" ]]; then
  echo "error: output directory already exists and is non-empty: $OUT_DIR (this customer may already be initialized; check with --list and choose a new directory)" >&2
  exit 1
fi

# ---- create directories + copy the 4 company-level files + empty projects/ ----
mkdir -p "$OUT_DIR/reference" "$OUT_DIR/metrics" "$OUT_DIR/rules" "$OUT_DIR/projects"
cp "$TEMPLATE_DIR/index.md" "$OUT_DIR/index.md"
cp "$TEMPLATE_DIR/reference/metric-registry.md" "$OUT_DIR/reference/metric-registry.md"
cp "$TEMPLATE_DIR/rules/caveats-checklist.md" "$OUT_DIR/rules/caveats-checklist.md"

# ---- metric family trimming: --families seeds only the specified families, otherwise all ----
# The family set = the .md files actually present under metrics/; no extra README (avoids being picked up by +add directory upload).
if [[ -n "$FAMILIES" ]]; then
  IFS=',' read -r -a fams <<< "$FAMILIES"
  for f in "${fams[@]}"; do
    f="${f// /}"   # strip spaces
    [[ -z "$f" ]] && continue
    src="$TEMPLATE_DIR/metrics/${f}.md"
    cp "$src" "$OUT_DIR/metrics/${f}.md"
  done
else
  cp "$TEMPLATE_DIR/metrics/"*.md "$OUT_DIR/metrics/"
fi

# ---- print follow-up guidance ----
echo
echo "========== company KB skeleton generated =========="
echo "KB directory: $OUT_DIR"
echo "company-level files are ready, projects/ is empty (each project appends later)."
echo
echo "Next the agent completes the 'company onboarding' checklist (see SKILL.md 'Stage 0'),"
echo "then replaces the index.md title with the real company name and records it in the index.md changelog."
echo "After that, use scaffold.sh to append project layers to this directory for this customer's projects:"
echo
echo "  bash scaffold.sh --project-id <N> --project-name \"<ProjectName>\" --company-layer \"$OUT_DIR\""
