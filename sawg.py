from migen import *
from misoc.interconnect.stream import Endpoint

from cordic import Cordic
from spline import Spline
from accu import PhasedAccu
from tools import Delay


class DDS(Module):
    def __init__(self, width, t_width=None,
                 a_width=None, p_width=None, f_width=None,
                 a_order=4, p_order=1, f_order=2, parallelism=8):
        if t_width is None:
            t_width = width
        if a_width is None:
            a_width = width + (a_order - 1)*t_width
        if p_width is None:
            p_width = width + (p_order - 1)*t_width
        if f_width is None:
            f_width = width + (f_order + 1)*t_width
        a = Spline(order=a_order, width=a_width)
        p = Spline(order=p_order, width=p_width)
        f = Spline(order=f_order, width=f_width)
        self.submodules += a, p, f

        self.a = a.tri(t_width)
        self.f = f.tri(t_width)
        self.p = p.tri(t_width)
        self.i = [self.a, self.f, self.p]
        self.o = [[Signal((width, True)) for i in range(2)]
                  for i in range(parallelism)]
        self.ce = Signal()
        self.clr = Signal()
        self.parallelism = parallelism
        self.latency = 0  # will be accumulated

        ###

        self.latency += p.latency
        q = PhasedAccu(f_width, parallelism)
        self.submodules += q
        self.latency += q.latency
        da = [Signal((width, True)) for i in range(q.latency)]

        self.sync += [
            If(q.i.stb & q.i.ack,
                da[0][-a_width:].eq(a.o.a0[-width:]),
                [da[i + 1].eq(da[i]) for i in range(len(da) - 1)],
            ),
            If(p.o.stb & p.o.ack,
                q.i.clr.eq(0),
            ),
            If(p.i.stb & p.i.ack,
                q.i.clr.eq(self.clr),
            ),
        ]
        self.comb += [
            a.o.ack.eq(self.ce),
            p.o.ack.eq(self.ce),
            f.o.ack.eq(self.ce),
            q.i.stb.eq(self.ce),
            q.i.p[-p_width:].eq(p.o.a0[-f_width:]),
            q.i.f.eq(f.o.a0),
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
        self.cfg = Record([("tap", 5), ("clr", 1), ("iq", 2)])
        self.i = Endpoint(self.cfg.layout)
        self.ce = Signal()

        ###

        n = Signal(1 << len(self.i.tap))
        tap = Signal.like(self.i.tap)
        clk = Signal()
        clk0 = Signal()

        self.comb += [
            self.i.ack.eq(1),
            clk.eq(Array(n)[tap]),
        ]
        self.sync += [
            clk0.eq(clk),
            self.ce.eq(0),
            If(clk0 ^ clk,
                self.ce.eq(1),
            ),
            n.eq(n + 1),
            If(self.i.stb,
                n.eq(0),
                self.cfg.eq(self.i.payload),
            ),
        ]


class Channel(Module):
    def __init__(self, width=16, t_width=None, u_order=4, **kwargs):
        if t_width is None:
            t_width = width
        du = Spline(width=width + (u_order - 1)*t_width, order=u_order)
        da = DDS(width, t_width, **kwargs)
        cfg = Config()
        self.submodules += du, da, cfg
        self.i = [cfg.i, du.tri(t_width)] + da.i
        self.q_i = [Signal((width, True)) for i in range(da.parallelism)]
        self.q_o = [ai[1] for ai in da.o]
        self.o = [Signal((width, True)) for i in range(da.parallelism)]
        self.parallelism = da.parallelism
        self.latency = da.latency + 1
        self.cordic_gain = da.gain

        ###

        # delay du to match da
        ddu = Delay((width, True), da.latency - du.latency)
        self.submodules += ddu
        self.comb += [
            ddu.i.eq(du.o.a0[-width:]),
            da.clr.eq(cfg.cfg.clr),
            da.ce.eq(cfg.ce),
            du.o.ack.eq(cfg.ce),
        ]
        # wire up outputs and q_{i,o} exchange
        for oi, ai, qi in zip(self.o, da.o, self.q_i):
            self.sync += [
                oi.eq(ddu.o +
                      Mux(cfg.cfg.iq[0], ai[0], 0) +
                      Mux(cfg.cfg.iq[1], qi, 0)),
            ]

    def connect_q(self, buddy):
        for i, qi in enumerate(self.q_i):
            self.comb += qi.eq(buddy.q_o[i])
