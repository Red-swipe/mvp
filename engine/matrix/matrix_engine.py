import copy


class MatrixEngineError(Exception):
    pass


class MatrixEngine:
    _VALID_NAMES = ("MatA", "MatB", "MatC", "MatD")
    _MAX_DIM = 4
    _PIVOT_EPS = 1e-15
    _SINGULAR_DET_EPS = 1e-10

    def __init__(self):
        self.matrices = {"MatA": None, "MatB": None, "MatC": None, "MatD": None}

    def _validate_name(self, name):
        if name not in self._VALID_NAMES:
            raise MatrixEngineError(f"Invalid matrix name: {name}")

    def _get_raw(self, name):
        self._validate_name(name)
        if self.matrices[name] is None:
            raise MatrixEngineError("Matrix not defined")
        return copy.deepcopy(self.matrices[name])

    def define_matrix(self, name, data):
        self._validate_name(name)
        rows = len(data)
        if rows < 1 or rows > self._MAX_DIM:
            raise MatrixEngineError("Dimension ERROR")
        cols = len(data[0])
        if cols < 1 or cols > self._MAX_DIM:
            raise MatrixEngineError("Dimension ERROR")
        if any(len(row) != cols for row in data):
            raise MatrixEngineError("Dimension ERROR")
        self.matrices[name] = copy.deepcopy(data)

    def get_matrix(self, name):
        return self._get_raw(name)

    def dimensions(self, name):
        mat = self._get_raw(name)
        return (len(mat), len(mat[0]))

    def add(self, name_a, name_b):
        a = self._get_raw(name_a)
        b = self._get_raw(name_b)
        if len(a) != len(b) or len(a[0]) != len(b[0]):
            raise MatrixEngineError("Dimension ERROR")
        return [
            [a[i][j] + b[i][j] for j in range(len(a[0]))]
            for i in range(len(a))
        ]

    def subtract(self, name_a, name_b):
        a = self._get_raw(name_a)
        b = self._get_raw(name_b)
        if len(a) != len(b) or len(a[0]) != len(b[0]):
            raise MatrixEngineError("Dimension ERROR")
        return [
            [a[i][j] - b[i][j] for j in range(len(a[0]))]
            for i in range(len(a))
        ]

    def scalar_multiply(self, name, scalar):
        mat = self._get_raw(name)
        rows = len(mat)
        cols = len(mat[0])
        return [[mat[i][j] * scalar for j in range(cols)] for i in range(rows)]

    def multiply(self, name_a, name_b):
        a = self._get_raw(name_a)
        b = self._get_raw(name_b)
        if len(a[0]) != len(b):
            raise MatrixEngineError("Dimension ERROR")
        rows = len(a)
        cols = len(b[0])
        inner = len(a[0])
        return [
            [sum(a[i][k] * b[k][j] for k in range(inner)) for j in range(cols)]
            for i in range(rows)
        ]

    def transpose(self, name):
        mat = self._get_raw(name)
        rows = len(mat)
        cols = len(mat[0])
        return [[mat[i][j] for i in range(rows)] for j in range(cols)]

    def determinant(self, name):
        mat = self._get_raw(name)
        n = len(mat)
        if len(mat[0]) != n:
            raise MatrixEngineError("Dimension ERROR")
        if n == 1:
            return float(mat[0][0])
        if n == 2:
            return float(mat[0][0] * mat[1][1] - mat[0][1] * mat[1][0])
        work = copy.deepcopy(mat)
        det = 1.0
        for col in range(n):
            pivot = col
            for row in range(col + 1, n):
                if abs(work[row][col]) > abs(work[pivot][col]):
                    pivot = row
            if pivot != col:
                work[col], work[pivot] = work[pivot], work[col]
                det = -det
            if abs(work[col][col]) < self._PIVOT_EPS:
                return 0.0
            det *= work[col][col]
            for row in range(col + 1, n):
                factor = work[row][col] / work[col][col]
                for j in range(n):
                    work[row][j] -= factor * work[col][j]
        return float(det)

    def inverse(self, name):
        mat = self._get_raw(name)
        n = len(mat)
        if len(mat[0]) != n:
            raise MatrixEngineError("Dimension ERROR")
        if abs(self.determinant(name)) < self._SINGULAR_DET_EPS:
            raise MatrixEngineError("Singular Matrix")
        work = [
            row + [1.0 if i == j else 0.0 for j in range(n)]
            for i, row in enumerate(copy.deepcopy(mat))
        ]
        for col in range(n):
            pivot = col
            for row in range(col + 1, n):
                if abs(work[row][col]) > abs(work[pivot][col]):
                    pivot = row
            if pivot != col:
                work[col], work[pivot] = work[pivot], work[col]
            if abs(work[col][col]) < self._PIVOT_EPS:
                raise MatrixEngineError("Singular Matrix")
            pivot_val = work[col][col]
            for j in range(2 * n):
                work[col][j] /= pivot_val
            for row in range(n):
                if row != col:
                    factor = work[row][col]
                    for j in range(2 * n):
                        work[row][j] -= factor * work[col][j]
        return [row[n:] for row in work]

    def ref(self, name):
        work = self._get_raw(name)
        rows = len(work)
        cols = len(work[0])
        lead = 0
        for col in range(cols):
            if lead >= rows:
                break
            pivot = lead
            for row in range(lead + 1, rows):
                if abs(work[row][col]) > abs(work[pivot][col]):
                    pivot = row
            if abs(work[pivot][col]) < self._PIVOT_EPS:
                continue
            if pivot != lead:
                work[lead], work[pivot] = work[pivot], work[lead]
            for row in range(lead + 1, rows):
                factor = work[row][col] / work[lead][col]
                for j in range(cols):
                    work[row][j] -= factor * work[lead][j]
            lead += 1
        return work

    def rref(self, name):
        work = self._get_raw(name)
        rows = len(work)
        cols = len(work[0])
        lead = 0
        for col in range(cols):
            if lead >= rows:
                break
            pivot = lead
            for row in range(lead + 1, rows):
                if abs(work[row][col]) > abs(work[pivot][col]):
                    pivot = row
            if abs(work[pivot][col]) < self._PIVOT_EPS:
                continue
            if pivot != lead:
                work[lead], work[pivot] = work[pivot], work[lead]
            pivot_val = work[lead][col]
            for j in range(cols):
                work[lead][j] /= pivot_val
            for row in range(rows):
                if row != lead:
                    factor = work[row][col]
                    for j in range(cols):
                        work[row][j] -= factor * work[lead][j]
            lead += 1
        return work

    def identity(self, n: int) -> list:
        """
        Return an n×n identity matrix as a list of lists of floats.
        Max supported size matches existing engine limit: n must be 1 to 4.
        """
        if n < 1 or n > 4:
            raise MatrixEngineError(
                f"Identity matrix size must be between 1 and 4, got {n}"
            )
        return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]