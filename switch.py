from migen import *
from misoc.interconnect.stream import Endpoint


class RequestSwitch(Module):
    def __init__(self, num_ports, width):
        self.layout = [("data", width)]
        self.i = Endpoint(self.layout)
        self.o = [Endpoint(self.layout) for _ in range(num_ports)]
        self.offsets = [Signal(width) for _ in range(num_ports)]

        ###

        sel0 = Signal(max=num_ports)
        sel1 = Signal(max=num_ports)
        sel = Signal(max=num_ports)
        sop = Signal()
        payload = Record(self.layout)

        for j in range(num_ports):
            self.comb += [
                If(self.i.payload.data >= self.offsets[j],
                    sel0.eq(j),
                )
            ]
        self.sync += [
            If(sop & self.i.stb & self.i.ack,
                sel1.eq(sel0),
                sop.eq(0),
            ),
            If(self.i.eop,
                sop.eq(1),
            ),
        ]
        self.comb += [
            sel.eq(Mux(sop, sel0, sel1)),
            payload.raw_bits().eq(self.i.payload.raw_bits() -
                                  Mux(sop, Array(self.offsets)[sel], 0)),
            [[
                o.payload.eq(payload),
                o.eop.eq(self.i.eop),
            ] for o in self.o],
            Array([o.stb for o in self.o])[sel].eq(self.i.stb),
            self.i.ack.eq(Array([o.ack for o in self.o])[sel]),
        ]


class ReplySwitch(Module):
    def __init__(self, num_ports, width):
        self.layout = [("data", width)]
        self.i = [Endpoint(self.layout) for _ in range(num_ports)]
        self.o = Endpoint(self.layout)
        self.offsets = [Signal(width) for _ in range(num_ports)]

        ###

        sel0 = Signal(max=num_ports)
        sel1 = Signal(max=num_ports)
        sel = Signal(max=num_ports)
        sop = Signal()

        for j in range(num_ports):
            self.comb += [
                If(self.i[j].stb,
                    sel0.eq(j),
                ),
            ]
        self.sync += [
            If(sop & self.o.stb & self.o.ack,
                sel1.eq(sel0),
                sop.eq(0),
            ),
            If(self.o.eop,
                sop.eq(1),
            ),
        ]
        self.comb += [
            sel.eq(Mux(sop, sel0, sel1)),
            self.o.payload.raw_bits().eq(
                Array([i.payload.raw_bits() for i in self.i])[sel] +
                Mux(sop, Array(self.offsets)[sel0], 0)),
            self.o.stb.eq(Array([i.stb for i in self.i])[sel]),
            self.o.eop.eq(Array([i.eop for i in self.i])[sel]),
            Array([i.ack for i in self.i])[sel].eq(self.o.ack),
        ]


class Switch(Module):
    def __init__(self, num_ports, width=16):
        self.submodules.req = RequestSwitch(num_ports, width)
        self.submodules.rep = ReplySwitch(num_ports, width)
        self.offsets = self.req.offsets
        self.comb += [i.eq(j) for i, j in
                      zip(self.rep.offsets, self.req.offsets)]
