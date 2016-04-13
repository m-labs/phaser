from migen import *
from migen.fhdl.verilog import convert

from switch import Switch


def req(dut, pkg):
    yield dut.stb.eq(1)
    yield dut.eop.eq(0)
    for i, j in enumerate(pkg):
        yield dut.data.eq(j)
        if i == len(pkg) - 1:
            yield dut.eop.eq(1)
        yield
        while not (yield dut.ack):
            yield
    yield dut.stb.eq(0)


def read(dut, o):
    yield dut.ack.eq(1)
    while True:
        while not (yield dut.stb):
            yield
        o.append((yield dut.data))
        if (yield dut.eop):
            break
        yield
    yield dut.ack.eq(0)


class FB(Module):
    def __init__(self, dut):
        self.submodules += dut
        for j, (i, o) in enumerate(zip(dut.req.o, dut.rep.i)):
            self.comb += [
                o.payload.raw_bits().eq(i.payload.raw_bits()),
                o.eop.eq(i.eop),
                o.stb.eq(i.stb),
                i.ack.eq(o.ack),
            ]


def fb(dut_i, dut_o, o, func):
    while True:
        while not (yield dut_i.stb):
            yield
        o.append((yield dut_i.data))
        if (yield dut_i.eop):
            break
        yield


def xfer(dut, *pkgs):
    def setup():
        yield dut.offsets[1].eq(1)
        yield dut.offsets[2].eq(4)
        yield dut.offsets[3].eq(9)

    def send():
        for pkg in pkgs:
            yield
            yield from req(dut.req.i, pkg)

    o = []

    def recv():
        for pkg in pkgs:
            oi = []
            yield from read(dut.rep.o, oi)
            yield
            o.append(oi)

    def teardown():
        while len(o) < len(pkgs):
            yield
        for i in [dut.req.i, dut.rep.o] + dut.req.o + dut.rep.i:
            assert not (yield i.stb)
            assert not (yield i.ack)
            assert (yield i.eop)

    gens = [setup(), send(), recv(), teardown()]
    f = []
    for i, (ai, bi) in enumerate(zip(dut.req.o, dut.rep.i)):
        fi = []
        f.append(fi)
        gens.append(fb(ai, bi, fi, lambda _: _))
    return f, o, gens


def test():
    dut = Switch(4)

    if False:
        print(convert(dut))
    else:
        i = [[0], [1], [4, 1, 2, 3], [100, 2, 3]]
        f, o, gens = xfer(dut, *i)
        run_simulation(FB(dut), gens, vcd_name="switch.vcd")
        print(i, f, o)
        assert i == o


if __name__ == "__main__":
    test()
