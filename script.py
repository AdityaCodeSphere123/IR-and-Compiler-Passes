#!/usr/bin/env python3
"""
Count basic blocks and LLVM instruction opcodes, one row per (function, -O level).

Parses instructions properly:
  * only lines inside a  define ... { ... }  body are considered
  * comments (everything after an unquoted ';') are stripped first, so
    the  "; preds = %21, %0"  annotations cannot be miscounted
  * label lines, metadata lines (!0 = ...), declare/attributes lines are skipped
  * the opcode is taken from its syntactic position -- after the optional
    "%result = " and after any tail/musttail/notail modifier -- and is then
    checked against the real LLVM opcode set, so substring hits such as
    "or" inside "store" are impossible
  * basic blocks are counted as terminator instructions, since every basic
    block ends in exactly one; this is cross-checked against the label count

Usage:
    python3 count_opcodes.py opcodes.O0.ll opcodes.O1.ll opcodes.O2.ll opcodes.O3.ll
    python3 count_opcodes.py --latex *.ll        # LaTeX tabular for the report
"""

import re
import sys
from collections import Counter, OrderedDict

# ---------------------------------------------------------------- opcode set
TERMINATORS = {
    "ret", "br", "switch", "indirectbr", "invoke", "callbr", "resume",
    "catchswitch", "catchret", "cleanupret", "unreachable",
}

OPCODES = TERMINATORS | {
    # unary / binary arithmetic
    "fneg",
    "add", "fadd", "sub", "fsub", "mul", "fmul",
    "udiv", "sdiv", "fdiv", "urem", "srem", "frem",
    # bitwise
    "shl", "lshr", "ashr", "and", "or", "xor",
    # vector
    "extractelement", "insertelement", "shufflevector",
    # aggregate
    "extractvalue", "insertvalue",
    # memory / addressing
    "alloca", "load", "store", "fence", "cmpxchg", "atomicrmw",
    "getelementptr",
    # conversion
    "trunc", "zext", "sext", "fptrunc", "fpext",
    "fptoui", "fptosi", "uitofp", "sitofp",
    "ptrtoint", "inttoptr", "bitcast", "addrspacecast",
    # other
    "icmp", "fcmp", "phi", "select", "freeze", "call", "va_arg",
    "landingpad", "catchpad", "cleanuppad",
}

CALL_MODIFIERS = {"tail", "musttail", "notail"}

DEFINE_RE = re.compile(r"^define\b.*?@\"?([A-Za-z0-9_.$\-]+)\"?\s*\(")
LABEL_RE = re.compile(r"^[%A-Za-z0-9_.$\-]+:")
ASSIGN_RE = re.compile(r"^%[\"%A-Za-z0-9_.$\-]+\s*=\s*(.*)$")


def strip_comment(line):
    """Remove a trailing ';' comment, ignoring semicolons inside "..." strings."""
    out, in_string, i = [], False, 0
    while i < len(line):
        ch = line[i]
        if ch == '"' and (i == 0 or line[i - 1] != "\\"):
            in_string = not in_string
        elif ch == ";" and not in_string:
            break
        out.append(ch)
        i += 1
    return "".join(out).strip()


def opcode_of(line):
    """Return the instruction opcode on this line, or None if it isn't one."""
    text = strip_comment(line)
    if not text or text in ("{", "}"):
        return None
    if LABEL_RE.match(text):          # basic block label
        return None
    if text[0] in "!@#":              # metadata, globals, attribute groups
        return None

    m = ASSIGN_RE.match(text)         # drop "%result = " if present
    if m:
        text = m.group(1)

    tokens = text.split()
    if not tokens:
        return None
    head = tokens[0]
    if head in CALL_MODIFIERS:        # "tail call ..." -> "call"
        head = tokens[1] if len(tokens) > 1 else head

    return head if head in OPCODES else None


def parse(path):
    """Yield (function_name, block_count, Counter_of_opcodes) for one .ll file."""
    results = []
    fname, body, depth = None, [], 0

    with open(path) as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if fname is None:
                m = DEFINE_RE.match(line)
                if m:
                    fname, body, depth = m.group(1), [], line.count("{")
                continue

            depth += line.count("{") - line.count("}")
            if depth <= 0:                       # function body finished
                counts = Counter()
                labels = 0
                for bl in body:
                    text = strip_comment(bl)
                    if LABEL_RE.match(text):
                        labels += 1
                    op = opcode_of(bl)
                    if op:
                        counts[op] += 1
                blocks = sum(counts[t] for t in TERMINATORS)
                # Sanity check.  The entry block may or may not carry an
                # explicit label (it does under -fno-discard-value-names),
                # so either labels or labels+1 is consistent.
                if blocks not in (labels, labels + 1):
                    print(f"  note: {fname} in {path}: {blocks} terminators vs "
                          f"{labels} labels", file=sys.stderr)
                results.append((fname, blocks, counts))
                fname = None
            else:
                body.append(line)
    return results


def level_of(path):
    m = re.search(r"O([0-3s z]|fast)\b|\.O([0-3])\.", path)
    m2 = re.search(r"O([0-3])", path)
    return f"-O{m2.group(1)}" if m2 else path


def main():
    args = [a for a in sys.argv[1:] if a != "--latex"]
    latex = "--latex" in sys.argv
    if not args:
        print(__doc__)
        return

    rows = []
    for path in args:
        for fname, blocks, counts in parse(path):
            rows.append((fname, level_of(path), blocks, counts))

    # only show opcodes that actually occur somewhere
    seen = OrderedDict()
    for _, _, _, c in rows:
        for op in c:
            seen[op] = True
    cols = sorted(seen, key=lambda o: (o not in TERMINATORS, o))

    header = ["function", "opt", "blocks"] + cols
    table = [header] + [
        [fn, lv, str(bb)] + [str(c.get(op, 0)) for op in cols]
        for fn, lv, bb, c in sorted(rows, key=lambda r: (r[0], r[1]))
    ]

    if latex:
        print("\\begin{tabular}{ll" + "r" * (len(cols) + 1) + "}")
        print("\\hline")
        print(" & ".join("\\texttt{%s}" % h for h in header) + " \\\\")
        print("\\hline")
        for row in table[1:]:
            print(" & ".join(row) + " \\\\")
        print("\\hline")
        print("\\end{tabular}")
    else:
        widths = [max(len(r[i]) for r in table) for i in range(len(header))]
        for n, row in enumerate(table):
            print("  ".join(cell.rjust(widths[i]) for i, cell in enumerate(row)))
            if n == 0:
                print("-" * (sum(widths) + 2 * len(widths)))


if __name__ == "__main__":
    main()
