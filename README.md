# cdcl-sat-solver

A conflict-driven clause learning (CDCL) SAT solver in pure Python with zero dependencies, plus an independent DRUP proof checker so every UNSAT answer can be verified rather than trusted.

## Why

SAT solving underpins formal verification, planning, package resolution and scheduling. Modern solvers are built from a handful of ideas that are easy to get subtly wrong. This project implements them end to end and, importantly, checks itself: SAT answers are validated against the original formula, and UNSAT answers emit a proof that a separate, deliberately naive checker replays.

## What is inside

- Two-watched-literal unit propagation with lazy removal of deleted clauses
- First-UIP conflict analysis and recursive clause minimisation
- VSIDS branching (lazy binary heap, activity rescaling) with phase saving
- Luby-sequence restarts
- LBD-guided learned clause database reduction (glue clauses are kept)
- DRUP proof logging (clause additions and deletions)
- `cdclsat.proof.check_rup_proof`: reverse unit propagation checker sharing no code with the solver
- DIMACS reader/writer, benchmark generators (random 3-SAT, pigeonhole, N-queens, graph colouring), and a CLI

## Run it

Requires Python 3.8+.

```
python -m cdclsat problem.cnf --check --stats
python -m cdclsat problem.cnf --proof out.drat      # write DRUP proof when UNSAT
python -m unittest discover -s tests                # run the tests
```

Exit codes follow SAT convention: 0 for SAT, 20 for UNSAT. Output uses the standard `s SATISFIABLE` / `v ...` format.

As a library:

```python
from cdclsat import Solver, check_rup_proof
from cdclsat.generators import pigeonhole

n, clauses = pigeonhole(6)
proof = []
s = Solver(n, proof=proof)
for c in clauses:
    s.add_clause(c)
sat, model = s.solve()
print(sat, check_rup_proof(clauses, proof))   # False (True, 'empty clause derived ...')
```

## Design and testing notes

- Literals are encoded as `2*v` / `2*v+1` internally so negation is `l ^ 1` and arrays index directly by literal.
- Learned clause minimisation walks reason clauses with memoisation; a literal is dropped when its reason is entirely covered by the learned clause, level 0, or other redundant literals.
- Clause deletion is lazy: deleted clauses leave an `alive` set and are skipped when encountered in watch lists, and clauses that are the reason for a current assignment are never deleted.
- Tests cross-check 300 random small formulas against brute force enumeration, verify every SAT model against the formula, and replay every UNSAT proof through the independent checker. They also cover the Luby sequence, DIMACS round trips, pigeonhole, queens, colouring, and confirm the checker rejects a bogus proof.
- Rough numbers on a laptop: PHP(7 holes) refuted in about 2s (9k conflicts); 150 variable random 3-SAT near the threshold in a fraction of a second. Pure Python is of course far slower than MiniSat or CaDiCaL; the goal is clarity and verifiability.

## Layout

```
cdclsat/solver.py      the solver
cdclsat/proof.py       model checking and RUP proof checker
cdclsat/dimacs.py      CNF I/O
cdclsat/generators.py  benchmark families
cdclsat/cli.py         command line
tests/test_cdclsat.py  unit and property style tests
```

## License

MIT
