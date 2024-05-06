from Compiler.GC.types import sbits, cbits

import math

class Cell:
    def __init__(self, cellsize):
        self.cellsize = cellsize
    
    def __xor__(self, b):
        raise "NotImplemented"

class BitCell(Cell):
    def __init__(self, cellsize, value):
        super().__init__(cellsize)
        self.value = value
    def __str__(self):
        return f'BitCell({self.cellsize}){self.value}'
    def __repr__(self):
        return str(self)
    def __xor__(self, b):
        if isinstance(b, BitCell):
            assert self.cellsize == b.cellsize
            return BitCell(self.cellsize, value=[ai ^ bi for ai, bi in zip(self.value, b.value)])
        elif isinstance(b, int):
            assert 0 <= b and b < 2**self.cellsize
            return BitCell(self.cellsize, value=[~ai if ((b >> i) & 0x1) > 0 else ai for i,ai in enumerate(self.value)])
        else:
            raise CompileError(f'Unsupported operand {b}')
    #@classmethod
    #def get_type(cls, cellsize, nparallel):
    #    def BitCelln(values):
    #        assert len(values) == cellsize
    #        v = []
    #        if isinstance(values, int):
    #            cb = cbits.get_type(nparallel)
    #        for value in values:
    #            if isinstance(value, sbits) or isinstance(value, cbits):
    #                assert nparallel == value.n
    #                v.append(value)
    #            else:
                    
    def to_cbit(self):
        cbn = cbits.get_type(self.cellsize)
        if self.value[0].n == 1:
            return cbn.bit_compose([v.reveal() for v in self.value])
        regs = []
        for i in range(self.value[0].n):
            regs.append(cbn.bit_compose(v[i].reveal() for v in self.value))
        return regs

class ProjCell(Cell):
    def __init__(self, cellsize, wire):
        super().__init__(cellsize)
        self.wire = wire
    def __str__(self):
        return f'ProjCell({self.cellsize}){self.wire}'
    def __repr__(self):
        return str(self)
    def __xor__(self, b):
        if isinstance(b, ProjCell):
            assert self.cellsize == b.cellsize
            return ProjCell(self.cellsize, wire = self.wire ^ b.wire)
        elif isinstance(b, int):
            assert 0 <= b and b < 2**self.cellsize
            return ProjCell(self.cellsize, wire=self.wire ^ b)
        else:
            raise CompileError(f'Unsupported operand {b}')
    def proj(self, sbox, n):
        assert self.cellsize == n
        return ProjCell(self.cellsize, wire=self.wire.proj(sbox, n))

def compose_bit(bits):
    n = len(bits)
    return sum([b.proj([0, 1 << i],n) for i,b in enumerate(bits)])

def uncompose_bits(w):
    assert 2**math.ceil(math.log2(w.single_wire_n)) == w.single_wire_n, f'Argument single_wire_n of n-bit wire {w} must be a power of two: {w.single_wire_n}'
    def _uncompose_bits(ws, n):
        if n == 1:
            return ws
        lower_mask = 2**(n//2)-1
        table0 = [x & lower_mask for x in range(2**n)]
        table1 = [(x >> (n//2)) & lower_mask for x in range(2**n)]
        output = []
        for w in ws:
            output.append(w.proj(table0, n//2))
            output.append(w.proj(table1, n//2))
        return _uncompose_bits(output, n//2)
    return _uncompose_bits([w], w.single_wire_n)

def into_cells(x, n, variant):
    assert len(x) % n == 0, f'{len(x)} % {n} failed'
    assert variant in ['bit', 'proj']
    cells = []
    for i in range(0, len(x), n):
        if variant == 'bit':
            cells.append(BitCell(n, x[i:i+n]))
        else:
            cells.append(ProjCell(n, compose_bit(x[i:i+n])))
    return cells

def from_cells(cells, variant):
    assert variant in ['bit', 'proj']
    if variant == 'bit':
        return [b for cell in cells for b in cell.value]
    else:
        return [w for cell in cells for w in cell.wire.bit_decompose() for w in uncompose_bits(w)]

def permute(state, permutation):
    assert len(state) == len(permutation)
    new_state = [None] * len(state)
    for i in range(len(state)):
        new_state[permutation[i]] = state[i]
    return new_state

def into_bitsliced_bits(x, n, nparallel):
    zero = sbits.get_type(nparallel)(0)
    one = sbits.get_type(nparallel)(2**nparallel-1)
    bits = []
    for xi in x:
        assert xi < 2**n
        for i in range(n):
            if ((xi >> i) & 0x1) > 0:
                bits.append(one)
            else:
                bits.append(zero)
    return bits

def _inner_prod(v1, v2):
    assert len(v1) == len(v2)
    assert all(x in [0,1] for x in v2)
    if sum(v2) <= 0:
        return 0
    res = None
    for i in range(len(v1)):
        if v2[i] == 1:
            if res == None:
                res = v1[i]
            else:
                res = res ^ v1[i]
    return res

def mix_columns_left(matrix, state):
    """ matrix is row-wise"""
    assert len(state) % len(matrix) == 0
    n = len(state)//len(matrix)
    new_state = [None] * len(state)
    for i in range(n):
        for j in range(n):
            v = [state[n*k+j] for k in range(n)]
            new_state[n*i+j] = _inner_prod(v, matrix[i])
    return new_state

def mix_columns_right(state, matrix):
    """ matrix is row-wise"""
    assert len(state) % len(matrix) == 0
    n = len(state)//len(matrix)
    new_state = [None] * len(state)
    for i in range(n):
        for j in range(n):
            v = [matrix[j][k] for k in range(n)]
            new_state[n*i+j] = _inner_prod(state[n*i:n*i+n], v)
    return new_state