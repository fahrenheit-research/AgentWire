"""
AgentWire v0.4 Competitive Benchmark — chart generation
=======================================================

Soft pastel palette derived from the gradient-orb reference (May 2026 brief):
  cream paper · deep-navy ink · amber/coral/sky/mint/lemon/lavender accents
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import os

# ===========================================================================
# Design system  (soft pastel — gradient-orb palette)
# ===========================================================================

# Neutrals
PAPER         = "#F4F1E6"
PAPER_DEEP    = "#ECE6D3"
INK           = "#1F2D3D"
INK_SOFT      = "#4A5868"
INK_MUTED     = "#8E96A3"
RULE          = "#D6CFBC"

# Accent palette (soft pastels from the orb)
AMBER         = "#E8B85B"
CORAL         = "#E89176"
SKY           = "#7BC0E6"
MINT          = "#9ECDB6"
LEMON         = "#EFD96A"
LAVENDER      = "#B5A6D4"
SAND          = "#D4B886"
ROSE          = "#E0A4B8"

# Tints (for callout backgrounds)
AMBER_TINT    = "#FAEFD3"
CORAL_TINT    = "#FADDD2"
SKY_TINT      = "#DEF0F9"
MINT_TINT     = "#E2EFE5"
LEMON_TINT    = "#FAF3CD"
LAVENDER_TINT = "#EAE3F0"
ROSE_TINT     = "#F4E0E6"
NEUTRAL_TINT  = "#ECE6D3"

# Format colors
COLORS = {
    "JSON":           "#A8A39A",
    "TOON":           SKY,
    "ZOON":           LAVENDER,
    "ISON":           MINT,
    "TERSE":          AMBER,
    "AgentWire Std":  "#6B7B8E",
    "AgentWire Chmp": SAND,
    "AgentWire Bin":  ROSE,
    "AgentWire v4":   CORAL,
    "AgentWire v4+z": "#C66B4F",
}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9.5,
    "axes.edgecolor": INK_SOFT,
    "axes.labelcolor": INK,
    "axes.titlecolor": INK,
    "xtick.color": INK_SOFT,
    "ytick.color": INK_SOFT,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.7,
    "grid.color": RULE,
    "grid.linewidth": 0.4,
    "grid.linestyle": "--",
    "figure.facecolor": PAPER,
    "axes.facecolor": PAPER,
    "savefig.facecolor": PAPER,
})


def _title_block(fig, title, subtitle=None, top=0.93, left=0.08):
    fig.text(left, top, title, fontsize=13, fontweight="bold", color=INK)
    if subtitle:
        fig.text(left, top - 0.045, subtitle, fontsize=9, color=INK_MUTED)


def _label_payload(p):
    head, _, rest = p.partition(" (")
    return f"{head}\n({rest}"


# ===========================================================================
# Cover hero — gradient orb
# ===========================================================================

def chart_cover_hero(outpath):
    """Stunning full-bleed gradient hero — the orb softly fills the frame,
    fading at the edges to cream so it can sit cleanly under typography."""
    fig = plt.figure(figsize=(9.5, 5.2))
    fig.patch.set_facecolor(PAPER)

    # Single full-bleed axes
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_facecolor(PAPER)

    # Build a sweeping gradient that fills the entire frame, with multiple
    # soft "blobs" of color blended at different points. The blobs are
    # weighted by gaussian distance so the colors blend smoothly.
    n_x, n_y = 480, 260
    xs = np.linspace(0, 1.65, n_x)  # extend right so orb pours off-page
    ys = np.linspace(0, 1, n_y)
    X, Y = np.meshgrid(xs, ys)

    def hex_to_rgb(h):
        h = h.lstrip("#")
        return np.array([int(h[i:i+2], 16) / 255 for i in (0, 2, 4)])

    # Color stops positioned across the frame.
    # (color, (cx, cy), sigma_x, sigma_y, weight)
    stops = [
        (hex_to_rgb(LEMON),    (0.80, 0.92), 0.42, 0.35, 1.0),  # top — lemon
        (hex_to_rgb(AMBER),    (1.20, 0.55), 0.42, 0.45, 1.2),  # right — amber
        (hex_to_rgb(CORAL),    (0.95, 0.30), 0.35, 0.30, 1.0),  # mid-right — coral
        (hex_to_rgb(ROSE),     (0.65, 0.08), 0.45, 0.30, 0.9),  # bottom-mid — rose
        (hex_to_rgb(SKY),      (0.45, 0.20), 0.35, 0.35, 1.0),  # lower-left — sky
        (hex_to_rgb(MINT),     (0.70, 0.55), 0.30, 0.30, 0.7),  # center — mint
    ]

    img = np.zeros((n_y, n_x, 3))
    weight = np.zeros((n_y, n_x))
    cream = hex_to_rgb(PAPER)

    for color, (cx, cy), sx, sy, w in stops:
        d2 = ((X - cx) / sx) ** 2 + ((Y - cy) / sy) ** 2
        wmap = w * np.exp(-d2 / 2)
        for c in range(3):
            img[:, :, c] += wmap * color[c]
        weight += wmap

    # Add cream as the dominant background blob to soften everything
    bg_weight = 0.8 * np.ones_like(weight)
    for c in range(3):
        img[:, :, c] += bg_weight * cream[c]
    weight += bg_weight

    img = img / weight[:, :, None]

    # Strong fade to cream at left edge (so typography sits on clean paper)
    left_fade = np.clip((X - 0.05) / 0.30, 0, 1)
    img = img * left_fade[:, :, None] + cream * (1 - left_fade[:, :, None])

    # Soft fade at top/bottom edges
    top_fade = np.clip((0.96 - Y) / 0.10, 0, 1)
    bot_fade = np.clip((Y - 0.04) / 0.06, 0, 1)
    edge_fade = np.minimum(top_fade, bot_fade)
    img = img * edge_fade[:, :, None] + cream * (1 - edge_fade[:, :, None])

    ax.imshow(img, extent=(0, 1, 0, 1), origin="lower",
              interpolation="bilinear", aspect="auto")

    plt.savefig(outpath, dpi=200, bbox_inches="tight",
                facecolor=PAPER, pad_inches=0)
    plt.close(fig)


# ===========================================================================
# Common bar utilities
# ===========================================================================

def _grouped_bars(ax, results, payloads, encoders, idx, log=True,
                  highlight=("AgentWire v4", "AgentWire v4+z")):
    n_enc = len(encoders)
    width = 0.78 / n_enc
    x = np.arange(len(payloads))

    for i, enc in enumerate(encoders):
        vals = [results[enc][p][idx] for p in payloads]
        ax.bar(x + i * width - 0.39 + width / 2, vals, width,
               color=COLORS[enc], label=enc, zorder=3,
               edgecolor=PAPER, linewidth=0.5)
        if enc in highlight:
            for j, _ in enumerate(payloads):
                ax.bar(x[j] + i * width - 0.39 + width / 2,
                       vals[j], width, fill=False,
                       edgecolor=INK, linewidth=0.9, zorder=4)

    ax.set_xticks(x)
    ax.set_xticklabels([_label_payload(p) for p in payloads],
                       fontsize=8.5, color=INK_SOFT)
    if log:
        ax.set_yscale("log")
    ax.tick_params(axis="both", which="both", length=0)
    ax.grid(axis="y", alpha=0.6, zorder=0)


def _legend_below(ax, encoders, ncol=5):
    handles = [patches.Patch(color=COLORS[e], label=e) for e in encoders]
    ax.legend(handles=handles, loc="upper left",
              bbox_to_anchor=(0, -0.20), ncol=ncol,
              frameon=False, fontsize=8.3, columnspacing=1.2,
              handlelength=1.4, handleheight=0.7)


# ===========================================================================
# Charts
# ===========================================================================

def chart_bytes_grouped(results, payloads, encoders, outpath,
                        title="Body-only size by payload",
                        subtitle=None):
    fig, ax = plt.subplots(figsize=(9.5, 3.9))
    fig.subplots_adjust(top=0.83, bottom=0.27, left=0.08, right=0.97)
    _grouped_bars(ax, results, payloads, encoders, idx=0, log=True)
    ax.set_ylabel("Bytes (log)", fontsize=9, color=INK_SOFT)
    _title_block(fig, title, subtitle)
    _legend_below(ax, encoders, ncol=5)
    plt.savefig(outpath, dpi=180, bbox_inches="tight", facecolor=PAPER)
    plt.close(fig)


def chart_reduction_heatmap(results, payloads, encoders, outpath,
                            title="Byte reduction vs JSON (%)",
                            subtitle=None):
    encs = [e for e in encoders if e != "JSON"]
    matrix = np.zeros((len(encs), len(payloads)))
    for i, enc in enumerate(encs):
        for j, p in enumerate(payloads):
            base = results["JSON"][p][0]
            v = results[enc][p][0]
            matrix[i, j] = (1 - v / base) * 100

    fig, ax = plt.subplots(figsize=(9.5, 5.0))
    fig.subplots_adjust(top=0.85, bottom=0.16, left=0.13, right=0.93)

    cmap = LinearSegmentedColormap.from_list(
        "soft_div",
        [(0, "#B8597A"), (0.50, PAPER), (1, "#3A8AB8")],
    )
    vmax = max(abs(matrix.min()), abs(matrix.max()))
    im = ax.imshow(matrix, cmap=cmap, vmin=-vmax, vmax=vmax, aspect="auto")

    ax.set_xticks(range(len(payloads)))
    ax.set_yticks(range(len(encs)))
    ax.set_xticklabels([_label_payload(p) for p in payloads],
                       fontsize=8, color=INK_SOFT)
    ax.set_yticklabels(encs, fontsize=9, color=INK)

    for i in range(len(encs)):
        for j in range(len(payloads)):
            val = matrix[i, j]
            txt_color = "white" if abs(val) > vmax * 0.55 else INK
            ax.text(j, i, f"{val:+.1f}%", ha="center", va="center",
                    fontsize=8.3, color=txt_color, fontweight="bold")

    _title_block(fig, title, subtitle)
    ax.tick_params(axis="both", which="both", length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)

    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cbar.set_label("larger ◀ % vs JSON ▶ smaller",
                   fontsize=8, color=INK_SOFT)
    cbar.ax.tick_params(labelsize=7.5, colors=INK_SOFT)
    cbar.outline.set_visible(False)

    plt.savefig(outpath, dpi=180, bbox_inches="tight", facecolor=PAPER)
    plt.close(fig)


def chart_tokens_grouped(results, payloads, encoders, outpath,
                         title="Estimated tokens by payload",
                         subtitle=None):
    fig, ax = plt.subplots(figsize=(9.5, 3.9))
    fig.subplots_adjust(top=0.83, bottom=0.27, left=0.08, right=0.97)
    _grouped_bars(ax, results, payloads, encoders, idx=1, log=True)
    ax.set_ylabel("Tokens (log)", fontsize=9, color=INK_SOFT)
    _title_block(fig, title, subtitle)
    _legend_below(ax, encoders, ncol=5)
    plt.savefig(outpath, dpi=180, bbox_inches="tight", facecolor=PAPER)
    plt.close(fig)


def chart_total_summary(results, payloads, encoders, outpath,
                        title="Total bytes across all 6 payloads",
                        metric_idx=0, ylabel="Total bytes",
                        subtitle=None):
    totals = [(enc, sum(results[enc][p][metric_idx] for p in payloads))
              for enc in encoders]
    totals.sort(key=lambda x: x[1])
    labels = [t[0] for t in totals]
    vals = [t[1] for t in totals]
    cols = [COLORS[l] for l in labels]

    fig, ax = plt.subplots(figsize=(9.5, 4.4))
    fig.subplots_adjust(top=0.85, bottom=0.10, left=0.20, right=0.95)
    bars = ax.barh(range(len(labels)), vals, color=cols, zorder=3,
                   edgecolor=PAPER, linewidth=0.6, height=0.72)

    for i, lbl in enumerate(labels):
        if lbl.startswith("AgentWire v4"):
            bars[i].set_edgecolor(INK)
            bars[i].set_linewidth(1.0)

    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=9.5, color=INK)
    ax.invert_yaxis()

    json_val = next(v for l, v in totals if l == "JSON")
    for i, (l, v) in enumerate(totals):
        delta = (1 - v / json_val) * 100
        if l == "JSON":
            delta_txt = "  (baseline)"
        elif abs(delta) < 0.05:
            delta_txt = "  ≈ JSON"
        elif delta > 0:
            delta_txt = f"  {delta:.1f}% smaller"
        else:
            delta_txt = f"  {-delta:.1f}% larger"
        ax.text(v, i, f"  {v:,}{delta_txt}", va="center", ha="left",
                fontsize=8.5, color=INK_SOFT)

    ax.set_xlim(0, max(vals) * 1.55)
    ax.grid(axis="x", alpha=0.5, zorder=0)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", length=0)
    ax.set_xlabel(ylabel, fontsize=9, color=INK_SOFT)
    _title_block(fig, title, subtitle, left=0.20)

    plt.savefig(outpath, dpi=180, bbox_inches="tight", facecolor=PAPER)
    plt.close(fig)


def chart_latency(results, payloads, encoders, outpath,
                  title="Encode latency (p50, μs)",
                  subtitle=None):
    fig, ax = plt.subplots(figsize=(9.5, 3.9))
    fig.subplots_adjust(top=0.83, bottom=0.27, left=0.08, right=0.97)
    _grouped_bars(ax, results, payloads, encoders, idx=2, log=True)
    ax.set_ylabel("μs (log)", fontsize=9, color=INK_SOFT)
    _title_block(fig, title, subtitle)
    _legend_below(ax, encoders, ncol=5)
    plt.savefig(outpath, dpi=180, bbox_inches="tight", facecolor=PAPER)
    plt.close(fig)


def chart_radar(outpath, title="Qualitative format scoring"):
    dims = [
        "Size\nefficiency",
        "Encode\nspeed",
        "Decode\nspeed",
        "Readability",
        "Type\nfidelity",
        "Tooling\nmaturity",
        "Envelope\n& metadata",
    ]
    scores = {
        "JSON":            [2, 5, 5, 4, 3, 5, 1],
        "TOON":            [4, 3, 3, 4, 3, 3, 1],
        "ZOON":            [3, 3, 3, 2, 4, 2, 1],
        "ISON":            [3, 4, 4, 3, 3, 2, 1],
        "TERSE":           [4, 4, 4, 1, 2, 1, 1],
        "AgentWire v0.4":  [5, 4, 4, 2, 5, 4, 5],
    }
    consolidated_colors = {
        "JSON":           COLORS["JSON"],
        "TOON":           COLORS["TOON"],
        "ZOON":           COLORS["ZOON"],
        "ISON":           COLORS["ISON"],
        "TERSE":          COLORS["TERSE"],
        "AgentWire v0.4": CORAL,
    }

    n = len(dims)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(7.0, 6.4), subplot_kw=dict(polar=True))
    fig.subplots_adjust(top=0.90, bottom=0.14)
    ax.set_facecolor(PAPER)
    fig.patch.set_facecolor(PAPER)

    for name, vals in scores.items():
        v = vals + vals[:1]
        c = consolidated_colors[name]
        is_winner = name == "AgentWire v0.4"
        lw = 2.6 if is_winner else 1.0
        alpha_fill = 0.28 if is_winner else 0.05
        ax.plot(angles, v, color=c, linewidth=lw, label=name,
                zorder=3 if is_winner else 2)
        ax.fill(angles, v, color=c, alpha=alpha_fill)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(dims, fontsize=9, color=INK)
    ax.set_yticks([1, 2, 3, 4, 5])
    ax.set_yticklabels(["1", "2", "3", "4", "5"], fontsize=7.5, color=INK_MUTED)
    ax.set_ylim(0, 5)
    ax.spines["polar"].set_color(RULE)
    ax.grid(color=RULE, linewidth=0.5)

    fig.text(0.5, 0.94, title, fontsize=13, fontweight="bold",
             color=INK, ha="center")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.16), ncol=3,
              frameon=False, fontsize=9)

    plt.savefig(outpath, dpi=180, bbox_inches="tight", facecolor=PAPER)
    plt.close(fig)


def chart_winner_showcase(body_results, outpath):
    """A focused chart for the verdict page."""
    targets = [
        ("Array (200 agent records)", "Array · 200 records"),
        ("Mixed (realistic prod)",    "Mixed · realistic"),
        ("Flat (medium, 50 keys)",    "Flat · 50 keys"),
        ("Nested (deep, 4 levels)",   "Nested · depth 4"),
    ]
    series = ["JSON", "TOON", "TERSE", "AgentWire v4", "AgentWire v4+z"]

    fig, ax = plt.subplots(figsize=(9.5, 4.3))
    fig.subplots_adjust(top=0.80, bottom=0.22, left=0.08, right=0.97)

    n = len(series)
    width = 0.78 / n
    x = np.arange(len(targets))

    for i, s in enumerate(series):
        vals = [body_results[s][p][0] for p, _ in targets]
        ax.bar(x + i * width - 0.39 + width / 2, vals, width,
               color=COLORS[s], label=s, zorder=3,
               edgecolor=PAPER, linewidth=0.5)
        if "v4" in s:
            json_vals = [body_results["JSON"][p][0] for p, _ in targets]
            for j, (v, jv) in enumerate(zip(vals, json_vals)):
                pct = (1 - v / jv) * 100
                ax.text(x[j] + i * width - 0.39 + width / 2,
                        v * 1.06, f"−{pct:.0f}%",
                        ha="center", va="bottom",
                        fontsize=7.5, color=INK,
                        fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels([t for _, t in targets], fontsize=9, color=INK_SOFT)
    ax.set_yscale("log")
    ax.set_ylabel("Bytes (log)", fontsize=9, color=INK_SOFT)
    ax.tick_params(axis="both", which="both", length=0)
    ax.grid(axis="y", alpha=0.5, zorder=0)
    _title_block(fig, "AgentWire v0.4 vs the field on four realistic payloads",
                 "Smaller is better. The −% annotations on the coral bars are the savings vs JSON.")
    _legend_below(ax, series, ncol=5)

    plt.savefig(outpath, dpi=180, bbox_inches="tight", facecolor=PAPER)
    plt.close(fig)


def chart_envelope_cost(wire_results, body_results, payloads, outpath,
                        title="AgentWire envelope overhead",
                        subtitle=None):
    encs = ["AgentWire Std", "AgentWire v4", "AgentWire v4+z"]
    fig, ax = plt.subplots(figsize=(9.5, 3.8))
    fig.subplots_adjust(top=0.83, bottom=0.25, left=0.08, right=0.97)

    n_enc = len(encs)
    width = 0.78 / n_enc
    x = np.arange(len(payloads))

    for i, enc in enumerate(encs):
        body_vals = [body_results[enc][p][0] for p in payloads]
        wire_vals = [wire_results[enc][p][0] for p in payloads]
        env_vals = [w - b for w, b in zip(wire_vals, body_vals)]
        ax.bar(x + i * width - 0.39 + width / 2, body_vals, width,
               color=COLORS[enc], zorder=3,
               edgecolor=PAPER, linewidth=0.3)
        ax.bar(x + i * width - 0.39 + width / 2, env_vals, width,
               bottom=body_vals, color=COLORS[enc], alpha=0.35, zorder=3,
               edgecolor=PAPER, linewidth=0.3)

    ax.set_xticks(x)
    ax.set_xticklabels([_label_payload(p) for p in payloads],
                       fontsize=8.5, color=INK_SOFT)
    ax.set_yscale("log")
    ax.set_ylabel("Bytes (log)", fontsize=9, color=INK_SOFT)
    ax.tick_params(axis="both", which="both", length=0)
    ax.grid(axis="y", alpha=0.5, zorder=0)
    _title_block(fig, title, subtitle)

    handles = [
        patches.Patch(facecolor=INK_SOFT, label="Body bytes"),
        patches.Patch(facecolor=INK_SOFT, alpha=0.35, label="Envelope bytes"),
        patches.Patch(facecolor=COLORS["AgentWire Std"], label="Std (JSON body)"),
        patches.Patch(facecolor=COLORS["AgentWire v4"], label="v4 (binary body)"),
        patches.Patch(facecolor=COLORS["AgentWire v4+z"], label="v4 + zstd"),
    ]
    ax.legend(handles=handles, loc="upper left",
              bbox_to_anchor=(0, -0.20), ncol=5,
              frameon=False, fontsize=8.3)
    plt.savefig(outpath, dpi=180, bbox_inches="tight", facecolor=PAPER)
    plt.close(fig)


if __name__ == "__main__":
    import benchmark as bm
    os.makedirs("/home/claude/figs", exist_ok=True)
    print("Running benchmarks…")
    wire = bm.run_all(bm.ENCODERS)
    body = bm.run_all(bm.ENCODERS_BODY_ONLY)
    payloads = list(bm.PAYLOADS.keys())
    encoders = list(bm.ENCODERS.keys())

    chart_cover_hero("/home/claude/figs/00_cover.png")
    chart_bytes_grouped(body, payloads, encoders,
                        "/home/claude/figs/01_bytes.png",
                        subtitle="Body-only encoding — envelope overhead excluded.")
    chart_reduction_heatmap(body, payloads, encoders,
                            "/home/claude/figs/03_heatmap.png",
                            subtitle="Sky-blue = smaller than JSON. Rose = larger.")
    chart_total_summary(body, payloads, encoders,
                        "/home/claude/figs/04_total.png",
                        subtitle="Sum of body-only bytes across the 6-payload suite.")
    chart_tokens_grouped(body, payloads, encoders,
                         "/home/claude/figs/02_tokens.png",
                         subtitle="Estimated cl100k_base tokens.")
    chart_latency(wire, payloads, encoders,
                  "/home/claude/figs/05_latency.png",
                  subtitle="Median of 200 iterations. CPython 3.13.")
    chart_radar("/home/claude/figs/06_radar.png")
    chart_envelope_cost(wire, body, payloads,
                        "/home/claude/figs/07_envelope.png",
                        subtitle="Solid = body. Translucent = envelope.")
    chart_winner_showcase(body, "/home/claude/figs/08_winner.png")
    print("Charts done.")
