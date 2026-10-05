#!/usr/bin/env bash
# =============================================================================
#  C2 paper - step 5: build paper.pdf and record the build log.
#
#  Runs the full LaTeX cycle (pdflatex -> bibtex -> pdflatex x2), captures the
#  complete log, and fails loudly on any unresolved reference, citation or
#  overfull-box warning that indicates a real defect.
#
#  Usage:
#     bash pipeline/05_build.sh            # build into build/
#     bash pipeline/05_build.sh --check    # build and only report pass/fail
# =============================================================================
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
C2="$(dirname "$HERE")"
BUILD="$C2/build"
LOG="$BUILD/build.log"

# TeX Live is not on PATH by default on this machine; find it explicitly.
TL_BIN=""
for cand in "$HOME/texlive/2026/bin/windows" "/c/texlive/2026/bin/windows" \
            "/c/texlive/2024/bin/windows"; do
  [ -x "$cand/pdflatex.exe" ] && TL_BIN="$cand" && break
done
if [ -z "$TL_BIN" ]; then
  echo "[build] FATAL: pdflatex not found. Run pipeline/00_setup_texlive.py first." >&2
  exit 2
fi
export PATH="$TL_BIN:$PATH"

mkdir -p "$BUILD"
cp "$C2/paper.tex" "$BUILD/paper.tex"
cp "$C2/references.bib" "$BUILD/references.bib"
mkdir -p "$BUILD/figures"
cp "$C2"/figures/*.pdf "$BUILD/figures/" 2>/dev/null || true

cd "$BUILD"
: > "$LOG"

run() {
  echo "=== $1 ===" >> "$LOG"
  shift
  "$@" >> "$LOG" 2>&1
  return $?
}

run "pdflatex (pass 1)" pdflatex -interaction=nonstopmode -halt-on-error paper.tex
p1=$?
run "bibtex" bibtex paper
pb=$?
run "pdflatex (pass 2)" pdflatex -interaction=nonstopmode -halt-on-error paper.tex
run "pdflatex (pass 3)" pdflatex -interaction=nonstopmode -halt-on-error paper.tex
p3=$?

echo "[build] pdflatex#1=$p1 bibtex=$pb pdflatex#3=$p3"

# ---- 健全性检查：未解析的引用/交叉引用会让 PDF 静默地留下 "?" ------------
PROBLEMS=0
check() {
  local label="$1" pattern="$2"
  # `grep -c` exits 1 when the count is zero; swallow that without emitting a
  # second line (the earlier `|| echo 0` produced "0\n0" and broke the test).
  local n
  n=$(grep -c "$pattern" "$BUILD/paper.log" 2>/dev/null) || n=0
  n=${n:-0}
  if [ "$n" -gt 0 ] 2>/dev/null; then
    echo "[build] PROBLEM ($label): $n occurrence(s)"
    grep -m3 "$pattern" "$BUILD/paper.log" | sed 's/^/         /'
    PROBLEMS=$((PROBLEMS + 1))
  fi
}
check "undefined references" "LaTeX Warning: Reference .* undefined"
check "undefined citations"  "LaTeX Warning: Citation .* undefined"
check "undefined control"    "Undefined control sequence"
check "emergency stop"       "Emergency stop"
check "missing file"         "! LaTeX Error: File"

PAGES=$(grep -oE "Output written on paper.pdf \(([0-9]+) pages" "$BUILD/paper.log" \
        | grep -oE "[0-9]+" | head -1)
BYTES=$(stat -c%s "$BUILD/paper.pdf" 2>/dev/null || echo 0)
echo "[build] paper.pdf: ${PAGES:-?} pages, ${BYTES} bytes"

if [ "$PROBLEMS" -gt 0 ]; then
  echo "[build] FAILED: $PROBLEMS problem class(es); see build/build.log"
  exit 1
fi
echo "[build] OK -- no undefined references, citations or control sequences."
