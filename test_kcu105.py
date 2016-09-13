from migen import *
from migen.build.generic_platform import *

from sawg import Channel
import kcu105


class Top(Module):
    def __init__(self, platform):
        assert platform.default_clk_period
        platform.default_clk_period = 4

        width = 16
        chs = [Channel(width, parallelism=4) for i in range(4)]
        self.submodules += chs
        # wire up q exchange
        for i in range(0, len(chs), 2):
            chs[i].connect_q(chs[i + 1])
            chs[i + 1].connect_q(chs[i])

        # just take random data from a sr to prevent folding
        inp = platform.request("user_btn_c")
        dat = Cat([[_.stb, _.payload.flatten()] for ch in chs for _ in ch.i])
        sr = Signal(len(dat))
        self.sync += sr.eq(Cat(inp, sr)), dat.eq(sr)

        # add all outputs together to prevent folding
        o = Signal((width, True))
        for ch in chs:
            for oi in ch.o:
                o0, o = o, Signal.like(o)
                self.sync += o.eq(o0 + oi)
        self.sync += platform.request("user_led").eq(o[-1])


if __name__ == "__main__":
    platform = kcu105.Platform()
    top = Top(platform)
    platform.build(top, build_dir="build_kcu105_250mhz")
