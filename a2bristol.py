import argparse
import re

class Instruction:
    def __init__(self, name, in_wires, out_wires):
        self.name = name
        self.in_wires = in_wires
        self.out_wires = out_wires
    
    @classmethod
    def XOR(cls, res, op1, op2):
        assert isinstance(res, int)
        assert isinstance(op1, int)
        assert isinstance(op2, int)
        return cls(name='XOR', in_wires=[op1, op2], out_wires=[res])
    @classmethod
    def AND(cls, res, op1, op2):
        assert isinstance(res, int)
        assert isinstance(op1, int)
        assert isinstance(op2, int)
        return cls(name='AND', in_wires=[op1, op2], out_wires=[res])
    @classmethod
    def NOT(cls, res, op1):
        assert isinstance(res, int)
        assert isinstance(op1, int)
        return cls(name='NOT', in_wires=[op1], out_wires=[res])
        
    def __repr__(self):
        return str(self)
    
    def __str__(self):
        return f'{self.name} in={self.in_wires} out={self.out_wires}'
    
    def to_bristol_format(self, not_is_inv=False):
        name = self.name
        if not_is_inv and name == 'NOT':
            name = 'INV'
        in_wires = ' '.join(map(str, self.in_wires))
        out_wires = ' '.join(map(str, self.out_wires))
        return f'{len(self.in_wires)} {len(self.out_wires)} {in_wires} {out_wires} {name}'

