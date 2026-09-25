import math


class VectorEngine:
    def __init__(self):
        self.dim = None
        self.vectors = {}

    def set_dimension(self, dim):
        if dim not in (2, 3):
            raise ValueError("dimension must be 2 or 3")
        self.dim = dim
        self.vectors = {}

    _VALID_NAMES = ("VctA", "VctB", "VctC", "VctD")

    def store_vector(self, name, components):
        if name not in self._VALID_NAMES:
            raise ValueError("name must be VctA, VctB, VctC, or VctD")
        if self.dim is None:
            raise ValueError("dimension has not been set")
        comps = list(components)
        if len(comps) != self.dim:
            raise ValueError("component count must match dimension")
        self.vectors[name] = comps

    def get_vector(self, name):
        if name not in self.vectors:
            raise KeyError(name)
        return list(self.vectors[name])

    def _require(self, name):
        if name not in self.vectors:
            raise KeyError(name)
        return self.vectors[name]

    def add(self, a, b):
        va = self._require(a)
        vb = self._require(b)
        return [x + y for x, y in zip(va, vb)]

    def subtract(self, a, b):
        va = self._require(a)
        vb = self._require(b)
        return [x - y for x, y in zip(va, vb)]

    def scalar_multiply(self, name, scalar):
        v = self._require(name)
        return [scalar * c for c in v]

    def magnitude(self, name):
        v = self._require(name)
        return math.sqrt(sum(c * c for c in v))

    def unit_vector(self, name):
        mag = self.magnitude(name)
        if mag == 0:
            raise ValueError("cannot compute unit vector of zero vector")
        v = self._require(name)
        return [c / mag for c in v]

    def dot_product(self, a, b):
        va = self._require(a)
        vb = self._require(b)
        return sum(x * y for x, y in zip(va, vb))

    def cross_product(self, a, b):
        if self.dim != 3:
            raise ValueError("cross product requires dimension 3")
        va = self._require(a)
        vb = self._require(b)
        ax, ay, az = va
        bx, by, bz = vb
        return [ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx]

    def angle_between(self, a, b):
        mag_a = self.magnitude(a)
        mag_b = self.magnitude(b)
        if mag_a == 0 or mag_b == 0:
            raise ValueError("cannot compute angle with zero vector")
        dot = self.dot_product(a, b)
        ratio = dot / (mag_a * mag_b)
        ratio = max(-1.0, min(1.0, ratio))
        return math.acos(ratio)

    def reset(self):
        self.dim = None
        self.vectors = {}

    def get_state(self):
        return {
            "dim": self.dim,
            "vectors": {k: list(v) for k, v in self.vectors.items()},
        }