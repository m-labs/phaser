import numpy as np

from migen import *
from migen.fhdl.verilog import convert

from spline import Spline
from phaser import Phaser


def _test_gen_phaser(dut, o):
    yield dut.ce.eq(1)
    yield dut.i.a0.eq(0)
    yield dut.i.a1.eq(1)
    yield dut.i.stb.eq(1)
    yield
    while not (yield dut.i.ack):
        yield
    yield dut.i.stb.eq(0)
    for i in range(len(dut.o)):
        yield
    for i in range(20):
        yield
        o.append((yield from [(yield pi.a0) for pi in dut.o]))


def _test_phaser():
    def f(step):
        return Spline(order=2, width=16, step=step)
    dut = Phaser(f, parallelism=2)

    if False:
        print(convert(dut))
    else:
        o = []
        run_simulation(dut, _test_gen_phaser(dut, o), vcd_name="phaser.vcd")
        o = np.array(o)
        print(o)


if __name__ == "__main__":
    _test_phaser()
