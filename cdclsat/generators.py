"""Benchmark instance generators."""
import random
from itertools import combinations


def random_ksat(n, m, k=3, seed=0):
    rng = random.Random(seed)
    cls = []
    for _ in range(m):
        vs = rng.sample(range(1, n + 1), k)
        cls.append([v if rng.random() < 0.5 else -v for v in vs])
    return n, cls


def pigeonhole(holes):
    """PHP: holes+1 pigeons into `holes` holes. Always UNSAT, exponentially hard for resolution."""
    pigeons = holes + 1
    var = lambda p, h: p * holes + h + 1
    cls = [[var(p, h) for h in range(holes)] for p in range(pigeons)]
    for h in range(holes):
        for p1, p2 in combinations(range(pigeons), 2):
            cls.append([-var(p1, h), -var(p2, h)])
    return pigeons * holes, cls


def n_queens(n):
    var = lambda r, c: r * n + c + 1
    cls = [[var(r, c) for c in range(n)] for r in range(n)]
    cells = [(r, c) for r in range(n) for c in range(n)]
    for (r1, c1), (r2, c2) in combinations(cells, 2):
        if r1 == r2 or c1 == c2 or abs(r1 - r2) == abs(c1 - c2):
            cls.append([-var(r1, c1), -var(r2, c2)])
    return n * n, cls


def graph_coloring(edges, nodes, colors):
    var = lambda v, c: v * colors + c + 1
    cls = [[var(v, c) for c in range(colors)] for v in range(nodes)]
    for v in range(nodes):
        for c1, c2 in combinations(range(colors), 2):
            cls.append([-var(v, c1), -var(v, c2)])
    for u, v in edges:
        for c in range(colors):
            cls.append([-var(u, c), -var(v, c)])
    return nodes * colors, cls
