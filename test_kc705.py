from migen import *
from migen.build.platforms import kc705
from migen.build.generic_platform import *

from sawg import DDSPair

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
        ch = DDSPair(width, parallelism=8)
        self.submodules += ch
        dat = Cat([ch.ce, ch.iq] + [[_.stb, _.payload.flatten()]
                                    for _ in ch.i])
        sr = Signal(len(dat))
        self.sync += sr.eq(Cat(i, sr)), dat.eq(sr)

        platform.add_extension(dumb)
        o = Signal((width, True))
        self.sync += o.eq(sum(_[0] + _[1] for _ in ch.o))
        for i in range(16):  # balance
            o, o0 = Signal.like(o), o
            self.sync += o.eq(o0)
        h = platform.request("data")
        self.comb += h.eq(o)


if __name__ == "__main__":
    platform = kc705.Platform()
    top = Top(platform)
    platform.build(top)
