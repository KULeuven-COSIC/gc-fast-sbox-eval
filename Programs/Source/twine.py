from Programs.Source.spn import into_bitsliced_bits, into_cells, BitCell, permute, from_cells

from Compiler.library import print_ln

#def print_state(state, msg=""):
#    n = len(state)
#    cells = [cell.to_cbit() for cell in state]
#    print_ln(msg + ('%s ' * n), *cells)

class Twine:
    PERMUTATION = [5, 0, 1, 4, 7, 12, 3, 8, 13, 6, 9, 2, 15, 10, 11, 14]
    RC = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x03, 0x06, 0x0C, 0x18, 0x30, 0x23, 0x05, 0x0A, 0x14, 0x28, 0x13, 0x26, 0x0F, 0x1E, 0x3C, 0x3B, 0x35, 0x29, 0x11, 0x22, 0x07, 0x0E, 0x1C, 0x38, 0x33, 0x25, 0x09, 0x12, 0x24]
    RC_L = [rc & 0x7 for rc in RC]
    RC_H = [(rc >> 3) & 0x7 for rc in RC]
    KS_P1 = [3, 0, 1, 2]
    KS_P2_80 = [16, 17, 18, 19, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15] #[4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 0, 1, 2, 3]
    KS_P2_128 = [28, 29, 30, 31, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27] #[28, 29, 30, 31, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27]
    SBOX = [0xC, 0x0, 0xF, 0xA, 0x2, 0xB, 0x9, 0x5, 0x8, 0x3, 0xD, 0x7, 0x1, 0xE, 0x6, 0x4]
    def __init__(self, keysize, variant='bit'):
        if keysize == 80:
            self.expand_key = self.key_schedule80
        elif keysize == 128:
            self.expand_key = self.key_schedule128
        else:
            raise Error(f'Unknown keysize {keysize}')
        assert variant in ['bit', 'proj']
        self.variant = variant
    
    def encrypt(self, plaintext, key):
        assert len(plaintext) == 64
        state = into_cells(plaintext, 4, self.variant)
        keyschedule = self.expand_key(key)
        assert len(keyschedule) == 36
        for i in range(35):
            round_key = keyschedule[i]
            assert len(round_key) == 8
            for j in range(8):
                state[2*j+1] = self.sbox(state[2*j] ^ round_key[j]) ^ state[2*j+1]
            state = permute(state, Twine.PERMUTATION)
        
        round_key = keyschedule[35]
        for j in range(8):
            state[2*j+1] = self.sbox(state[2*j] ^ round_key[j]) ^ state[2*j+1]
        return from_cells(state, self.variant)
    
    def sbox(self, cell):
        if self.variant == 'bit':
            x0, x1, x2, x3 = cell.value
            a = x2 ^ x3
            b = x3 ^ (~x0 & x1)
            c = ~x0 ^ a ^ (x1 & a & b)
            d = a ^ (b & c)
            e = b ^ c
            f = c ^ d
            y3 = x1 ^ e
            y2 = e ^ (d & y3)
            y0 = c ^ (f & y2)
            y1 = f ^ y3
            return BitCell(4, [y0, y1, y2, y3])
        else:
            return cell.proj(Twine.SBOX, 4)
    
    def key_schedule80(self, key):
        assert len(key) == 80
        wk = into_cells(key, 4, self.variant)
        assert len(wk) == 20
        round_keys = []
        for i in range(35):
            round_keys.append([wk[1], wk[3], wk[4], wk[6], wk[13], wk[14], wk[15], wk[16]])
            wk[1] = wk[1] ^ self.sbox(wk[0])
            wk[4] = wk[4] ^ self.sbox(wk[16])
            wk[7] = wk[7] ^ Twine.RC_H[i]
            wk[19] = wk[19] ^ Twine.RC_L[i]
            # ROT 4
            wk[0:4] = permute(wk[0:4], Twine.KS_P1) #wk[1:4] + wk[:1]
            # ROT 16
            wk = permute(wk, Twine.KS_P2_80) #wk[4:] + wk[:4]
        round_keys.append([wk[1], wk[3], wk[4], wk[6], wk[13], wk[14], wk[15], wk[16]])
        return round_keys
    
    def key_schedule128(self, key):
        assert len(key) == 128
        wk = into_cells(key, 4, self.variant)
        assert len(wk) == 32
        round_keys = []
        for i in range(35):
            round_keys.append([wk[2], wk[3], wk[12], wk[15], wk[17], wk[18], wk[28], wk[31]])
            wk[1] = wk[1] ^ self.sbox(wk[0])
            wk[4] = wk[4] ^ self.sbox(wk[16])
            wk[23] = wk[23] ^ self.sbox(wk[30])
            wk[7] = wk[7] ^ Twine.RC_H[i]
            wk[19] = wk[19] ^ Twine.RC_L[i]
            wk[0:4] = permute(wk[0:4], Twine.KS_P1)
            wk = permute(wk, Twine.KS_P2_128)
        round_keys.append([wk[2], wk[3], wk[12], wk[15], wk[17], wk[18], wk[28], wk[31]])
        return round_keys


def twine_test(nparallel, variant='bit'):
    # 80-bit
    key = into_bitsliced_bits([0,0,1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8,9,9], 4, nparallel)
    plaintext = into_bitsliced_bits([0,1,2,3,4,5,6,7,8,9, 0xA,0xB,0xC,0xD,0xE,0xF], 4, nparallel)
    ciphertext = Twine(80, variant=variant).encrypt(plaintext, key)
    expected = into_bitsliced_bits([0x7,0xC,0x1,0xF,0x0,0xF,0x8,0x0,0xB,0x1,0xD,0xF,0x9,0xC,0x2,0x8], 4, nparallel)
    assert len(ciphertext) == len(expected)
    for c,e in zip(ciphertext, expected):
        c = c.reveal()
        e = e.reveal()
        print_ln('t: %s == %s :t', c, e)
    
    
    # 128-bit
    key = into_bitsliced_bits([0,0,1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8,9,9,0xA,0xA,0xB,0xB,0xC,0xC,0xD,0xD,0xE,0xE,0xF,0xF], 4, nparallel)
    plaintext = into_bitsliced_bits([0,1,2,3,4,5,6,7,8,9, 0xA,0xB,0xC,0xD,0xE,0xF], 4, nparallel)
    ciphertext = Twine(128, variant=variant).encrypt(plaintext, key)
    expected = into_bitsliced_bits([0x9,0x7,0x9,0xF,0xF,0x9,0xB,0x3,0x7,0x9,0xB,0x5,0xA,0x9,0xB,0x8], 4, nparallel)
    assert len(ciphertext) == len(expected)
    for c,e in zip(ciphertext, expected):
        c = c.reveal()
        e = e.reveal()
        print_ln('t: %s == %s :t', c, e)
    