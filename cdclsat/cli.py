"""Command line: python -m cdclsat file.cnf [--proof out.drat] [--check]"""
import argparse
import sys
import time

from .dimacs import parse_dimacs
from .proof import check_rup_proof, verify_model
from .solver import Solver


def main(argv=None):
    ap = argparse.ArgumentParser(prog="cdclsat", description="CDCL SAT solver")
    ap.add_argument("cnf", help="DIMACS CNF file ('-' for stdin)")
    ap.add_argument("--proof", help="write DRUP proof here when UNSAT")
    ap.add_argument("--check", action="store_true", help="verify the answer independently")
    ap.add_argument("--stats", action="store_true")
    a = ap.parse_args(argv)
    text = sys.stdin.read() if a.cnf == "-" else open(a.cnf).read()
    n, clauses = parse_dimacs(text)
    proof = [] if (a.proof or a.check) else None
    s = Solver(n, proof=proof)
    t = time.time()
    for c in clauses:
        s.add_clause(c)
    sat, model = s.solve()
    dt = time.time() - t
    if sat:
        print("s SATISFIABLE")
        print("v " + " ".join(str(v if val else -v) for v, val in sorted(model.items())) + " 0")
        if a.check:
            print("c model check:", "OK" if verify_model(clauses, model) else "FAILED")
    else:
        print("s UNSATISFIABLE")
        if a.proof:
            with open(a.proof, "w") as f:
                for kind, lits in proof:
                    f.write(("d " if kind == "d" else "") + " ".join(map(str, lits + [0])) + "\n")
        if a.check:
            ok, msg = check_rup_proof(clauses, proof)
            print("c proof check:", "OK" if ok else "FAILED", "-", msg)
    if a.stats:
        print("c time %.3fs %s" % (dt, s.stats))
    return 0 if sat else 20


if __name__ == "__main__":
    sys.exit(main())