class Circuit:
    def __init__(self, gates, inputs, outputs):
        self.gates = gates
        self.inputs = inputs
        self.outputs = outputs
    
    def _count_unique_wires(self):
        wires = set()
        for g in self.gates:
            wires |= set(g.in_wires)
            wires |= set(g.out_wires)
        return len(wires)
        
    def map_wire_ids(self, map_f):
        """ Replaces each wire wi in the circuit with map_f(wi) """
        for g in self.gates:
            g.in_wires = [map_f(wi) for wi in g.in_wires]
            g.out_wires = [map_f(wi) for wi in g.out_wires]
    
    def rename_first_wire(self, wi, wo, start=0):
        """ Rename the first wire with id wi to wo """
        cnt = 0
        for g in self.gates[start:]:
            if wi in g.in_wires:
                # replace wi with wo in the input list
                g.in_wires = [wo if xi == wi else xi for xi in g.in_wires]
                cnt += 1
            if wi in g.out_wires:
                # stop since from now on, wi is a different value
                return cnt
        return cnt
    
    def rename_last_wire(self, wi, wo):
        cnt = 0
        for g in reversed(self.gates):
            if wi in g.out_wires:
                # replace wi with wo in the output list
                g.out_wires = [wo if xi == wi else xi for xi in g.out_wires]
                cnt += 1
                return cnt
            if wi in g.in_wires:
                # replace wi with wo in the input list
                g.in_wires = [wo if xi == wi else xi for xi in g.in_wires]
                cnt += 1
        return cnt
    
    def max_wire(self):
        max_wire_id = -1
        for g in self.gates:
            m1 = max(g.out_wires)
            m2 = max(g.in_wires)
            max_wire_id = max([m1,m2,max_wire_id])
        return max_wire_id
        
    def num_wires(self):
        return sum(len(g.out_wires) for g in self.gates)
    
    def relabel_circuit(self):
        n_input_wires = sum([len(in_ids) for in_ids in self.inputs])
        # increment all wire ids in the circuit
        self.map_wire_ids(lambda w: w + n_input_wires)
        # rename inputs
        next_wire_id = 0
        for ids in self.inputs:
            for i,wi in enumerate(ids):
                # rename wi (which is now wi+n_input_wires) to next_wire_id
                cnt = self.rename_first_wire(wi+n_input_wires, next_wire_id)
                ids[i] = next_wire_id
                next_wire_id += 1
                print(f'Renamed input wire {wi} {cnt} times')
        
        # fix self.outputs
        self.outputs = [[i + n_input_wires for i in ids] for ids in self.outputs]
        
        
        # linearize ids
        id_dict = {i:i for i in range(n_input_wires)}
        next_free = n_input_wires
        for g in self.gates:
            # print(f'Gate {g}')
            assert all(wi in id_dict for wi in g.in_wires)
            assert len(set(g.out_wires)) == len(g.out_wires), f'No duplicates in out wires supported'
            out_wires = []
            in_wires = []
            
            for wi in g.in_wires:
                in_wires.append(id_dict[wi])
                # print(f'Renaming input wire {wi} to {id_dict[wi]}')
            
            for wi in g.out_wires:
                out_wires.append(next_free)
                id_dict[wi] = next_free
                # print(f'Renaming output wire {wi} to {next_free}')
                next_free += 1
            g.in_wires = in_wires
            g.out_wires = out_wires
        # fix self.outputs
        self.outputs = [[id_dict[i] for i in ids] for ids in self.outputs]
        
        # now the output wires are not ordered and the last ids in the circuit
        n_wires = self.num_wires() + n_input_wires
        # rename output wires to free range
        id_cnt = n_wires
        for ids in self.outputs:
            for i,wi in enumerate(ids):
                cnt = self.rename_last_wire(wi, id_cnt)
                ids[i] = id_cnt
                id_cnt += 1
        
        # we potentially have n_outputs unused wires between n_input_wires and n_wires
        n_output_wires = sum(len(ids) for ids in self.outputs)
        wires = set()
        for g in self.gates:
            wires |= set(g.in_wires)
            wires |= set(g.out_wires)
        max_wire_id = max(wires)
        unused = list()
        for i in range(max_wire_id+1):
            if i not in wires:
                unused.append(i)
        # try to rename wires from n_wires - n_output_wires until n_wires into the unused ids
        unused_idx = 0
        for i in range(n_wires - n_output_wires, n_wires):
            cnt = self.rename_last_wire(i, unused[unused_idx])
            if cnt > 0:
                unused_idx += 1
    
        # rename output wires into the range n_wires - n_output_wires until n_wires
        id_cnt = n_wires - n_output_wires
        for ids in self.outputs:
            for i,wi in enumerate(ids):
                cnt = self.rename_last_wire(wi, id_cnt)
                ids[i] = id_cnt
                id_cnt += 1
                print(f'Renamed output wire {wi} {cnt} times')
    
    def shrink_circuit(self):
        wires = set()
        for g in self.gates:
            wires |= set(g.in_wires)
            wires |= set(g.out_wires)
        max_wire_id = max(wires)
        unused = set()
        for i in range(max_wire_id+1):
            if i not in wires:
                unused.add(i)
        print(f'Found {len(unused)} unused wire slots')
        
        computed_wires = set(wi for ids in self.inputs for wi in ids)
        required_wires = set(wi for ids in self.outputs for wi in ids)
        for g in self.gates:
            computed_wires |= set(g.out_wires)
            required_wires |= set(g.in_wires)
        cnt = 0
        unused_gate_ids = set()
        for i in computed_wires:
            if i not in required_wires:
                cnt += 1
                unused_gate_ids.add(i)
        print(f'Found {cnt} unused gates')
        if cnt > 0:
            for i,g in enumerate(self.gates):
                for wi in g.out_wires:
                    if wi in unused_gate_ids:
                        print(f'#{i} {g} unused output wire {wi}')
    
    def check_connectivity(self):
        print('Checking wire connections in the circuit')
        wires = set()
        # add input wires
        for ids in self.inputs:
            for wi in ids:
                wires.add(wi)
        for i,g in enumerate(self.gates):
            for wi in g.in_wires:
                assert wi in wires, f'Input wire {wi} to gate #{i} ({str(g)}) has not been written'
            for wi in g.out_wires:
                wires.add(wi)
        # output wires are written to
        for i,ids in enumerate(self.outputs):
            for wi in ids:
                assert wi in wires, f'Output wire {wi} of output #{i} has not been written'
        print('ok')
        
    def prepare_for_bristol_format(self):
        self.check_connectivity()
        #print(self)
        self.relabel_circuit()
        #print(self)
        self.check_connectivity()
        #print(self)
        self.shrink_circuit()
        #print(self)
        self.check_connectivity()
    
    def write_to_bristol_format(self, fp, not_is_inv=False):
        n_wires = self.max_wire() + 1
        fp.write(f'{len(self.gates)} {n_wires}\n')
        inputs = ' '.join([str(len(ids)) for ids in self.inputs])
        outputs = ' '.join([str(len(ids)) for ids in self.outputs])
        fp.write(f'{len(self.inputs)} {inputs}\n')
        fp.write(f'{len(self.outputs)} {outputs}\n')
        # write newline (this is not explicitly documented but all parsers expect it...)
        fp.write('\n')
        for g in self.gates:
            fp.write(g.to_bristol_format(not_is_inv=not_is_inv))
            fp.write('\n')
    
    def __repr__(self):
        return str(self)
    def __str__(self):
        gates = [str(g) for g in self.gates]
        return f'Circuit with input={self.inputs}, output={self.outputs}\n' + "\n".join(gates)

sbit_pattern = re.compile(r'''sb(\d+)\(\d+\)''')
def parse_sbit_op(sbitop):
    m = sbit_pattern.match(sbitop)
    return int(m.group(1))

