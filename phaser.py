from migen import *


class Phaser(Module):
    def __init__(self, factory, parallelism=8):
        q = factory(step=1)
        p = [factory(step=parallelism) for i in range(parallelism)]

        self.i = q.i
        self.o = [pi.o for pi in p]
        self.ce = Signal()
        self.busy = Signal()
        self.parallelism = parallelism
        self.latency = q.latency*parallelism + p[-1].latency

        ###

        self.submodules += q, p

        n = Signal(max=parallelism)
        shift = Signal()
        self.comb += [
            self.busy.eq(n != 0),
            q.ce.eq(q.i.stb | self.busy),
            p[-1].i.payload.eq(q.o.payload),
            p[-1].i.stb.eq(shift & ~self.busy),
            [pi.i.stb.eq(p[-1].i.stb) for pi in p[:-1]],
            [pi.ce.eq(self.ce) for pi in p],
        ]
        self.sync += [
            If(n == 0,
                If(p[-1].i.ack,
                    shift.eq(0),
                ),
            ).Elif(q.o.stb,
                [p[i].i.payload.eq(p[i + 1].i.payload)
                 for i in range(parallelism - 1)],
                n.eq(n - 1),
            ),
            If(q.i.stb,
                shift.eq(1),
                n.eq(parallelism - 1),
            ),
        ]
