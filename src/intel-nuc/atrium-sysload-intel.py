#!/usr/bin/python3
# atrium-sysload - CPU and Intel GPU load for the GNOME top bar.
# 2026-10-04: GPU engine busyness comes from intel_gpu_top (Intel's tool, reads the i915 PMU; needs
# only CAP_PERFMON), CPU load from /proc/stat. Once a second one line is written to
# /run/atrium-sysload/panel, e.g. "CPU 12%   GPU 34%   VIDEO 5%":
#   GPU = Render/3D engine (drawing: desktop, browser, mpv shaders),
#   VIDEO = Video engine (hardware video decoding; 0 while a video plays = decoded by the CPU).
# The Executor extension shows the file in the top bar (cat every second).
import os
import subprocess
import sys

OUT = "/run/atrium-sysload/panel"
FIG = "\u2007"  # figure space (as wide as a digit) pads numbers, so the text does not jump


def cpu_times():
    with open("/proc/stat") as f:
        v = [int(x) for x in f.readline().split()[1:9]]  # user nice system idle iowait irq softirq steal
    return sum(v), v[3] + v[4]


def pct(x):
    return (str(round(x)) + "%").ljust(4, FIG)


def write(text):
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text + "\n")
    os.replace(tmp, OUT)


def main():
    gpu_top = subprocess.Popen(["/usr/bin/intel_gpu_top", "-c", "-s", "1000"],
                               stdout=subprocess.PIPE, text=True)
    header = gpu_top.stdout.readline().strip().split(",")
    rcs, vcs = header.index("RCS %"), header.index("VCS %")
    total0, idle0 = cpu_times()
    for line in gpu_top.stdout:
        total1, idle1 = cpu_times()
        busy = (total1 - total0) - (idle1 - idle0)
        cpu = 100.0 * busy / (total1 - total0) if total1 > total0 else 0.0
        total0, idle0 = total1, idle1
        fields = line.strip().split(",")
        try:
            gpu, dec = float(fields[rcs]), float(fields[vcs])
        except (IndexError, ValueError):
            continue
        write(f"CPU {pct(cpu)}   GPU {pct(gpu)}   VIDEO {pct(dec)}")
    sys.exit(f"intel_gpu_top exited with code {gpu_top.wait()}")


if __name__ == "__main__":
    main()
