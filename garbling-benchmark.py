import argparse
import subprocess
import time
import re
import numpy as np
import sys
import os


def compile(target):
    args = ['./compile.py', *target]
    try:
        subprocess.run(args, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(e.stdout.decode('utf-8'))
        print(e.stderr.decode('utf-8'))
        assert False, f'Compilation of {target} failed. See above'

def run_mpspdz(target, dir, iters):
    garbler_args = ['./yao-party.x', '-p', '0', '-pn', '8000', target]
    eval_args = ['./yao-party.x', '-p', '1', '-pn', '8000', target]
    
    garble_logs = []
    eval_logs = []
    for i in range(iters):
        garble_log = f'{dir}/{target}-garbler-{i}'
        eval_log = f'{dir}/{target}-eval-{i}'
        with open(garble_log, 'w') as garblefp:
            with open(eval_log, 'w') as evalfp:
                garbler = subprocess.Popen(garbler_args, stdout=garblefp, stderr=garblefp)
                evaluator = subprocess.Popen(eval_args, stdout=evalfp, stderr=evalfp)
                assert garbler.wait() == 0
                assert evaluator.wait() == 0
                garble_logs.append(garble_log)
                eval_logs.append(eval_log)
    return garble_logs, eval_logs

TIMER1 = re.compile(r"""Time1 = ([0-9\.e-]+)""")
MEM = re.compile(r"""Data sent = ([0-9\.e-]+) MB""")
def parse_mpspdz(path):
    with open(path, 'r') as fp:
        time = None
        mem = None
        for line in fp.readlines():
            if not time:
                time = re.match(TIMER1, line)
            if not mem:
                mem = re.match(MEM, line)
        assert time, f'Cannot find time in {path}'
        assert mem, f'Cannot find mem in {path}'
        time = float(time.group(1)) * 1000
        mem = float(mem.group(1))
        return time, mem

def benchmark_mpspdz(dir, target, simd, iters):
    compile(['-B', str(simd), 'garbling_benchmark', target, str(simd)])
    garble_logs, eval_logs = run_mpspdz(f'garbling_benchmark-{target}-{simd}', dir, iters)
    garble = []
    eval = []
    mem = []
    for garble_log, eval_log in zip(garble_logs, eval_logs):
        g, m = parse_mpspdz(garble_log)
        e, _ = parse_mpspdz(eval_log)
        garble.append(g)
        eval.append(e)
        mem.append(m)
    
    garble_avg = np.mean(garble)
    garble_std = np.std(garble)
    eval_avg = np.mean(eval)
    eval_std = np.std(eval)
    mem_avg = np.mean(mem)
    mem_std = np.std(mem)
    return garble_avg, garble_std, eval_avg, eval_std, mem_avg, mem_std


MOTION_SETUP = re.compile(r'Gates Setup\s*([0-9\.e-]+) ms\s*([0-9\.e-]+) ms\s*([0-9\.e-]+|-nan\s*) ms')
MOTION_ONLINE = re.compile(r'Gates Online\s*([0-9\.e-]+) ms\s*([0-9\.e-]+) ms\s*([0-9\.e-]+|-nan\s*) ms')
MOTION_MEM = re.compile(r'Sent: ([0-9\.e-]+) MiB')
def benchmark_motion(dir,target, circuit, simd, iters):
    motion_bin = 'MOTION/build/bin/bristol-evaluator'
    garbler_args = [motion_bin, '--my-id', '0', '--parties', '0,127.0.0.1,23000', '1,127.0.0.1,23001', '--num-simd', str(simd), '--repetitions', str(iters), '--online-after-setup', '1', '--circuit', circuit]
    eval_args = [motion_bin, '--my-id', '1', '--parties', '0,127.0.0.1,23000', '1,127.0.0.1,23001', '--num-simd', str(simd), '--repetitions', str(iters), '--online-after-setup', '1', '--circuit', circuit]
    
    garble_log = f'{dir}/motion-{target}-garbler'
    eval_log = f'{dir}/motion-{target}-eval'
    with open(garble_log, 'w') as garblefp:
        with open(eval_log, 'w') as evalfp:
            garbler = subprocess.Popen(garbler_args, stdout=garblefp, stderr=garblefp)
            evaluator = subprocess.Popen(eval_args, stdout=evalfp, stderr=evalfp)
            assert garbler.wait() == 0
            assert evaluator.wait() == 0
    
    garble_match = None
    mem_match = None
    with open(garble_log, 'r') as fp:
        for line in fp.readlines():
            if not garble_match:
                garble_match = re.match(MOTION_SETUP, line)
            if not mem_match:
                mem_match = re.match(MOTION_MEM, line)
    assert garble_match, f'Cannot find garbler time in {garble_log}'
    assert mem_match, f'Cannot find mem in {garble_log}'
    garble_avg = float(garble_match.group(1))
    garble_std = float(garble_match.group(3))
    mem_avg = float(mem_match.group(1))
    mem_std = 0.0 # this is not measured in MOTION
    
    eval_match = None
    with open(eval_log, 'r') as fp:
        for line in fp.readlines():
            if not eval_match:
                eval_match = re.match(MOTION_ONLINE, line)
    assert eval_match, f'Cannot find eval time in {eval_log}'
    eval_avg = float(eval_match.group(1))
    eval_std = float(eval_match.group(3))
    return garble_avg, garble_std, eval_avg, eval_std, mem_avg, mem_std
    
def run_benchmark(targets, simd, iters, benchname):
    os.mkdir(benchname)
    d = dict()
    for target in targets:
        d[target] = benchmark_mpspdz(benchname, target, simd, iters)
    return d

def run_benchmark_motion(targets, circuits, simd, iters, benchname):
    os.mkdir(benchname)
    d = dict()
    for target, circuit in zip(targets, circuits):
        d[target] = benchmark_motion(benchname, target, circuit, simd, iters)
    return d

circuits = ['all', 'skinny64_64', 'skinny64_128', 'skinny64_192', 'skinny128_128', 'skinny128_256', 'skinny128_384', 'mantis7', 'twine80', 'twine128', 'aes128']

parser = argparse.ArgumentParser()
parser.add_argument('--simd', type=int, required=False, default=1, help='The number of SIMD, i.e., parallel invocations of the circuit')
parser.add_argument('--iters', type=int, required=False, default=1, help='The number of repetitions')
parser.add_argument('--zre15', action='store_true', default=False, required=False, help='Use ZRE15 garbling scheme (HalfGates)')
parser.add_argument('--rr21', action='store_true', default=False, required=False, help='Use RR21 garbling scheme (ThreeHalves)')
parser.add_argument('--proj', action='store_true', default=False, required=False, help='Use projection gates garbling scheme')
parser.add_argument('--csv', type=str, required=False, help='Generate a csv file with the data.')
parser.add_argument('circuit', type=str, nargs='+', metavar='circuit', help=f'The circuits to execute, options are {circuits}', choices=circuits)

args = parser.parse_args()

if not args.zre15 and not args.proj and not args.rr21:
    print('At least one garbling scheme is required!')
    sys.exit(1)

if 'all' in args.circuit:
    args.circuit = list(circuits[1:])

data = dict()

t = time.strftime('%Y-%m-%d-%H:%M')
benchname = f'benchmark-{t}'

if args.zre15:
    d = run_benchmark(args.circuit, args.simd, args.iters, f'{benchname}-zre15')
    data['ZRE15'] = d
    print('-' * 30)
    print(f'ZRE15 in MP-SPDZ\tSIMD={args.simd}\tITERS={args.iters}')
    for circuit in args.circuit:
        garble_avg, garble_std, eval_avg, eval_std, mem_avg, mem_std = d[circuit]
        print(f'{circuit}:\tMean Garble={garble_avg} ms ({garble_std}), Mean Eval={eval_avg} ms ({eval_std}), Mean mem={mem_avg} MB ({mem_std})')

if args.proj:
    targets = [f'{circuit}_proj' for circuit in args.circuit]
    d = run_benchmark(targets, args.simd, args.iters, f'{benchname}-proj')
    data['PROJ'] = d
    print('-' * 30)
    print(f'Proj in MP-SPDZ\tSIMD={args.simd}\tITERS={args.iters}')
    for circuit in args.circuit:
        garble_avg, garble_std, eval_avg, eval_std, mem_avg, mem_std = d[f'{circuit}_proj']
        print(f'{circuit}:\tMean Garble={garble_avg} ms ({garble_std}), Mean Eval={eval_avg} ms ({eval_std}), Mean mem={mem_avg} MB ({mem_std})')

if args.rr21:
    circuits = [f'{target}.txt' if target != 'aes128' else f'Programs/Circuits/aes_128.txt' for target in args.circuit]
    d = run_benchmark_motion(args.circuit, circuits, args.simd, args.iters, f'{benchname}-rr21')
    data['RR21'] = d
    print('-' * 30)
    print(f'RR21 in MOTION\tSIMD={args.simd}\tITERS={args.iters}')
    for circuit in args.circuit:
        garble_avg, garble_std, eval_avg, eval_std, mem_avg, mem_std = d[circuit]
        print(f'{circuit}:\tMean Garble={garble_avg} ms ({garble_std}), Mean Eval={eval_avg} ms ({eval_std}), Mean mem={mem_avg} MB ({mem_std})')

if args.csv:
    header = 'Circuit,Protocol,Iterations,SIMD,Garbling time [ms],Garbling time std,Eval time [ms],Eval time std,Circuit Size [MB],Circuit Size std\n'
    def write_data(fp,circuit,protocol,args,garble_avg, garble_std, eval_avg, eval_std, mem_avg, mem_std):
        fp.write(f'{circuit},{protocol},{args.iters},{args.simd},{garble_avg},{garble_std},{eval_avg},{eval_std},{mem_avg},{mem_std}\n')
    with open(args.csv, 'w') as fp:
        fp.write(header)
        for circuit in args.circuit:
            if 'ZRE15' in data:
                write_data(fp, circuit, 'ZRE15', args, *(data['ZRE15'][circuit]))
            if 'RR21' in data:
                write_data(fp, circuit, 'RR21', args, *(data['RR21'][circuit]))
            if 'PROJ' in data:
                write_data(fp, circuit, 'PROJ', args, *(data['PROJ'][f'{circuit}_proj']))
    print(f'Wrote results to {args.csv}')
