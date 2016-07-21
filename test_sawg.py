import numpy as np

from migen import *
from migen.fhdl.verilog import convert

from sawg import DDS

from tools import xfer


def _test_gen_dds(dut, o):
    yield dut.ce.eq(1)
    yield dut.clr.eq(1)
    yield from xfer(dut,
                    a1=dict(a0=10),
                    p1=dict(a0=0),
                    f1=dict(a0=0 << 16, a1=0),
                    f=dict(a0=10 << 24),
                    p=dict(a0=0),
                    )
    for i in range(256):
        yield
        o.append((yield from [((yield _[0]), (yield _[1])) for _ in dut.o]))


def _test_channel():
    dut = DDS(width=8, parallelism=2)

    if False:
        print(convert(dut))
    else:
        o = []
        run_simulation(dut, _test_gen_dds(dut, o), vcd_name="dds.vcd")
        o = np.array(o)
        print(o[:, :, 0])


if __name__ == "__main__":
    _test_channel()
