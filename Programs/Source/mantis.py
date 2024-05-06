from Programs.Source.spn import into_cells, permute, from_cells, BitCell, mix_columns_left, into_bitsliced_bits

from Compiler.library import print_ln
from Compiler.GC.types import sbits

#def print_state(state, msg=""):
#    n = len(state)
#    cells = [cell.to_cbit() for cell in state]
#    print_ln(msg + ('%s ' * n), *cells)

#def print_bytes(bits, msg=""):
#    assert len(bits) % 8 == 0
#    l = []
#    s = ''
#    for i in range(0,len(bits),8):
#        l += list(bits[i:i+8])[::-1]
#        s += '%s' * 8
#        s += ' '
#    print_ln(msg+s, *[x.reveal() for x in l])

#def print_bits(bits, msg=""):
#    assert len(bits) % 8 == 0
#    s = ''
#    for i in range(0,len(bits),8):
#        s += '%s' * 8
#        s += ' '
#    print_ln(msg+s, *[x.reveal() for x in bits])

def nibble_swap(bits):
    assert len(bits) % 8 == 0
    l = []
    for i in range(0, len(bits), 8):
        l += (bits[i+4:i+8] + bits[i:i+4])[::-1]
    return l

class Mantis:
    RC = ['13198A2E03707344', 'A4093822299F31D0', '082EFA98EC4E6C89', '452821E638D01377', 'BE5466CF34E90C6C', 'C0AC29B7C97C50DD', '3F84D5B5B5470917', '9216D5D98979FB1B']
    P_T = [6, 5, 14, 15, 0, 1, 2, 3, 7, 12, 13, 4, 8, 9, 10, 11]
    P_T_inv = [4, 5, 6, 7, 11, 1, 0, 8, 12, 13, 14, 15, 9, 10, 2, 3]
    P_S = [0, 11, 6, 13, 10, 1, 12, 7, 5, 14, 3, 8, 15, 4, 9, 2]
    P_S_inv = [0, 5, 15, 10, 13, 8, 2, 7, 11, 14, 4, 1, 6, 3, 9, 12]
    M = [
        [0,1,1,1],
        [1,0,1,1],
        [1,1,0,1],
        [1,1,1,0]
    ]
    Alpha = [0x2, 0x4, 0x3, 0xf, 0x6, 0xa, 0x8, 0x8, 0x8, 0x5, 0xa, 0x3, 0x0, 0x8, 0xd, 0x3]
    SBOX = [0xc, 0xa, 0xd, 0x3, 0xe, 0xb, 0xf, 0x7, 0x8, 0x9, 0x1, 0x5, 0x0, 0x2, 0x4, 0x6]
    def __init__(self, rounds, variant='bit'):
        assert 5 <= rounds <= 8
        assert variant in ['bit', 'proj']
        self.rounds = rounds
        self.variant = variant
    
    def encrypt(self, plaintext, key, tweak):
        assert len(plaintext) == 64
        assert len(key) == 128
        assert len(tweak) == 64
        
        # create subkeys
        k0 = key[:64]
        
        # emulate little endian right rotation
        k0_prime = nibble_swap(key[:64])
        k0_prime = [k0_prime[63]] + k0_prime[:63]
        k0_prime[63] = k0_prime[63] ^ k0_prime[7]
        k0_prime = nibble_swap(k0_prime)
        
        k1 = key[64:]
        
        # add k0 to state before turning into cells
        assert len(plaintext) == len(k0)
        state = [p ^ k for p,k in zip(plaintext, k0)]
        
        state = into_cells(state, 4, self.variant)
        k0_prime = into_cells(k0_prime, 4, self.variant)
        k1 = into_cells(k1, 4, self.variant)
        tweak = into_cells(tweak, 4, self.variant)
        
        # rk0
        state = [s ^ k ^ t for s, k, t in zip(state, k1, tweak)]
        # forward rounds
        for i in range(self.rounds):
            # SubCells
            state = [self.sbox(s) for s in state]
            # AddConstant
            state = [s ^ int(Mantis.RC[i][j], 16) for j,s in enumerate(state)]
            # update tweak
            tweak = permute(tweak, Mantis.P_T_inv)
            # AddRoundTweakey
            state = [s ^ k ^ t for s,k,t in zip(state, k1, tweak)]
            # PermuteCells
            state = permute(state, Mantis.P_S_inv)
            # MixColumns
            state = mix_columns_left(Mantis.M, state)
            
        # SubCells
        state = [self.sbox(s) for s in state]
        # MixColumns
        state = mix_columns_left(Mantis.M, state)
        # SubCells Inv
        state = [self.sbox(s) for s in state]
        
        # Add alpha to k1
        k1 = [k ^ a for k, a in zip(k1, Mantis.Alpha)]
        
        for i in range(self.rounds-1, -1, -1):
            # MixColumns Inv
            state = mix_columns_left(Mantis.M, state)
            # PermuteCells Inv
            state = permute(state, Mantis.P_S)
            # AddRoundTweakey Inv
            state = [s ^ k ^ t for s,k,t in zip(state, k1, tweak)]
            # update tweak Inv
            tweak = permute(tweak, Mantis.P_T)
            # AddConstant Inv
            state = [s ^ int(Mantis.RC[i][j], 16) for j,s in enumerate(state)]
            # SubCells Inv
            state = [self.sbox(s) for s in state]
        # rk0
        state = [s ^ k ^ t for s, k, t in zip(state, k1, tweak)]
        state = [s ^ k for s, k in zip(state, k0_prime)]
        
        return from_cells(state, self.variant)
    def sbox(self, cell):
        if self.variant == 'bit':
            x0, x1, x2, x3 = cell.value
            a = ~(x0 ^ x2)
            b = x0 ^ (a & x3)
            c = x1 ^ b
            d = ~x3 ^ (a & b)
            y0 = b ^ (c & d)
            e = d ^ y0
            y1 = a ^ d
            y2 = c ^ e
            y3 = e ^ (y0 & y2)
            return BitCell(4, [y0, y1, y2, y3])
        else:
            return cell.proj(Mantis.SBOX, 4)

def mantis_test(nparallel, variant='bit'):
    # MANTIS-7
    key = into_bitsliced_bits([0x9,0x2,0xf,0x0,0x9,0x9,0x5,0x2,0xc,0x6,0x2,0x5,0xe,0x3,0xe,0x9,0xd,0x7,0xa,0x0,0x6,0x0,0xf,0x7,0x1,0x4,0xc,0x0,0x2,0x9,0x2,0xb], 4, nparallel)
    tweak = into_bitsliced_bits([0xb,0xa,0x9,0x1,0x2,0xe,0x6,0xf,0x1,0x0,0x5,0x5,0xf,0xe,0xd,0x2], 4, nparallel)
    plaintext = into_bitsliced_bits([0x6,0x0,0xe,0x4,0x3,0x4,0x5,0x7,0x3,0x1,0x1,0x9,0x3,0x6,0xf,0xd], 4, nparallel)
    ciphertext = Mantis(rounds=7, variant=variant).encrypt(plaintext, key, tweak)
    expected = into_bitsliced_bits([0x3,0x0,0x8,0xe,0x8,0xa,0x0,0x7,0xf,0x1,0x6,0x8,0xf,0x5,0x1,0x7], 4, nparallel)
    assert len(ciphertext) == len(expected)
    for c,e in zip(ciphertext, expected):
        c = c.reveal()
        e = e.reveal()
        print_ln('t: %s == %s :t', c, e)
