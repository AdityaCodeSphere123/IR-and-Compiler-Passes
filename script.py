import sys

terms = {"ret", "br", "switch", "indirectbr", "invoke", "callbr", "resume", "catchswitch", "catchret", "cleanupret", "unreachable"}
ops = terms | {"fneg", "add", "fadd", "sub", "fsub", "mul", "fmul", "udiv", "sdiv", "fdiv", "urem", "srem", "frem", "shl", "lshr", "ashr", "and", "or", "xor", "extractelement", "insertelement", "shufflevector", "extractvalue", "insertvalue", "alloca", "load", "store", "fence", "cmpxchg", "atomicrmw", "getelementptr", "trunc", "zext", "sext", "fptrunc", "fpext", "fptoui", "fptosi", "uitofp", "sitofp", "ptrtoint", "inttoptr", "bitcast", "addrspacecast", "icmp", "fcmp", "phi", "select", "freeze", "call", "va_arg", "landingpad", "catchpad", "cleanuppad"}
cmods = {"tail", "musttail", "notail"}

args = []
for a in sys.argv:
    args.append(a)

narg = []
for i in range(len(args)):
    if i > 0:
        narg.append(args[i])
args = narg

rows = []

for path in args:
    lvl = path
    for o in ["O0", "O1", "O2", "O3", "Os", "Oz", "Ofast"]:
        fnd = False
        for i in range(len(path) - len(o) + 1):
            mtc = True
            for j in range(len(o)):
                if path[i+j] != o[j]:
                    mtc = False
                    break
            if mtc:
                fnd = True
                break
        if fnd:
            if o == "Ofast":
                lvl = "-Ofast"
            else:
                lvl = "-" + o[0:2]
            break

    fname = None
    body = []
    depth = 0

    fh = open(path)
    lines = []
    for raw in fh:
        lines.append(raw)
    fh.close()

    for raw in lines:
        line = raw
        while len(line) > 0 and (line[-1] == "\n" or line[-1] == "\r"):
            line = line[:-1]

        if fname is None:
            if len(line) > 6 and line[0:6] == "define":
                atidx = -1
                for i in range(len(line)):
                    if line[i] == "@":
                        atidx = i
                        break
                if atidx != -1:
                    paren = -1
                    for i in range(atidx, len(line)):
                        if line[i] == "(":
                            paren = i
                            break
                    if paren != -1:
                        n = line[atidx+1:paren]
                        while len(n) > 0 and (n[0] == " " or n[0] == '"'):
                            n = n[1:]
                        while len(n) > 0 and (n[-1] == " " or n[-1] == '"'):
                            n = n[:-1]
                        fname = n
                        body = []
                        c = 0
                        for ch in line:
                            if ch == "{": 
                                c += 1
                        depth = c
            continue

        cin = 0
        cout = 0
        for ch in line:
            if ch == "{": cin += 1
            if ch == "}": cout += 1
        depth += (cin - cout)

        if depth <= 0:
            cnts = {}
            lbls = 0
            for bl in body:
                out = []
                instr = False
                i = 0
                while i < len(bl):
                    ch = bl[i]
                    if ch == '"':
                        if i == 0 or bl[i-1] != "\\":
                            instr = not instr
                    elif ch == ";" and not instr:
                        break
                    out.append(ch)
                    i += 1
                
                txt = ""
                for ch in out: 
                    txt += ch
                
                start = 0
                while start < len(txt) and (txt[start] == " " or txt[start] == "\t"):
                    start += 1
                end = len(txt) - 1
                while end >= start and (txt[end] == " " or txt[end] == "\t"):
                    end -= 1
                
                if start > end:
                    txt = ""
                else:
                    txt = txt[start:end+1]

                if txt == "" or txt == "{" or txt == "}":
                    continue
                
                if txt[-1] == ":":
                    lbls += 1
                    continue
                if txt[0] == "!" or txt[0] == "@" or txt[0] == "#":
                    continue
                
                if txt[0] == "%":
                    eq = -1
                    for i in range(len(txt)):
                        if txt[i] == "=":
                            eq = i
                            break
                    if eq != -1:
                        txt = txt[eq+1:]
                        s = 0
                        while s < len(txt) and (txt[s] == " " or txt[s] == "\t"):
                            s += 1
                        txt = txt[s:]

                toks = []
                cur = ""
                for ch in txt:
                    if ch == " " or ch == "\t":
                        if cur != "":
                            toks.append(cur)
                            cur = ""
                    else:
                        cur += ch
                if cur != "":
                    toks.append(cur)

                if len(toks) == 0:
                    continue
                head = toks[0]
                if head in cmods:
                    if len(toks) > 1:
                        head = toks[1]
                
                if head in ops:
                    if head not in cnts:
                        cnts[head] = 0
                    cnts[head] += 1
            
            blks = 0
            for t in terms:
                if t in cnts:
                    blks += cnts[t]
            
            if blks != lbls and blks != (lbls + 1):
                sys.stderr.write("  note: " + fname + " in " + path + ": " + str(blks) + " terminators vs " + str(lbls) + " labels\n")
            
            rows.append((fname, lvl, blks, cnts))
            fname = None
        else:
            body.append(line)

seen = {}
for r in rows:
    for k in r[3]:
        seen[k] = True

cols = []
for k in seen:
    cols.append(k)

for i in range(len(cols)):
    for j in range(len(cols)-1-i):
        c1 = cols[j]
        c2 = cols[j+1]
        v1t = 0 if c1 in terms else 1
        v2t = 0 if c2 in terms else 1
        swap = False
        if v1t > v2t:
            swap = True
        elif v1t == v2t:
            if c1 > c2:
                swap = True
        if swap:
            tmp = cols[j]
            cols[j] = cols[j+1]
            cols[j+1] = tmp

for i in range(len(rows)):
    for j in range(len(rows)-1-i):
        r1 = rows[j]
        r2 = rows[j+1]
        swap = False
        if r1[0] > r2[0]:
            swap = True
        elif r1[0] == r2[0]:
            if r1[1] > r2[1]:
                swap = True
        if swap:
            tmp = rows[j]
            rows[j] = rows[j+1]
            rows[j+1] = tmp

head = ["function", "opt", "blocks"]
for c in cols:
    head.append(c)

tab = [head]
for r in rows:
    rr = [r[0], r[1], str(r[2])]
    for c in cols:
        val = 0
        if c in r[3]:
            val = r[3][c]
        rr.append(str(val))
    tab.append(rr)

wids = []
for i in range(len(head)):
    mw = 0
    for ro in tab:
        l = len(ro[i])
        if l > mw:
            mw = l
    wids.append(mw)

for n in range(len(tab)):
    ro = tab[n]
    s = ""
    for i in range(len(ro)):
        cell = ro[i]
        pad = ""
        for _ in range(wids[i] - len(cell)):
            pad += " "
        s += pad + cell
        if i < len(ro) - 1:
            s += "  "
    print(s)
    if n == 0:
        tot = 0
        for w in wids:
            tot += w
        tot += 2 * len(wids)
        ln = ""
        for _ in range(tot):
            ln += "-"
        print(ln)
