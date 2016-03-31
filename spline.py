from migen import *
from misoc.interconnect.stream import Endpoint


class Spline(Module):
    def __init__(self, order, width, step=1):
        if not (step == 1 or order <= 2):
            raise ValueError("For non-linear splines, "
                             "`step` needs to be one.")
        layout = [("a{}".format(i), (width, True)) for i in range(order)]
        self.i = Endpoint(layout)
        self.o = Endpoint(layout)
        self.latency = 1

        ###

        o = self.o.payload.flatten()

        self.comb += self.i.ack.eq(~self.o.stb | self.o.ack)
        self.sync += [
            If(self.o.ack,
                self.o.stb.eq(0),
            ),
            If(self.i.ack,
                self.o.stb.eq(1),
                [o[i].eq(o[i] + (o[i + 1] << log2_int(step)))
                 for i in range(order - 1)],
                If(self.i.stb,
                    self.o.payload.eq(self.i.payload),
                ),
            ),
        ]
