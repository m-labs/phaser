from migen import *
from misoc.interconnect.stream import Endpoint

from cordic import Cordic
from spline import Spline
from accu import PhasedAccu
from tools import Delay


class DDS(Module):
    def __init__(self, width, a_width=None, p_width=None, f_width=None,
                 a_order=4, p_order=1, f_order=2, parallelism=8):
        if a_width is None:
            a_width = a_order*width
        if p_width is None:
            p_width = p_order*width
        if f_width is None:
            f_width = (f_order + 1)*width
        a = Spline(order=a_order, width=a_width)
        p = Spline(order=p_order, width=p_width)
        f = Spline(order=f_order, width=f_width)
        self.submodules += a, p, f

        self.a = a.i
        self.f = f.i
        self.p = Endpoint(p.i.payload.layout + [("clr", 1)])
        self.i = [a.i, f.i, self.p]
        self.o = [[Signal((width, True)) for i in range(2)]
                  for i in range(parallelism)]
        self.ce = Signal()
        self.parallelism = parallelism
        self.latency = 0  # will be accumulated

        ###

        self.latency += p.latency
        assert p.latency == 1
        q = PhasedAccu(f_width, parallelism)
        self.submodules += q
        self.latency += q.latency
        c = Signal()
        da = [Signal((width, True)) for i in range(q.latency)]

        self.sync += [
            If(q.i.stb & q.i.ack,
                c.eq(0),
                da[0][-a_width:].eq(a.o.a0[-width:]),
                [da[i + 1].eq(da[i]) for i in range(len(da) - 1)],
            ),
            If(self.p.stb & self.p.ack,
                c.eq(self.p.clr),
            ),
        ]
        self.comb += [
            self.p.connect(p.i, leave_out={"clr"}),
            a.o.ack.eq(self.ce),
            p.o.ack.eq(self.ce),
            f.o.ack.eq(self.ce),
            q.i.stb.eq(self.ce),
            q.i.p[-p_width:].eq(p.o.a0[-f_width:]),
            q.i.f.eq(f.o.a0),
            q.i.clr.eq(c),
            q.o.ack.eq(1),
        ]

        c = []
        for i in range(parallelism):
            ci = Cordic(width=width, widthz=p_width,
                        guard=None, eval_mode="pipelined")
            self.submodules += ci
            c.append(ci)
            qoi = getattr(q.o, "z{}".format(i))
            self.comb += [
                ci.xi.eq(da[-1]),
                ci.yi.eq(0),
                ci.zi[-f_width:].eq(qoi[-p_width:]),
                self.o[i][0][-len(ci.xo):].eq(ci.xo[-width:]),
                self.o[i][1][-len(ci.yo):].eq(ci.yo[-width:]),
            ]
        self.latency += c[0].latency
        self.gain = c[0].gain


class DDSPair(Module):
    def __init__(self, width=16, **kwargs):
        du = Spline(width=width*4, order=4)
        dv = Spline(width=width*4, order=4)
        da = DDS(width, **kwargs)
        db = DDS(width, **kwargs)
        self.submodules += du, dv, da, db
        self.i = [du.i, dv.i] + da.i + db.i
        self.o = [(Signal((width, True)), Signal((width, True)))
                  for i in range(da.parallelism)]
        self.parallelism = da.parallelism
        self.latency = da.latency + 1
        self.cordic_gain = da.gain
        self.iq = Signal(4)
        self.ce = Signal()

        ###

        ddu, ddv = (Delay((width, True), da.latency - du.latency)
                    for i in range(2))
        self.submodules += ddu, ddv
        self.comb += [
            [d.i.eq(u.o.a0[-width:]) for d, u in zip((ddu, ddv), (du, dv))],
            [_.ce.eq(self.ce) for _ in (da, db)],
            [_.o.ack.eq(self.ce) for _ in (du, dv)],
        ]
        for oi, ai, bi in zip(self.o, da.o, db.o):
            self.sync += [
                oi[0].eq(ddu.o +
                         Mux(self.iq[0], ai[0], 0) +
                         Mux(self.iq[1], bi[0], 0)),
                oi[1].eq(ddv.o +
                         Mux(self.iq[2], ai[1], 0) +
                         Mux(self.iq[3], bi[1], 0)),
            ]
