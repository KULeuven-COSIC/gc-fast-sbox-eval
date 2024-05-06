from Compiler.library import print_ln
from Compiler.GC.types import cbits
from Compiler.types import sgf2n, cgf2n
import importlib.util
import sys

def import_path(module_name, path):
    spec = importlib.util.spec_from_loader(
        module_name,
        importlib.machinery.SourceFileLoader(module_name, path)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules[module_name] = module
    return module

def test(a,b):
    bitlen = a.single_wire_n if a.single_wire_n > 1 else a.n
    n_wires = 1 if a.single_wire_n == 1 else a.n
    
    if a.single_wire_n > 1:
        a = a.reveal() # this returns a list
    else:
        a = [a.reveal()]
    if n_wires == 1:
        b = [b]
    assert len(b) == n_wires
    assert len(a) == n_wires
    print_ln('t: %s == %s :t', a, [cbits(x, n=bitlen) for x in b])