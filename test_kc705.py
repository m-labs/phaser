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
        self.comb += [[
            chs[i].q_adjacent[j][0].eq(chs[i + 1].q_adjacent[j][1]),
            chs[i + 1].q_adjacent[j][0].eq(chs[i].q_adjacent[j][1]),
        ] for i in range(0, len(chs), 2) for j in range(len(chs[0].o))]
        dat = Cat([[_.stb, _.payload.flatten()] for ch in chs for _ in ch.i])
        sr = Signal(len(dat))
        self.sync += sr.eq(Cat(i, sr)), dat.eq(sr)

        platform.add_extension(dumb)
        o = Signal((width, True))
        for ch in chs:
            for oi in ch.o:
                o0, o = o, Signal.like(o)
                self.sync += o.eq(o0 + oi)
        h = platform.request("data")
        self.sync += h.eq(o)


if __name__ == "__main__":
    platform = kc705.Platform()
    top = Top(platform)
    platform.build(top)
