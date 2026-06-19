"""Generate ER diagram PNG for the competitor analysis system."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import matplotlib.patheffects as pe

FIG_W, FIG_H = 32, 22
ROW_H = 0.32
HEADER_H = 0.42
FONT_FIELD = 7.8
FONT_TITLE = 9.5
BG = "#F7F4FC"

PALETTE = {
    "users":               "#4A7FD4",
    "tasks":               "#7B2CBF",
    "task_runs":           "#2E9E6A",
    "agent_traces":        "#1A7A50",
    "source_citations":    "#D4691A",
    "competitor_profiles": "#C0392B",
    "cross_analyses":      "#922B21",
    "reports":             "#8E44AD",
    "report_claims":       "#6C3483",
    "manual_corrections":  "#B7770D",
    "survey_uploads":      "#148F77",
    "scoping_drafts":      "#1F6FAE",
}


def table_height(fields):
    return HEADER_H + ROW_H * len(fields)


def draw_table(ax, x, y, w, name, fields):
    """Draw one table; y is the TOP-LEFT corner y."""
    h = table_height(fields)
    color = PALETTE.get(name, "#555555")

    # outer shadow
    shadow = FancyBboxPatch(
        (x + 0.07, y - h - 0.07), w, h,
        boxstyle="round,pad=0.06",
        facecolor="#CCCCCC", edgecolor="none", linewidth=0, zorder=1,
    )
    ax.add_patch(shadow)

    # main body
    body = FancyBboxPatch(
        (x, y - h), w, h,
        boxstyle="round,pad=0.06",
        facecolor="#FFFFFF", edgecolor="#AAAAAA", linewidth=1.2, zorder=2,
    )
    ax.add_patch(body)

    # header bar
    hdr = FancyBboxPatch(
        (x, y - HEADER_H), w, HEADER_H,
        boxstyle="round,pad=0.04",
        facecolor=color, edgecolor="none", linewidth=0, zorder=3,
    )
    ax.add_patch(hdr)

    ax.text(
        x + w / 2, y - HEADER_H / 2, name,
        ha="center", va="center", fontsize=FONT_TITLE, fontweight="bold",
        color="white", zorder=4,
    )

    # separator line
    ax.plot([x + 0.1, x + w - 0.1], [y - HEADER_H, y - HEADER_H],
            color="#DDDDDD", lw=0.8, zorder=3)

    # field rows
    for i, field in enumerate(fields):
        fy = y - HEADER_H - ROW_H * i
        if i % 2 == 1:
            stripe = FancyBboxPatch(
                (x + 0.04, fy - ROW_H), w - 0.08, ROW_H,
                boxstyle="square,pad=0",
                facecolor="#F3EEFF", edgecolor="none", zorder=2,
            )
            ax.add_patch(stripe)

        # tag  (PK / FK / UK)
        parts = field.split("|")
        tag = parts[0].strip() if len(parts) > 1 else ""
        fname = parts[1].strip() if len(parts) > 1 else parts[0].strip()

        if tag:
            tag_color = {"PK": "#D4400B", "FK": "#1A6FAE", "UK": "#1A7A50"}.get(tag, "#666")
            ax.text(x + 0.13, fy - ROW_H / 2, tag,
                    ha="left", va="center", fontsize=6.5, fontweight="bold",
                    color=tag_color, zorder=5)
            ax.text(x + 0.52, fy - ROW_H / 2, fname,
                    ha="left", va="center", fontsize=FONT_FIELD,
                    color="#222222", zorder=5)
        else:
            ax.text(x + 0.18, fy - ROW_H / 2, fname,
                    ha="left", va="center", fontsize=FONT_FIELD,
                    color="#444444", zorder=5)

        if i < len(fields) - 1:
            ax.plot([x + 0.1, x + w - 0.1], [fy - ROW_H, fy - ROW_H],
                    color="#EEEEEE", lw=0.6, zorder=3)

    cx = x + w / 2
    return {
        "top":    (cx, y),
        "bottom": (cx, y - h),
        "left":   (x,  y - h / 2),
        "right":  (x + w, y - h / 2),
        "x": x, "y": y, "w": w, "h": h,
        "mid_right": (x + w, y - HEADER_H / 2),
    }


def arrow(ax, p1, p2, label="", dashed=False, color="#555555", rad=0.0):
    ls = (0, (5, 4)) if dashed else "solid"
    ax.annotate(
        "", xy=p2, xytext=p1,
        arrowprops=dict(
            arrowstyle="-|>",
            color=color, lw=1.3,
            linestyle=ls,
            connectionstyle=f"arc3,rad={rad}",
            mutation_scale=10,
        ),
        zorder=0,
    )
    if label:
        mx = (p1[0] + p2[0]) / 2
        my = (p1[1] + p2[1]) / 2
        ax.text(mx, my, label, fontsize=7, color=color,
                ha="center", va="center",
                bbox=dict(facecolor="#F7F4FC", edgecolor="none", pad=1),
                zorder=6)


# ─── layout ───────────────────────────────────────────────────────────────────
# columns: x = 0.5 | 7.2 | 14.2 | 21.2
# rows:    top y = 20.5 | mid y = 13.5 | bottom y = 6.0

fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
ax.set_xlim(0, FIG_W)
ax.set_ylim(0, FIG_H)
ax.axis("off")
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)

ax.text(FIG_W / 2, FIG_H - 0.35,
        "Database ER Diagram — Competitor Analysis System",
        ha="center", va="top", fontsize=16, fontweight="bold",
        color="#2C1654")

p = {}

# ── Column 1 ──
p["users"] = draw_table(ax, 0.5, 20.5, 5.5, "users", [
    "PK|id  uuid",
    "UK|email  text",
    "   created_at  timestamptz",
    "   last_login_at  timestamptz",
])

p["task_runs"] = draw_table(ax, 0.5, 13.5, 5.5, "task_runs", [
    "PK|id  uuid",
    "FK|task_id  uuid",
    "   status  text",
    "   retry_count  int",
    "   checkpoint_id  text",
    "   langgraph_thread_id  text",
    "   started_at  timestamptz",
])

p["agent_traces"] = draw_table(ax, 0.5, 6.0, 5.5, "agent_traces", [
    "PK|id  uuid",
    "FK|task_run_id  uuid",
    "   sequence_no  int  (UQ)",
    "   agent_name  text",
    "   tokens_in / tokens_out  int",
    "   cost_usd  numeric",
    "   langsmith_run_id  text",
])

# ── Column 2 ──
p["tasks"] = draw_table(ax, 7.2, 20.5, 5.8, "tasks", [
    "PK|id  uuid",
    "FK|user_id  uuid",
    "   target_brief  text",
    "   competitor_names  jsonb",
    "   dimensions  jsonb",
    "   status  text",
    "   created_at  timestamptz",
])

p["source_citations"] = draw_table(ax, 7.2, 13.5, 5.8, "source_citations", [
    "PK|id  text",
    "FK|task_id  uuid",
    "   type / category  text",
    "   url  text",
    "   title  text",
    "   provider  text",
    "   embedding  vector(1536)",
])

p["reports"] = draw_table(ax, 7.2, 6.0, 5.8, "reports", [
    "PK|id  uuid",
    "FK|task_id  uuid",
    "FK|source_report_id  uuid (self)",
    "   qa_status  text",
    "   version  int",
    "   language  text",
    "   embedding  vector(1536)",
])

# ── Column 3 ──
p["scoping_drafts"] = draw_table(ax, 14.2, 20.5, 5.8, "scoping_drafts", [
    "PK|id  uuid",
    "FK|task_id  uuid (nullable)",
    "   user_brief  text",
    "   intent_mode  text",
    "   scope_contract  jsonb",
    "   clarification_questions  jsonb",
    "   iteration  int",
])

p["competitor_profiles"] = draw_table(ax, 14.2, 13.5, 5.8, "competitor_profiles", [
    "PK|id  uuid",
    "FK|task_id  uuid",
    "   competitor_name  text",
    "   feature_tree  jsonb",
    "   pricing  jsonb",
    "   user_personas  jsonb",
    "   swot  jsonb",
])

p["report_claims"] = draw_table(ax, 14.2, 6.0, 5.8, "report_claims", [
    "PK|id  uuid",
    "FK|report_id  uuid",
    "   claim_path  text",
    "   source_ids  jsonb  (→ citations)",
    "   source_support  text",
    "   qa_status  text",
    "   embedding  vector(1536)",
])

# ── Column 4 ──
p["cross_analyses"] = draw_table(ax, 21.2, 13.5, 5.8, "cross_analyses", [
    "PK|id  uuid",
    "FK|task_id  uuid",
    "   feature_matrix  jsonb",
    "   pricing_comparison  jsonb",
    "   positioning_map  jsonb",
    "   differentiation_summary  text",
])

p["survey_uploads"] = draw_table(ax, 21.2, 8.5, 5.8, "survey_uploads", [
    "PK|id  uuid",
    "FK|task_id  uuid",
    "FK|uploaded_by  uuid",
    "   kind  text",
    "   filename  text",
    "   redacted_content  jsonb",
])

p["manual_corrections"] = draw_table(ax, 21.2, 3.5, 5.8, "manual_corrections", [
    "PK|id  uuid",
    "FK|report_id  uuid",
    "FK|claim_id  uuid (nullable)",
    "FK|user_id  uuid",
    "   correction_type  text",
    "   triggered_rerun  bool",
])

# ─── Relationships ─────────────────────────────────────────────────────────────

# users → tasks
arrow(ax, p["users"]["right"], p["tasks"]["left"], "1:N")

# users → manual_corrections  (curved, long)
arrow(ax, p["users"]["bottom"],
      (p["manual_corrections"]["x"], p["manual_corrections"]["y"] - 0.6),
      "1:N", rad=0.35, color="#777777")

# users → survey_uploads
arrow(ax, p["users"]["right"],
      (p["survey_uploads"]["x"], p["survey_uploads"]["y"] - 0.6),
      "1:N", rad=-0.25, color="#777777")

# tasks → task_runs
arrow(ax, p["tasks"]["left"], p["task_runs"]["right"], "1:N", rad=0.2)

# tasks → source_citations
arrow(ax, p["tasks"]["bottom"], p["source_citations"]["top"], "1:N")

# tasks → competitor_profiles
arrow(ax, p["tasks"]["right"], p["competitor_profiles"]["left"], "1:N")

# tasks → cross_analyses
arrow(ax, p["tasks"]["right"],
      (p["cross_analyses"]["x"], p["cross_analyses"]["y"] - 0.8),
      "1:N", rad=-0.2)

# tasks → reports
arrow(ax, p["source_citations"]["bottom"], p["reports"]["top"], "1:N")

# tasks → scoping_drafts
arrow(ax, p["tasks"]["right"], p["scoping_drafts"]["left"], "0/1:N")

# tasks → survey_uploads
arrow(ax, p["tasks"]["right"],
      (p["survey_uploads"]["x"], p["survey_uploads"]["y"] - 1.5),
      "1:N", rad=-0.35, color="#777777")

# task_runs → agent_traces
arrow(ax, p["task_runs"]["bottom"], p["agent_traces"]["top"], "1:N")

# reports → report_claims
arrow(ax, p["reports"]["right"], p["report_claims"]["left"], "1:N")

# reports self-reference (version)
rx, ry, rw = p["reports"]["x"], p["reports"]["y"], p["reports"]["w"]
ax.annotate("", xy=(rx + rw, ry - 0.9), xytext=(rx + rw, ry - 0.22),
            arrowprops=dict(arrowstyle="-|>", color="#8E44AD", lw=1.2,
                            connectionstyle="arc3,rad=-1.4", mutation_scale=9), zorder=0)
ax.text(rx + rw + 1.2, ry - 0.55, "self\n(version)", fontsize=6.5,
        color="#8E44AD", ha="center", style="italic")

# reports → manual_corrections
arrow(ax, p["reports"]["right"],
      (p["manual_corrections"]["x"], p["manual_corrections"]["y"] - 0.22),
      "1:N", rad=-0.15, color="#B7770D")

# report_claims → manual_corrections
arrow(ax, p["report_claims"]["right"],
      (p["manual_corrections"]["x"], p["manual_corrections"]["y"] - 1.3),
      "0/1:N", rad=0.1, color="#B7770D")

# report_claims → source_citations  (dashed, logical JSONB)
arrow(ax, p["report_claims"]["top"],
      p["source_citations"]["bottom"],
      "JSONB logical", dashed=True, color="#999999")

# ─── Legend ────────────────────────────────────────────────────────────────────
lx, ly = 0.5, 3.0
ax.add_patch(FancyBboxPatch((lx, ly - 2.3), 5.5, 2.5,
             boxstyle="round,pad=0.1",
             facecolor="white", edgecolor="#BBBBBB", lw=1, zorder=2))
ax.text(lx + 0.2, ly + 0.05, "Legend", fontsize=9, fontweight="bold", color="#333")
for txt, col, dy in [
    ("PK  Primary Key", "#D4400B", 0.45),
    ("FK  Foreign Key", "#1A6FAE", 0.80),
    ("UK  Unique Key",  "#1A7A50", 1.15),
    ("-->  1:N relationship", "#555555", 1.50),
    ("- - ->  JSONB logical ref (no FK)", "#999999", 1.85),
]:
    ax.text(lx + 0.25, ly - dy, txt, fontsize=7.5, color=col)

plt.tight_layout(pad=0.3)
out = "docs/er-diagram.png"
plt.savefig(out, dpi=160, bbox_inches="tight",
            facecolor=BG, edgecolor="none")
print(f"Saved: {out}")
