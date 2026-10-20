import itertools
import random
import unittest

from cdclsat import Solver, check_rup_proof, parse_dimacs, to_dimacs, verify_model
from cdclsat.generators import graph_coloring, n_queens, pigeonhole, random_ksat
from cdclsat.solver import luby


def brute(n, clauses):
    for bits in itertools.product([False, True], repeat=n):
        m = {i + 1: bits[i] for i in range(n)}
        if verify_model(clauses, m):
            return True
    return False


def run(n, clauses):
    proof = []
    s = Solver(n, proof=proof)
    for c in clauses:
        s.add_clause(c)
    sat, model = s.solve()
    return sat, model, proof, s


class Tests(unittest.TestCase):
    def test_luby(self):
        self.assertEqual([luby(i) for i in range(1, 16)], [1, 1, 2, 1, 1, 2, 4, 1, 1, 2, 1, 1, 2, 4, 8])

    def test_dimacs_roundtrip(self):
        n, cl = parse_dimacs("c hi\np cnf 3 2\n1 -2\n0 3 0\n")
        self.assertEqual((n, cl), (3, [[1, -2], [3]]))
        self.assertEqual(parse_dimacs(to_dimacs(n, cl)), (n, cl))

    def test_trivial(self):
        self.assertTrue(run(1, [[1]])[0])
        self.assertFalse(run(1, [[1], [-1]])[0])
        self.assertFalse(run(0, [[]])[0])

    def test_matches_bruteforce_and_proofs(self):
        for seed in range(300):
            n = random.Random(seed).randint(3, 11)
            m = int(n * random.Random(seed + 7).uniform(3.0, 5.5))
            n, cl = random_ksat(n, m, 3, seed)
            sat, model, proof, _ = run(n, cl)
            self.assertEqual(sat, brute(n, cl), seed)
            if sat:
                self.assertTrue(verify_model(cl, model))
            else:
                ok, msg = check_rup_proof(cl, proof)
                self.assertTrue(ok, (seed, msg))

    def test_pigeonhole_unsat_with_proof(self):
        n, cl = pigeonhole(5)
        sat, _, proof, s = run(n, cl)
        self.assertFalse(sat)
        self.assertTrue(check_rup_proof(cl, proof)[0])

    def test_queens(self):
        for k, expect in [(4, True), (6, True), (3, False)]:
            n, cl = n_queens(k)
            sat, model, proof, _ = run(n, cl)
            self.assertEqual(sat, expect)
            if sat:
                self.assertTrue(verify_model(cl, model))
                self.assertEqual(sum(model[v] for v in range(1, n + 1)), k)

    def test_coloring(self):
        k4 = list(itertools.combinations(range(4), 2))
        self.assertFalse(run(*graph_coloring(k4, 4, 3))[0])
        self.assertTrue(run(*graph_coloring(k4, 4, 4))[0])

    def test_larger_random_with_restarts_and_reduction(self):
        n, cl = random_ksat(90, 385, 3, seed=5)
        sat, model, proof, s = run(n, cl)
        if sat:
            self.assertTrue(verify_model(cl, model))
        else:
            self.assertTrue(check_rup_proof(cl, proof)[0])

    def test_bad_proof_rejected(self):
        cl = [[1, 2], [-1, 2]]
        self.assertFalse(check_rup_proof(cl, [("a", [-2]), ("a", [])])[0])


if __name__ == "__main__":
    unittest.main()
