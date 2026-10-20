"""DIMACS CNF reading and writing. Literals are non-zero ints, negative = negated."""


def parse_dimacs(text):
    """Return (num_vars, clauses). Tolerates comments and clauses spanning lines."""
    num_vars = 0
    clauses = []
    cur = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line[0] == "c":
            continue
        if line[0] == "%":
            break
        if line[0] == "p":
            parts = line.split()
            if len(parts) < 4 or parts[1] != "cnf":
                raise ValueError("bad problem line: %r" % line)
            num_vars = int(parts[2])
            continue
        for tok in line.split():
            v = int(tok)
            if v == 0:
                clauses.append(cur)
                cur = []
            else:
                cur.append(v)
                num_vars = max(num_vars, abs(v))
    if cur:
        clauses.append(cur)
    return num_vars, clauses


def to_dimacs(num_vars, clauses):
    out = ["p cnf %d %d" % (num_vars, len(clauses))]
    for c in clauses:
        out.append(" ".join(map(str, c)) + " 0")
    return "\n".join(out) + "\n"
