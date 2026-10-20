"""Conflict-driven clause learning SAT solver.

Features: two-watched-literal propagation, first-UIP learning, recursive
clause minimisation, VSIDS with a lazy binary heap, phase saving, Luby
restarts, LBD-guided learned clause deletion, and proof (DRUP) logging.

Internal literal encoding: variable v (1-based) -> positive lit 2*v, negative 2*v+1.
"""
import heapq

UNDEF, TRUE, FALSE = 0, 1, -1


def _lit(x):
    return 2 * x if x > 0 else -2 * x + 1


def _ext(l):
    return (l >> 1) if not (l & 1) else -(l >> 1)


def luby(i):
    """i-th element (1-based) of the Luby sequence 1,1,2,1,1,2,4,..."""
    k = 1
    while (1 << k) - 1 < i:
        k += 1
    while True:
        if i == (1 << k) - 1:
            return 1 << (k - 1)
        i -= (1 << (k - 1)) - 1
        k = 1
        while (1 << k) - 1 < i:
            k += 1


class Solver:
    def __init__(self, num_vars=0, proof=None, restart_base=100, seed_phase=False):
        self.n = 0
        self.proof = proof            # list to which ('a', clause) / ('d', clause) are appended
        self.restart_base = restart_base
        self.clauses = []             # clause objects: lists of internal lits; [0],[1] watched
        self.learnts = []
        self.lbd = {}                 # id(clause) -> lbd
        self.alive = set()
        self.watches = [[], []]
        self.assign = [UNDEF]
        self.level = [0]
        self.reason = [None]
        self.phase = [False]
        self.activity = [0.0]
        self.trail = []
        self.trail_lim = []
        self.qhead = 0
        self.var_inc = 1.0
        self.heap = []
        self.ok = True
        self.stats = {"conflicts": 0, "decisions": 0, "propagations": 0, "restarts": 0, "learned": 0, "deleted": 0}
        self.ensure_vars(num_vars)

    # -- setup ---------------------------------------------------------
    def ensure_vars(self, n):
        while self.n < n:
            self.n += 1
            self.assign.append(UNDEF)
            self.level.append(0)
            self.reason.append(None)
            self.phase.append(False)
            self.activity.append(0.0)
            self.watches.extend(([], []))
            heapq.heappush(self.heap, (0.0, self.n))

    def _val(self, l):
        a = self.assign[l >> 1]
        if a == UNDEF:
            return UNDEF
        return a if not (l & 1) else -a

    def add_clause(self, ext_lits):
        """Add an original clause (external ints). Returns False if trivially UNSAT."""
        if not self.ok:
            return False
        if ext_lits:
            self.ensure_vars(max(abs(x) for x in ext_lits))
        lits = sorted(set(_lit(x) for x in ext_lits))
        if any((l ^ 1) in lits for l in lits):
            return True  # tautology
        if not lits:
            self.ok = False
            return False
        if len(lits) == 1:
            v = self._val(lits[0])
            if v == FALSE:
                self.ok = False
                self._log("a", [])
                return False
            if v == UNDEF:
                self._enqueue(lits[0], None)
                if self._propagate() is not None:
                    self.ok = False
                    self._log("a", [])
                    return False
            return True
        self._attach(lits)
        self.clauses.append(lits)
        self.alive.add(id(lits))
        return True

    def _attach(self, c):
        self.watches[c[0]].append(c)
        self.watches[c[1]].append(c)

    def _log(self, kind, clause):
        if self.proof is not None:
            self.proof.append((kind, [_ext(l) for l in clause]))

    # -- core ----------------------------------------------------------
    def _enqueue(self, l, reason):
        v = l >> 1
        self.assign[v] = TRUE if not (l & 1) else FALSE
        self.level[v] = len(self.trail_lim)
        self.reason[v] = reason
        self.trail.append(l)

    def _propagate(self):
        """Unit propagation. Returns a conflicting clause or None."""
        while self.qhead < len(self.trail):
            p = self.trail[self.qhead]
            self.qhead += 1
            self.stats["propagations"] += 1
            false_lit = p ^ 1
            ws = self.watches[false_lit]
            i = j = 0
            n = len(ws)
            while i < n:
                c = ws[i]
                i += 1
                if id(c) not in self.alive:
                    continue  # lazily drop deleted clauses
                if c[0] == false_lit:
                    c[0], c[1] = c[1], c[0]
                first = c[0]
                if self._val(first) == TRUE:
                    ws[j] = c
                    j += 1
                    continue
                found = False
                for k in range(2, len(c)):
                    if self._val(c[k]) != FALSE:
                        c[1], c[k] = c[k], c[1]
                        self.watches[c[1]].append(c)
                        found = True
                        break
                if found:
                    continue
                ws[j] = c
                j += 1
                if self._val(first) == FALSE:
                    while i < n:
                        ws[j] = ws[i]
                        j += 1
                        i += 1
                    del ws[j:]
                    self.qhead = len(self.trail)
                    return c
                self._enqueue(first, c)
            del ws[j:]
        return None

    def _bump(self, v):
        self.activity[v] += self.var_inc
        if self.activity[v] > 1e100:
            for u in range(1, self.n + 1):
                self.activity[u] *= 1e-100
            self.var_inc *= 1e-100
            self.heap = [(-self.activity[u], u) for u in range(1, self.n + 1) if self.assign[u] == UNDEF]
            heapq.heapify(self.heap)
        elif self.assign[v] == UNDEF:
            heapq.heappush(self.heap, (-self.activity[v], v))

    def _analyze(self, confl):
        """First-UIP learning. Returns (learned clause, backjump level)."""
        seen = set()
        learnt = [None]
        counter = 0
        p = None
        idx = len(self.trail) - 1
        cur = len(self.trail_lim)
        c = confl
        while True:
            for q in c:
                v = q >> 1
                if p is not None and v == (p >> 1):
                    continue
                if v not in seen and self.level[v] > 0:
                    seen.add(v)
                    self._bump(v)
                    if self.level[v] >= cur:
                        counter += 1
                    else:
                        learnt.append(q)
            while (self.trail[idx] >> 1) not in seen:
                idx -= 1
            p = self.trail[idx]
            idx -= 1
            c = self.reason[p >> 1]
            counter -= 1
            if counter == 0:
                break
        learnt[0] = p ^ 1
        learnt = self._minimize(learnt)
        if len(learnt) == 1:
            bt = 0
        else:
            m = max(range(1, len(learnt)), key=lambda i: self.level[learnt[i] >> 1])
            learnt[1], learnt[m] = learnt[m], learnt[1]
            bt = self.level[learnt[1] >> 1]
        return learnt, bt

    def _minimize(self, learnt):
        """Recursive clause minimisation: drop literals implied by the rest."""
        in_clause = set(l >> 1 for l in learnt)
        memo = {}

        def redundant(v):
            if v in memo:
                return memo[v]
            r = self.reason[v]
            if r is None:
                memo[v] = False
                return False
            memo[v] = False  # cycle guard (implication graph is acyclic anyway)
            for q in r:
                u = q >> 1
                if u == v or self.level[u] == 0 or u in in_clause:
                    continue
                if not redundant(u):
                    return False
            memo[v] = True
            return True

        return [learnt[0]] + [l for l in learnt[1:] if not redundant(l >> 1)]

    def _cancel_until(self, lvl):
        if len(self.trail_lim) <= lvl:
            return
        start = self.trail_lim[lvl]
        for l in reversed(self.trail[start:]):
            v = l >> 1
            self.phase[v] = not (l & 1)
            self.assign[v] = UNDEF
            self.reason[v] = None
            heapq.heappush(self.heap, (-self.activity[v], v))
        del self.trail[start:]
        del self.trail_lim[lvl:]
        self.qhead = len(self.trail)

    def _pick(self):
        while self.heap:
            _, v = heapq.heappop(self.heap)
            if self.assign[v] == UNDEF:
                return v
        return 0

    def _compute_lbd(self, c):
        return len(set(self.level[l >> 1] for l in c))

    def _reduce_db(self):
        locked = set(id(self.reason[l >> 1]) for l in self.trail if self.reason[l >> 1] is not None)
        cand = [c for c in self.learnts if len(c) > 2 and self.lbd.get(id(c), 99) > 2 and id(c) not in locked]
        cand.sort(key=lambda c: -self.lbd.get(id(c), 99))
        for c in cand[: len(cand) // 2]:
            self.alive.discard(id(c))
            self.lbd.pop(id(c), None)
            self._log("d", c)
            self.stats["deleted"] += 1
        self.learnts = [c for c in self.learnts if id(c) in self.alive]

    # -- public --------------------------------------------------------
    def solve(self, max_conflicts=None):
        """Return (True, model dict var->bool) or (False, None). None if budget exhausted."""
        if not self.ok:
            return False, None
        if self._propagate() is not None:
            self.ok = False
            self._log("a", [])
            return False, None
        restart_no = 1
        budget = luby(restart_no) * self.restart_base
        since = 0
        max_learnts = max(100, len(self.clauses) // 2)
        while True:
            confl = self._propagate()
            if confl is not None:
                self.stats["conflicts"] += 1
                since += 1
                if not self.trail_lim:
                    self._log("a", [])
                    self.ok = False
                    return False, None
                learnt, bt = self._analyze(confl)
                self._cancel_until(bt)
                self._log("a", learnt)
                self.stats["learned"] += 1
                if len(learnt) == 1:
                    self._enqueue(learnt[0], None)
                else:
                    self._attach(learnt)
                    self.learnts.append(learnt)
                    self.alive.add(id(learnt))
                    self.lbd[id(learnt)] = self._compute_lbd(learnt)
                    self._enqueue(learnt[0], learnt)
                self.var_inc /= 0.95
                if max_conflicts is not None and self.stats["conflicts"] >= max_conflicts:
                    self._cancel_until(0)
                    return None, None
            else:
                if since >= budget:
                    self.stats["restarts"] += 1
                    restart_no += 1
                    budget = luby(restart_no) * self.restart_base
                    since = 0
                    self._cancel_until(0)
                    continue
                if len(self.learnts) - len(self.trail) >= max_learnts:
                    self._reduce_db()
                    max_learnts = int(max_learnts * 1.1) + 10
                v = self._pick()
                if v == 0:
                    model = {i: self.assign[i] == TRUE for i in range(1, self.n + 1)}
                    self._cancel_until(0)
                    return True, model
                self.stats["decisions"] += 1
                self.trail_lim.append(len(self.trail))
                self._enqueue(2 * v + (0 if self.phase[v] else 1), None)


def solve(clauses, num_vars=0, proof=None):
    """Convenience wrapper: returns (sat, model_or_None, solver)."""
    s = Solver(num_vars, proof=proof)
    for c in clauses:
        s.add_clause(c)
    sat, model = s.solve()
    return sat, model, s
