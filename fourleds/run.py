"""Can a person steer a camera onto a target with four on/off LEDs?

The 2024 rig: YOLOv5 finds a bottle, a laptop compares it to an "ideal"
position, and an Arduino lights red/green/white/blue for left/right/up/down,
or sounds a buzzer when you're within 50 px. That is a human-in-the-loop
controller whose only sensor is four bits.

A person is modelled the way control textbooks do it: they see the display
~250 ms late, then move their hand at a comfortable speed in the direction
it says, with some tremor. Two displays are compared:

  bang-bang:    the 2024 LEDs — on or off per direction
  proportional: the same LEDs dimmed by PWM in proportion to the error,
                so the person slows down as they get close

    python -m fourleds.run           # prints the table, writes assets/*.png
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

DT = 0.01            # 100 Hz simulation
REACTION_S = 0.25    # typical visual reaction delay
HAND_PX_S = 600.0    # comfortable hand speed, as seen in pixels
TREMOR_PX_S = 25.0
DETECT_HZ = 15       # YOLOv5s on a laptop CPU, roughly
ASSETS = Path(__file__).resolve().parent.parent / "assets"


def display(err: np.ndarray, deadband: float, mode: str) -> np.ndarray:
    """What the LEDs tell the person to do, per axis, in [-1, 1]."""
    if mode == "bang-bang":
        return np.where(np.abs(err) > deadband, -np.sign(err), 0.0)
    g = np.clip(-err / (4 * deadband), -1, 1)  # full brightness at 4x the deadband
    return np.where(np.abs(err) > deadband, g, 0.0)


def trial(deadband: float, mode: str, rng: np.random.Generator, seconds: float = 8.0):
    n = int(seconds / DT)
    lag = int(REACTION_S / DT)
    hold = int(1 / DETECT_HZ / DT)
    x = rng.uniform(-220, 220, 2)
    shown = np.zeros(2)
    log, cmds = np.zeros((n, 2)), np.zeros((n, 2))
    for k in range(n):
        if k % hold == 0:  # a fresh detection updates the LEDs
            shown = display(x, deadband, mode)
        cmds[k] = shown
        act = cmds[k - lag] if k >= lag else np.zeros(2)
        x = x + (act * HAND_PX_S + rng.normal(0, TREMOR_PX_S, 2)) * DT
        log[k] = x
    return log


def score(log: np.ndarray, deadband: float):
    inside = np.all(np.abs(log) <= deadband, axis=1)
    # settled = inside for the final 1 s without leaving again
    last_out = np.where(~inside)[0]
    settle = (last_out[-1] + 1) * DT if len(last_out) else 0.0
    settled = settle <= len(log) * DT - 1.0
    # hunting: how many times the x-indicator flips direction
    sx = np.sign(np.where(np.abs(log[:, 0]) > deadband, log[:, 0], 0))
    sx = sx[sx != 0]
    flips = int(np.sum(sx[1:] != sx[:-1]))
    return settle if settled else np.nan, flips


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    deadbands = np.array([10, 20, 30, 40, 50, 75, 100])
    trials = 200
    rows = {}
    for mode in ("bang-bang", "proportional"):
        rng = np.random.default_rng(2024)
        res = []
        for db in deadbands:
            s = [score(trial(db, mode, rng), db) for _ in range(trials)]
            t = np.array([a for a, _ in s])
            res.append((np.nanmedian(t) if np.any(~np.isnan(t)) else np.nan,
                        np.mean(np.isnan(t)) * 100, np.median([b for _, b in s])))
        rows[mode] = res

    plt.rcParams.update({"font.family": "DejaVu Sans Mono", "font.size": 10})
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4), dpi=150)
    for mode, c in (("bang-bang", "#b3261e"), ("proportional", "#1f4e8c")):
        a1.plot(deadbands, [r[0] for r in rows[mode]], "o-", color=c, lw=2, label=mode)
        a2.plot(deadbands, [r[1] for r in rows[mode]], "o-", color=c, lw=2, label=mode)
    a1.axvline(50, color="k", lw=0.8, alpha=0.35)
    a2.axvline(50, color="k", lw=0.8, alpha=0.35)
    a1.set_xlabel("buzzer zone half-width (px)")
    a1.set_ylabel("median time to settle (s)")
    a2.set_xlabel("buzzer zone half-width (px)")
    a2.set_ylabel("never settled within 8 s (%)")
    a1.legend(frameon=False)
    for ax in (a1, a2):
        ax.grid(alpha=0.25)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(ASSETS / "deadband_sweep.png")
    plt.close(fig)

    # One person, one try, at the 2024 setting and at a tight 20 px zone.
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.4), dpi=150, sharey=True)
    for ax, db in zip(axes, (50, 20)):
        for mode, c in (("bang-bang", "#b3261e"), ("proportional", "#1f4e8c")):
            log = trial(db, mode, np.random.default_rng(5))
            ax.plot(np.arange(len(log)) * DT, log[:, 0], color=c, lw=1.6, label=mode)
        ax.axhspan(-db, db, color="#3f6b2a", alpha=0.12, lw=0)
        ax.set_title(f"buzzer zone ±{db} px", fontsize=10, loc="left")
        ax.set_xlabel("time (s)")
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    axes[0].set_ylabel("horizontal error (px)")
    axes[0].legend(frameon=False)
    fig.tight_layout()
    fig.savefig(ASSETS / "one_try.png")
    plt.close(fig)

    print("zone_px  " + "   ".join(f"{m:>34}" for m in rows))
    print("         " + "   ".join(f"{'settle_s  never%  x_flips':>34}" for _ in rows))
    for i, db in enumerate(deadbands):
        print(f"{db:7d}  " + "   ".join(f"{r[i][0]:12.2f}  {r[i][1]:6.1f}  {r[i][2]:7.0f}" for r in rows.values()))


if __name__ == "__main__":
    main()
