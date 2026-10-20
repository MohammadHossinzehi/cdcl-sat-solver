"""Independent verification: model checking and a RUP (DRUP) proof checker."""


def verify_model(clauses, model):
    """True iff every clause has a literal satisfied by model (var -> bool)."""
    return all(any(model.get(abs(l), False) == (l > 0) for l in c) for c in clauses)


class _Prop:
    """Tiny, deliberately naive propagator (no watches) so it shares no code with the solver."""

    def __init__(self, clauses):
        self.clauses = {}
        self.counter = 0
        for c in clauses:
            self.add(c)

    def add(self, c):
        self.counter += 1
        self.clauses[self.counter] = tuple(c)
        return self.counter

    def refutes(self, assumptions):
        """Assume literals true, propagate; True if a conflict is reached."""
        val = {}
        for l in assumptions:
            if val.get(abs(l), l > 0) != (l > 0):
                return True
            val[abs(l)] = l > 0
        changed = True
        while changed:
            changed = False
            for c in self.clauses.values():
                unassigned = None
                n_un = 0
                sat = False
                for l in c:
                    x = val.get(abs(l))
                    if x is None:
                        n_un += 1
                        unassigned = l
                    elif x == (l > 0):
                        sat = True
                        break
                if sat:
                    continue
                if n_un == 0:
                    return True
                if n_un == 1:
                    val[abs(unassigned)] = unassigned > 0
                    changed = True
        return False


def check_rup_proof(clauses, proof):
    """Check a DRUP proof: each added clause must be RUP w.r.t. the live clause set,
    and the proof must derive the empty clause. Returns (ok, message)."""
    p = _Prop(clauses)
    index = {}
    for cid, c in p.clauses.items():
        index.setdefault(frozenset(c), []).append(cid)
    for step, (kind, lits) in enumerate(proof):
        if kind == "d":
            ids = index.get(frozenset(lits))
            if ids:
                p.clauses.pop(ids.pop(), None)
            continue
        if not p.refutes([-l for l in lits]):
            return False, "step %d: clause %s is not RUP" % (step, lits)
        if not lits:
            return True, "empty clause derived at step %d" % step
        cid = p.add(lits)
        index.setdefault(frozenset(lits), []).append(cid)
    return p.refutes([]), "proof ended without explicit empty clause" if not p.refutes([]) else "refuted by propagation"
