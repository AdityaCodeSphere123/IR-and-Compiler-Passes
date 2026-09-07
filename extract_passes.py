#!/usr/bin/env python3
"""
Extract the ordered list of *transformation* passes from the output of

    opt -passes="default<On>" -print-pipeline-passes -disable-output ...

The printed pipeline is a nested, comma-separated expression.  A name that is
immediately followed by '(' is a pass-manager adaptor (module, function, cgscc,
loop, loop-mssa, devirt<4>, coro-cond, ...) and is a container, not a
transformation.  A name may carry parameters in angle brackets
(simplifycfg<bonus-inst-threshold=1>); those ARE real passes.

Leaves are kept only if `opt --print-passes` lists them under a *passes*
section (Module / CGSCC / Function / LoopNest / Loop).  Analyses, analysis
invalidation (require<>, invalidate<>, recompute-globalsaa), instrumentation
and remarks (annotation-remarks, ee-instrument, transform-warning, cg-profile,
verify, print) are dropped.  Repeated invocations are kept, in order.

Target dumps such as AArch64LoopIdiomTransformPass are C++ class names and
cannot be written in -passes='...'; they are skipped.

Usage:
    python3 extract_passes.py --available available-passes.txt \
            passes.O0.txt passes.O1.txt passes.O2.txt passes.O3.txt
    python3 extract_passes.py ... --ordered
    python3 extract_passes.py ... --latex
"""

import argparse
import re
import sys
from collections import Counter, OrderedDict, defaultdict

# Analyses / invalidation / instrumentation / remarks / verifiers.
# Base names only (text before the first '<').
NON_TRANSFORM = {
    "verify", "print", "annotation-remarks", "no-op-module",
    "no-op-cgscc", "no-op-function", "no-op-loop", "no-op-loopnest",
    "invalidate", "require", "recompute-globalsaa",
    "ee-instrument", "transform-warning", "cg-profile",
}

# Printed by -print-pipeline-passes on some targets; not a -passes= name.
UNNAMEABLE = {
    "AArch64LoopIdiomTransformPass",
}

PASS_SECTIONS = (
    "Module passes:", "Module passes with params:",
    "CGSCC passes:", "CGSCC passes with params:",
    "Function passes:", "Function passes with params:",
    "LoopNest passes:", "Loop passes:", "Loop passes with params:",
)

