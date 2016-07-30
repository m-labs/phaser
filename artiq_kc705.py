import argparse

from migen import *
from migen.build.generic_platform import *

from misoc.targets.kc705 import soc_kc705_args, soc_kc705_argdict
from misoc.integration.builder import builder_args, builder_argdict

from artiq.gateware.soc import build_artiq_soc
from artiq.gateware.targets import kc705
from artiq.gateware import rtio, nist_clock
from artiq.gateware.rtio.phy import ttl_simple, ttl_serdes_7series

import rtio_sawg


class Phaser(kc705._NIST_Ions):
    def __init__(self, cpu_type="or1k", **kwargs):
        kc705._NIST_Ions.__init__(self, cpu_type, **kwargs)

        platform = self.platform
        platform.add_extension(nist_clock.fmc_adapter_io)

        rtio_channels = []

        phy = ttl_serdes_7series.Inout_8X(platform.request("user_sma_gpio_n_33"))
        self.submodules += phy
        rtio_channels.append(rtio.Channel.from_phy(phy, ififo_depth=128))

        phy = ttl_simple.Output(platform.request("user_led", 2))
        self.submodules += phy
        rtio_channels.append(rtio.Channel.from_phy(phy))

        self.config["RTIO_REGULAR_TTL_COUNT"] = len(rtio_channels)

        self.config["RTIO_FIRST_PHASER_CHANNEL"] = len(rtio_channels)

        Channel = ClockDomainsRenamer("rio_phy")(rtio_sawg.Channel)
        sawgs = [Channel(width=16, parallelism=8) for i in range(4)]
        self.submodules += sawgs
        for i in range(0, len(sawgs), 2):
            sawgs[i].connect_q(sawgs[i + 1])
            sawgs[i + 1].connect_q(sawgs[i])

        # TODO: dummy
        o = Signal((16, True))
        for ch in sawgs:
            for oi in ch.o:
                o0, o = o, Signal.like(o)
                self.sync += o.eq(o0 + oi)
        self.sync.rio_phy += platform.request("dds").d.eq(o)

        # TODO: support wider RTIO (data) channels
        # (64 bit is fine here for testing)
        rtio_channels.extend(rtio.Channel.from_phy(phy)
                             for sawg in sawgs
                             for phy in sawg.phys)

        self.config["RTIO_LOG_CHANNEL"] = len(rtio_channels)
        rtio_channels.append(rtio.LogChannel())
        self.add_rtio(rtio_channels)

        self.config["RTIO_FIRST_DDS_CHANNEL"] = len(rtio_channels)
        self.config["RTIO_DDS_COUNT"] = 0
        self.config["DDS_CHANNELS_PER_BUS"] = 1
        self.config["DDS_AD9914"] = True
        self.config["DDS_ONEHOT_SEL"] = True
        self.config["DDS_RTIO_CLK_RATIO"] = 24 >> self.rtio.fine_ts_width
        assert self.rtio.fine_ts_width <= 3


def main():
    parser = argparse.ArgumentParser(
        description="ARTIQ core device builder / KC705 / Phaser")
    builder_args(parser)
    soc_kc705_args(parser)
    parser.set_defaults(toolchain="vivado")
    args = parser.parse_args()
    soc = Phaser(**soc_kc705_argdict(args))
    build_artiq_soc(soc, builder_argdict(args))


if __name__ == "__main__":
    main()
