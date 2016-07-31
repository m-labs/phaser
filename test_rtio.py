import numpy as np

from migen import *
from migen.fhdl.verilog import convert

from rtio_sawg import Channel
from tools import xfer, szip


def rtio_xfer(dut, **kwargs):
    yield from szip(*(
        xfer(dut.phys_names[k].rtlink, o={"data": v})
        for k, v in kwargs.items()))


def gen_rtio(dut):
    width = dut.width
    # iq=0b11, clr=0b1, tap=0b00000
    yield from rtio_xfer(dut, cfg=0b11100000)
    yield
    f0 = int(157/(200*8)*2**(4*width))
    f1 = int(81/200*2**(3*width))
    f2 = int(5/200*2**(3*width))
    a1 = int(.087*2**width)
    a2 = int(.95*a1)
    print(hex(f0), hex(f1), hex(a1), hex(a2))
    yield from rtio_xfer(
        dut,
        u=0,
        f0=f0, p0=0,
        a1=a1, f1=f1, p1=0,
        a2=a2, f2=f2, p2=0,
    )


def gen_log(dut, o, n):
    for i in range(3 + dut.latency):
        yield
    for i in range(n):
        yield
        o.append((yield from [(yield _) for _ in dut.o]))


def _test_channel():
    width = 16
    dut = Channel(width=width, parallelism=8)

    if False:
        print(convert(dut))
        return

    o = []
    run_simulation(
        dut,
        [gen_rtio(dut), gen_log(dut, o, 256 * 32)],
    )  # vcd_name="dds.vcd")
    o = np.array(o)/(1 << (width - 1))
    o = o.ravel()
    np.savez_compressed("dds.npz", o=o)

    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(2)
    ax[0].step(np.arange(o.size), o)
    ax[1].psd(o, 1 << 10, Fs=1, noverlap=1 << 9, scale_by_freq=False)
    fig.savefig("dds.pdf")
    plt.show()


if __name__ == "__main__":
    _test_channel()
