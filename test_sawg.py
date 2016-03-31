import numpy as np

from migen import *
from migen.fhdl.verilog import convert

from sawg import DDS, DDSPair

from tools import xfer


def _test_gen_dds(dut, o):
    yield dut.ce.eq(1)
    yield from xfer(dut,
                    a=dict(a0=1 << 24),
                    p=dict(a0=0 << 8, clr=1),
                    f=dict(a0=1 << 16, a1=0 << 12))
    for i in range(256):
        yield
        o.append((yield from [((yield _[0]), (yield _[1])) for _ in dut.o]))


def _test_channel():
    # dut = Channel()
    dut = DDS(8, parallelism=2)

    if False:
        print(convert(dut))
    else:
        o = []
        run_simulation(dut, _test_gen_dds(dut, o), vcd_name="dds.vcd")
        o = np.array(o)
        print(o[:, :, 0])
        print(o[:, :, 1])


if __name__ == "__main__":
    _test_channel()
