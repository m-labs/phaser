import argparse

from migen import *
from migen.build.generic_platform import *

from misoc.targets.kc705 import soc_kc705_args, soc_kc705_argdict
from misoc.integration.builder import builder_args, builder_argdict

from artiq.gateware.soc import build_artiq_soc
from artiq.gateware.targets import kc705
from artiq.gateware import rtio
from artiq.gateware.rtio.phy import ttl_simple, ttl_serdes_7series

import rtio_sawg


class Phaser(kc705._NIST_Ions):
    def __init__(self, cpu_type="or1k", **kwargs):
        kc705._NIST_Ions.__init__(self, cpu_type, **kwargs)

        platform = self.platform

        rtio_channels = []

        phy = ttl_serdes_7series.Inout_8X(platform.request("user_sma_gpio_n"))
        self.submodules += phy
        rtio_channels.append(rtio.Channel.from_phy(phy, ififo_depth=128))

        phy = ttl_simple.Output(platform.request("user_led", 2))
        self.submodules += phy
        rtio_channels.append(rtio.Channel.from_phy(phy))

        self.config["RTIO_REGULAR_TTL_COUNT"] = len(rtio_channels)

        self.config["RTIO_FIRST_PHASER_CHANNEL"] = len(rtio_channels)

        sawgs = [rtio_sawg.Channel(width=16, parallelism=8)
                 for i in range(4)]
        self.submodules += sawgs
        # TODO: wire up sawg.o[:parallelism, :width]
        # TODO: support wider RTIO (data) channels (fine here for testing)
        for i in range(0, len(sawgs), 2):
            sawgs[i].connect_q(sawgs[i + 1])
            sawgs[i + 1].connect_q(sawgs[i])
        rtio_channels.extend(rtio.Channel.from_phy(phy)
                             for sawg in sawgs
                             for phy in sawg.phys)
        self.config["RTIO_LOG_CHANNEL"] = len(rtio_channels)
        rtio_channels.append(rtio.LogChannel())
        self.add_rtio(rtio_channels)
        assert self.rtio.fine_ts_width <= 3

        #self.config["RTIO_FIRST_SPI_CHANNEL"] = len(rtio_channels)
        #self.config["RTIO_FIRST_DDS_CHANNEL"] = len(rtio_channels)
        #self.config["RTIO_DDS_COUNT"] = 0
        #self.config["DDS_CHANNELS_PER_BUS"] = 11
        #self.config["DDS_AD9914"] = True
        #self.config["DDS_ONEHOT_SEL"] = True
        #self.config["DDS_RTIO_CLK_RATIO"] = 24 >> self.rtio.fine_ts_width



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
