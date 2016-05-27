import numpy as np

from migen import *
from migen.fhdl.verilog import convert

from rtio_sawg import Channel
from tools import xfer


def _test_gen_dds(dut, o):
    # cfg: iq=0b11, clr=0b1, tap=0b00000
    yield from xfer(dut.phys[0].rtlink, o={"data": 0b11100000})
    # u (dc bias)
    yield from xfer(dut.phys[1].rtlink, o={"data": 0})
    # a (dds amplitude)
    yield from xfer(dut.phys[2].rtlink, o={"data": 50})
    # f (dds frequency)
    yield from xfer(dut.phys[3].rtlink, o={"data": 1 << 16})
    # p (dds phase)
    yield from xfer(dut.phys[4].rtlink, o={"data": 0})
    for i in range(256):
        yield
        o.append((yield from [(yield _) for _ in dut.o]))


def _test_channel():
    dut = Channel(width=8, parallelism=2)

    if False:
        print(convert(dut))
    else:
        o = []
        run_simulation(dut, _test_gen_dds(dut, o), vcd_name="dds.vcd")
        o = np.array(o)
        print(o)


if __name__ == "__main__":
    _test_channel()