def parse_xors(instr):
    l = list()
    name = instr[0]
    assert name == 'xors'
    n_xors = int(instr[1])
    assert n_xors % 4 == 0
    offset = 2
    for i in range(n_xors//4):
        n_bits = int(instr[offset+0])
        res = parse_sbit_op(instr[offset+1])
        op1 = parse_sbit_op(instr[offset+2])
        op2 = parse_sbit_op(instr[offset+3])
        
        assert n_bits == 1, 'More bits for XORS currently not implemented'
        l.append(Instruction.XOR(res, op1, op2))
        offset += 4
    return l

def parse_ands(instr):
    l = list()
    name = instr[0]
    assert name == 'ands'
    n_ands = int(instr[1])
    assert n_ands % 4 == 0
    offset = 2
    for i in range(n_ands//4):
        n_bits = int(instr[offset+0])
        res = parse_sbit_op(instr[offset+1])
        op1 = parse_sbit_op(instr[offset+2])
        op2 = parse_sbit_op(instr[offset+3])
        
        assert n_bits == 1, 'More bits for ANDS currently not implemented'
        l.append(Instruction.AND(res, op1, op2))
        offset += 4
    return l

def parse_reveal(instr):
    l = list()
    name = instr[0]
    assert name == 'reveal'
    n = int(instr[1])
    assert n % 3 == 0
    offset = 2
    for i in range(n//3):
        n_bits = int(instr[offset+0])
        rev = parse_sbit_op(instr[offset+2])
        
        assert n_bits == 1, 'More bits for reveal currently not implemented'
        l.append(rev)
        offset += 3
    return l

def parse_nots(instr):
    name = instr[0]
    assert name == 'nots'
    n_bits = int(instr[1])
    assert n_bits == 1, 'More bits for NOTS currently not implemented'
    res = parse_sbit_op(instr[2])
    op1 = parse_sbit_op(instr[3])
    return [Instruction.NOT(res, op1)]

input_marker = re.compile(r'''Input (\d+)''')
output_marker = re.compile(r'''Output (\d+)''')

def parse_asm_file(path, inputs, outputs):
    gates = list()
    input_ids = dict()
    output_ids = dict()
    next_input = False
    next_output = False
    next_i = None
    with open(path, 'r') as fp:
        for line in fp.readlines():
            if not line.startswith('#'):
                line, _, _ = line.partition('#')
                instruction = re.split(r''',?\s''', line.strip())
                name = instruction[0]
                if next_input:
                    assert name == 'reveal'
                    next_input = False
                    assert next_i not in input_ids
                    ids = parse_reveal(instruction)
                    assert len(ids) == inputs[next_i]
                    input_ids[next_i] = ids
                    print(f'Found Input #{next_i} with {len(ids)} bits')
                if next_output:
                    assert name == 'reveal'
                    next_output = False
                    assert next_i not in output_ids
                    ids = parse_reveal(instruction)
                    assert len(ids) == outputs[next_i]
                    output_ids[next_i] = ids
                    print(f'Found Output #{next_i} with {len(ids)} bits')
                if name == 'xors':
                    gates += parse_xors(instruction)
                elif name == 'ands':
                    gates += parse_ands(instruction)
                elif name == 'nots':
                    gates += parse_nots(instruction)
            else:
                m = re.search(input_marker, line)
                if m != None:
                    next_input = True
                    next_output = False
                    next_i = int(m.group(1))
                    continue
                m = re.search(output_marker, line)
                if m != None:
                    next_output = True
                    next_input = False
                    next_i = int(m.group(1))
                    continue
    
    input_id_list = []
    for i in range(len(inputs)):
        assert i in input_ids
        input_id_list.append(input_ids[i])
    output_id_list = []
    for i in range(len(outputs)):
        assert i in output_ids
        output_id_list.append(output_ids[i])
    
    return gates, input_id_list, output_id_list

description = '''This script transpiles the Boolean circuit assembly from the MP-SPDZ compiler into the Bristol Fashion Circuit format (https://homes.esat.kuleuven.be/~nsmart/MPC/).

Example MP-SPDZ file "test.mpc"
>> sb = sbits.get_type(1)
>> 
>> input = [sb(0), sb(1)]
>> break_point('Input 0') #mark a reveal call using break_point as input or output
>> for w in input:
>>     w.reveal()
>>
>>
>> # function
>> a, b = input
>> c = a ^ b
>> d = a & c
>> d = b & d
>> e = a ^ b ^ d
>> output = [c,e]
>> 
>> break_point('Output 0')
>> for w in output:
>>     w.reveal()

Compile to assembly using "./compile.py -a <assembly name> test.mpc".
Now run the a2bristol script "python a2bristol.py --input 2 --output 2 <assembly name>". This will create the circuit file <assembly name>.txt.
Note that --input or --output can be repeated multiple times, e.g., --input 2 --input 4 for two breakpoints with names 'Input 0' and 'Input 1' revealing 2 and 4 sbits, respectively.
'''
parser = argparse.ArgumentParser(prog='a2bristol.py', description=description, formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('path', type=str)
parser.add_argument('--not-is-inv', action='store_true', default=False, required=False, dest='not_is_inv', help='Write every encountered NOTS instruction as INV gate (instead of NOT) in the output circuit. The MP-SPDZ circuit module requires this.')
parser.add_argument('--input', type=str, action='append', required=False, dest='input')
parser.add_argument('--output', type=str, action='append', required=False, dest='output')

args = parser.parse_args()

inputs = args.input
parsed_inputs = []
for i,in_stmt in enumerate(inputs):
    parsed_inputs.append(int(in_stmt))

outputs = args.output
parsed_outputs = []
for i,in_stmt in enumerate(outputs):
    parsed_outputs.append(int(in_stmt))



gates, input_ids, output_ids = parse_asm_file(args.path, parsed_inputs, parsed_outputs)
c = Circuit(gates, input_ids, output_ids)
c.prepare_for_bristol_format()

with open(f'{args.path}.txt', 'w') as fp:
    c.write_to_bristol_format(fp, not_is_inv=args.not_is_inv)
print('Done :)')