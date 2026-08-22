# Suggestion Techniques

Python implementations of each suggestion technique described in
[README_SUGGESTIONS.md](../docs/README_SUGGESTIONS.md).

## Setup

```bash
cd techniques
pip install -r requirements.txt
```

`rapidfuzz` provides optimized C-extension implementations of Levenshtein,
Damerau-Levenshtein, and Jaro-Winkler. Each technique implements the algorithm
from scratch first, then compares results against `rapidfuzz` where applicable.
The techniques work without `rapidfuzz` installed — library comparisons are
skipped with a helpful message.

## Running

Each file is self-contained. Run any example directly:

```bash
python3 03_levenshtein.py
python3 08_jaro_winkler.py
```

Each example prints:
1. A demonstration of the technique working on realistic inputs
2. A "Shortcomings" section with concrete failure cases
3. A **Pros vs Cons** summary box for quick comparison

All techniques import shared test data from `command_tree.py`.

## Files

| File | Technique |
|------|-----------|
| `command_tree.py` | Shared command tree and helpers |
| `01_exact_prefix.py` | Exact Prefix Matching |
| `02_multi_token_prefix.py` | Multi-token Prefix Abbreviation |
| `03_levenshtein.py` | Levenshtein Distance |
| `04_damerau_levenshtein.py` | Damerau-Levenshtein Distance |
| `05_weighted_edit_costs.py` | Weighted Edit Costs |
| `06_keyboard_aware.py` | Keyboard-Aware Weighted Distance |
| `07_threshold_scaling.py` | Threshold Scaling by Token Length |
| `08_jaro_winkler.py` | Jaro-Winkler Similarity |
| `09_ngram_similarity.py` | N-gram Similarity |
| `10_tree_matching.py` | Context-Aware Tree Matching |
| `11_flat_corpus_scan.py` | Flat-Corpus Scan |
| `12_hyphenated_handling.py` | Hyphenated Keyword Handling |
| `13_argument_preservation.py` | Variable Argument Preservation |
| `14_positional_swap.py` | Positional Swap Detection |
| `15_ai_semantic.py` | AI Semantic Backend (mock) |
| `16_combined_pipeline.py` | Combined Pipeline |