# Short shared descriptions for the report.  Unknown names fall back to the
# pass name itself.
DESCRIPTIONS = {
    "adce": "aggressive DCE using control dependence",
    "aggressive-instcombine": "heavier instcombine patterns (e.g. tables)",
    "alignment-from-assumptions": "raise load/store alignment from assumes",
    "always-inline": "inline functions marked always_inline",
    "annotation2metadata": "turn llvm.global.annotations into metadata",
    "argpromotion": "promote by-ref arguments to by-value",
    "bdce": "bit-tracking dead code elimination",
    "called-value-propagation": "propagate function pointers through calls",
    "callsite-splitting": "split a call so each predecessor can specialise it",
    "chr": "control-height reduction (flatten hot conditions)",
    "constmerge": "merge identical global constants",
    "constraint-elimination": "fold compares using dominating conditions",
    "coro-cleanup": "late coroutine lowering cleanup",
    "coro-early": "early coroutine lowering",
    "coro-elide": "elide coroutine heap allocation when possible",
    "coro-split": "split a coroutine into resume/destroy/cleanup",
    "correlated-propagation": "propagate values using correlated branches",
    "deadargelim": "remove unused function arguments",
    "div-rem-pairs": "hoist/sink matching div and rem",
    "dse": "dead store elimination",
    "early-cse": "early common-subexpression elimination",
    "elim-avail-extern": "drop available_externally bodies after use",
    "float2int": "replace float-to-int conversion loops",
    "forceattrs": "add attributes requested on the command line",
    "function-attrs": "infer function attributes (readonly, nocapture, ...)",
    "globaldce": "delete unreferenced internal globals",
    "globalopt": "optimise global variables and constructors",
    "gvn": "global value numbering (CSE + load elimination)",
    "indvars": "canonicalise loop induction variables",
    "infer-alignment": "infer better alignment for memory ops",
    "inferattrs": "infer attributes from library declarations",
    "inject-tli-mappings": "attach TargetLibraryInfo vector mappings",
    "inline": "general inliner",
    "instcombine": "algebraic simplification of instructions",
    "instsimplify": "cheap instruction simplification (no new insts)",
    "ipsccp": "interprocedural sparse conditional constant propagation",
    "jump-threading": "thread a branch through a block that ends in a branch",
    "libcalls-shrinkwrap": "guard library calls with cheap pre-checks",
    "licm": "loop-invariant code motion",
    "loop-deletion": "delete loops with no side effects",
    "loop-distribute": "split a loop so part of it can vectorise",
    "loop-idiom": "replace idioms (memset/memcpy loops, ...)",
    "loop-instsimplify": "instsimplify inside a loop",
    "loop-load-elim": "eliminate redundant loop loads",
    "loop-rotate": "rotate the loop to create a do-while shape",
    "loop-simplifycfg": "simplifycfg on the loop nest",
    "loop-sink": "sink instructions into the loop if that is cheaper",
    "loop-unroll": "partial / runtime loop unroll",
    "loop-unroll-full": "fully unroll tiny constant-trip loops",
    "loop-vectorize": "widen a loop into vector instructions",
    "lower-constant-intrinsics": "expand llvm.objectsize and friends",
    "lower-expect": "turn llvm.expect into branch weights",
    "mem2reg": "promote allocas to SSA registers",
    "memcpyopt": "form memcpy/memset from load/store sequences",
    "mldst-motion": "merge loads/stores across diamond CFG",
    "move-auto-init": "move llvm.memset auto-init out of the hot path",
    "openmp-opt": "OpenMP-aware module optimisations",
    "openmp-opt-cgscc": "OpenMP-aware CGSCC optimisations",
    "reassociate": "reassociate expressions for better CSE/LICM",
    "rel-lookup-table-converter": "build relative lookup tables for switches",
    "rpo-function-attrs": "infer attributes in reverse post-order",
    "sccp": "sparse conditional constant propagation",
    "simple-loop-unswitch": "unswitch a loop on an invariant condition",
    "simplifycfg": "fold branches, merge blocks, flatten selects",
    "slp-vectorizer": "superword-level parallelism (straight-line vectors)",
    "speculative-execution": "hoist cheap ops above a branch",
    "sroa": "scalar replacement of aggregates",
    "tailcallelim": "turn tail calls into loops / mark tail",
    "vector-combine": "combine scalar/vector ops into cheaper vector forms",
}


def load_available(path):
    """Return the set of pass (not analysis) names known to this opt build."""
    names, keep = set(), False
    with open(path) as fh:
        for line in fh:
            stripped = line.strip()
            if stripped.endswith(":") and not stripped.startswith(" "):
                keep = stripped in PASS_SECTIONS
                continue
            if keep and stripped:
                names.add(stripped.split("<")[0].strip())
    return names


def flatten(pipeline):
    """Yield leaf pass names, in order, skipping adaptors."""
    out = []
    i, n = 0, len(pipeline)
    token = []
    angle = 0
    while i < n:
        ch = pipeline[i]
        if ch == "<":
            angle += 1
            token.append(ch)
        elif ch == ">":
            angle -= 1
            token.append(ch)
        elif angle > 0:
            token.append(ch)
        elif ch == "(":
            token = []                # name before '(' is an adaptor -> drop
        elif ch in "),":
            if token:
                out.append("".join(token).strip())
            token = []
        else:
            token.append(ch)
        i += 1
    if token:
        out.append("".join(token).strip())
    return [t for t in out if t]


def transformations(pipeline, available):
    result = []
    for tok in flatten(pipeline):
        base = tok.split("<")[0]
        if base in NON_TRANSFORM or tok in UNNAMEABLE or base in UNNAMEABLE:
            continue
        if base not in available:
            print(f"  note: unknown pass name skipped: {tok}", file=sys.stderr)
            continue
        result.append(base)
    return result


