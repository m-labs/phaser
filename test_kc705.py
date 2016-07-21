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
        platform.add_extension(dumb)

        width = 16
        chs = [Channel(width, parallelism=8) for i in range(4)]
        self.submodules += chs
        # wire up q exchange
        for i in range(0, len(chs), 2):
            chs[i].connect_q(chs[i + 1])
            chs[i + 1].connect_q(chs[i])

        # just take random data from a sr to prevent folding
        inp = platform.request("cpu_reset")
        dat = Cat([[_.stb, _.payload.flatten()] for ch in chs for _ in ch.i])
        sr = Signal(len(dat))
        self.sync += sr.eq(Cat(inp, sr)), dat.eq(sr)

        # add all outputs together to prevent folding
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
