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
        self.p = p.i
        self.i = [a.i, f.i, self.p]
        self.o = [[Signal((width, True)) for i in range(2)]
                  for i in range(parallelism)]
        self.ce = Signal()
        self.clr = Signal()
        self.parallelism = parallelism
        self.latency = 0  # will be accumulated

        ###

        self.latency += p.latency
        assert p.latency == 1
        q = PhasedAccu(f_width, parallelism)
        self.submodules += q
        self.latency += q.latency
        da = [Signal((width, True)) for i in range(q.latency)]

        self.sync += [
            If(q.i.stb & q.i.ack,
                da[0][-a_width:].eq(a.o.a0[-width:]),
                [da[i + 1].eq(da[i]) for i in range(len(da) - 1)],
            ),
        ]
        self.comb += [
            a.o.ack.eq(self.ce),
            p.o.ack.eq(self.ce),
            f.o.ack.eq(self.ce),
            q.i.stb.eq(self.ce),
            q.i.p[-p_width:].eq(p.o.a0[-f_width:]),
            q.i.f.eq(f.o.a0),
            q.i.clr.eq(self.clr),
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


class Config(Module):
    def __init__(self):
        self.cfg = Record([("iq", 2), ("tap", 4), ("clr", 1)])
        self.i = Endpoint(self.cfg.layout)
        self.ce = Signal()

        ###

        n = Signal(1 << len(self.i.tap))
        tap = Signal.like(self.i.tap)

        self.comb += [
            self.i.ack.eq(1),
            self.ce.eq(Array([1] + list(n))[tap]),
        ]
        self.sync += [
            n.eq(n + 1),
            If(self.i.stb,
                n.eq(0),
                self.cfg.eq(self.i.payload),
            ),
        ]


class Channel(Module):
    def __init__(self, width=16, **kwargs):
        du = Spline(width=width*4, order=4)
        da = DDS(width, **kwargs)
        cfg = Config()
        self.submodules += du, da, cfg
        self.i = [cfg.i, du.i] + da.i
        self.q_adjacent = [(Signal((width, True)), Signal((width, True)))
                           for i in range(da.parallelism)]
        self.o = [Signal((width, True)) for i in range(da.parallelism)]
        self.parallelism = da.parallelism
        self.latency = da.latency + 1
        self.cordic_gain = da.gain

        ###

        ddu = Delay((width, True), da.latency - du.latency)
        self.submodules += ddu
        self.comb += [
            ddu.i.eq(du.o.a0[-width:]),
            da.ce.eq(cfg.ce),
            da.clr.eq(cfg.cfg.clr),
            du.o.ack.eq(cfg.ce),
        ]
        for oi, ai, qi in zip(self.o, da.o, self.q_adjacent):
            self.sync += [
                oi.eq(ddu.o +
                      Mux(cfg.cfg.iq[0], ai[0], 0) +
                      Mux(cfg.cfg.iq[1], qi[0], 0)),
                qi[1].eq(ai[1]),
            ]