def positions(lst):
    d = defaultdict(list)
    for i, p in enumerate(lst, 1):
        d[p].append(i)
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--available", required=True)
    ap.add_argument("--latex", action="store_true")
    ap.add_argument("--ordered", action="store_true",
                    help="print the full ordered list per level")
    args = ap.parse_args()

    available = load_available(args.available)

    levels = OrderedDict()
    for path in args.files:
        m = re.search(r"O([0-3])", path)
        level = f"O{m.group(1)}" if m else path
        with open(path) as fh:
            levels[level] = transformations(fh.read().strip(), available)

    if args.ordered:
        for lv, lst in levels.items():
            print(f"\n=== -{lv}: {len(lst)} invocations, "
                  f"{len(set(lst))} distinct ===")
            for k, p in enumerate(lst, 1):
                print(f"{k:3d}. {p}")

    counts = {lv: Counter(l) for lv, l in levels.items()}
    allnames = sorted({p for l in levels.values() for p in l})
    pos = {lv: positions(l) for lv, l in levels.items()}

    print("\n--- invocation counts per pass ---")
    hdr = ["pass"] + [f"-{lv}" for lv in levels]
    rows = [hdr] + [[p] + [str(counts[lv][p]) for lv in levels]
                    for p in allnames]
    rows.append(["TOTAL invocations"] + [str(len(levels[lv])) for lv in levels])
    rows.append(["DISTINCT passes"] + [str(len(set(levels[lv]))) for lv in levels])
    w = [max(len(r[i]) for r in rows) for i in range(len(hdr))]
    for k, r in enumerate(rows):
        print("  ".join(c.ljust(w[0]) if i == 0 else c.rjust(w[i])
                        for i, c in enumerate(r)))
        if k == 0:
            print("-" * (sum(w) + 2 * len(w)))

    sets = {lv: set(l) for lv, l in levels.items()}
    common = set.intersection(*sets.values()) if sets else set()
    print("\ncommon to all four levels:", ", ".join(sorted(common)) or "(none)")
    seen = set(sets.get("O0", set()))
    first = {}
    for lv in ("O1", "O2", "O3"):
        if lv in sets:
            new = sets[lv] - seen
            first[lv] = new
            print(f"first introduced at -{lv}:", ", ".join(sorted(new)) or "(none)")
            seen |= sets[lv]

    count_changed = [p for p in allnames
                     if len({counts[lv][p] for lv in levels}) > 1]
    print("\ncount changes across levels:", ", ".join(count_changed) or "(none)")

    pos_changed = []
    for p in allnames:
        seqs = [tuple(pos[lv][p]) for lv in levels]
        if len(set(seqs)) > 1:
            pos_changed.append(p)
    print("position changes across levels:", ", ".join(pos_changed) or "(none)")

    if args.latex:
        print("\n% ---- LaTeX: summary ----")
        print("\\begin{tabular}{lrr}")
        print("\\hline")
        print("level & invocations & distinct \\\\")
        print("\\hline")
        for lv, lst in levels.items():
            print(f"\\texttt{{-{lv}}} & {len(lst)} & {len(set(lst))} \\\\")
        print("\\hline")
        print("\\end{tabular}")

        print("\n% ---- LaTeX: ordered lists (one box per level) ----")
        for lv, lst in levels.items():
            print("\\subsection*{\\texttt{-%s}}" % lv)
            print()
            print("\\begin{lstlisting}[language={}]")
            for i, p in enumerate(lst, 1):
                print("%d. %s" % (i, p))
            print("\\end{lstlisting}")
            print()

        print("\n% ---- LaTeX: shared descriptions + counts ----")
        print("\\begin{longtable}{lp{6.2cm}rrrr}")
        print("\\hline")
        print("pass & description & "
              + " & ".join("\\texttt{-%s}" % lv for lv in levels)
              + " \\\\")
        print("\\hline")
        print("\\endfirsthead")
        print("\\hline")
        print("pass & description & "
              + " & ".join("\\texttt{-%s}" % lv for lv in levels)
              + " \\\\")
        print("\\hline")
        print("\\endhead")
        for p in allnames:
            desc = DESCRIPTIONS.get(p, "").replace("_", "\\_")
            print("\\texttt{%s} & %s & %s \\\\" % (
                p.replace("_", "\\_"),
                desc,
                " & ".join(str(counts[lv][p]) for lv in levels)))
        print("\\hline")
        print("\\end{longtable}")


if __name__ == "__main__":
    main()
