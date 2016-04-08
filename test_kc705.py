from migen import *
from migen.build.platforms import kc705
from migen.build.generic_platform import *

from sawg import Channel

dumb = [
    ("data", 0, Pins("LPC:LA15_N LPC:LA16_N LPC:LA15_P LPC:LA16_P "
                     "LPC:LA11_N LPC:LA12_N LPC:LA11_P LPC:LA12_P "
                     "LPC:LA07_N LPC:LA08_N LPC:LA07_P LPC:LA08_P "
                     "LPC:LA04_N LPC:LA03_N LPC:LA04_P LPC:LA03_P"),
     IOStandard("LVTTL")),
]


class Top(Module):
    def __init__(self, platform):
        i = platform.request("cpu_reset")
        width = 16
        chs = [Channel(width, parallelism=8) for i in range(8)]
        self.submodules += chs
        # wire up q exchange
        self.comb += [[
            chs[i].q_i[j].eq(chs[i + 1].q_o[j]),
            chs[i + 1].q_i[j].eq(chs[i].q_o[j]),
        ] for i in range(0, len(chs), 2) for j in range(len(chs[0].o))]

        # just take random data from a sr to prevent folding
        dat = Cat([[_.stb, _.payload.flatten()] for ch in chs for _ in ch.i])
        sr = Signal(len(dat))
        self.sync += sr.eq(Cat(i, sr)), dat.eq(sr)

        # add all outputs together to prevent folding
        platform.add_extension(dumb)
        o = Signal((width, True))
        for ch in chs:
            for oi in ch.o:
                o0, o = o, Signal.like(o)
                self.sync += o.eq(o0 + oi)
        self.sync += platform.request("data").eq(o)


if __name__ == "__main__":
    platform = kc705.Platform()
    top = Top(platform)
    platform.build(top)
