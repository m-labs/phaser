from migen.build.generic_platform import *
from migen.build.xilinx import XilinxPlatform, VivadoProgrammer


_io = [
    ("user_led", 0, Pins("AP8"), IOStandard("LVCMOS18")),

    ("user_btn_c", 0, Pins("AE10"), IOStandard("LVCMOS18")),

    ("clk125", 0,
        Subsignal("p", Pins("G10"), IOStandard("LVDS")),
        Subsignal("n", Pins("F10"), IOStandard("LVDS"))
    ),
]


_connectors = [
]


class Platform(XilinxPlatform):
    default_clk_name = "clk125"
    default_clk_period = 8.

    def __init__(self):
        XilinxPlatform.__init__(self, "xcku040-ffva1156-2-e", _io, _connectors,
                                toolchain="vivado")
        self.toolchain.bitstream_commands = ["set_property BITSTREAM.CONFIG.SPI_BUSWIDTH 4 [current_design]"]
        self.toolchain.additional_commands = ["write_cfgmem -force -format bin -interface spix4 -size 16 -loadbit \"up 0x0 {build_name}.bit\" -file {build_name}.bin"]
