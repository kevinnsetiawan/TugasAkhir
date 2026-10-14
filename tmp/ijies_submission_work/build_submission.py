from __future__ import annotations

import csv
import json
import re
from copy import deepcopy
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph


ROOT = Path.cwd()
WORK = ROOT / "tmp" / "ijies_submission_work"
SOURCE = ROOT / "IJIES_Manuscript_Draft_Adaptive_Web_Penetration_Testing.docx"
OUTPUT = ROOT / "IJIES_Manuscript_Submission_Draft.docx"
RESULTS = ROOT / "rl_pentest" / "results"

plt.rcParams.update({
    "font.family": "Times New Roman",
    "font.size": 8,
    "axes.titlesize": 8,
    "axes.labelsize": 8,
    "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5,
    "legend.fontsize": 7.5,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "axes.edgecolor": "#333333",
    "text.color": "#1b1b1b",
    "axes.labelcolor": "#1b1b1b",
    "xtick.color": "#1b1b1b",
    "ytick.color": "#1b1b1b",
})

QL_COLOR = "#28634f"
DQN_COLOR = "#3d82a2"
INK = "#263746"
PALE_BLUE = "#eaf2f8"
PALE_GREEN = "#e7f2ed"
PALE_GOLD = "#faf1dc"
PALE_ROSE = "#f7eaea"


def add_box(ax, xy, width, height, title, body="", face=PALE_BLUE,
            title_size=8.1, body_size=6.9):
    x, y = xy
    box = FancyBboxPatch(
        (x, y), width, height,
        boxstyle="round,pad=0.012,rounding_size=0.025",
        linewidth=0.9, edgecolor=INK, facecolor=face,
    )
    ax.add_patch(box)
    if body:
        ax.text(x + width / 2, y + height * 0.66, title,
                ha="center", va="center", fontsize=title_size,
                fontweight="bold", color=INK)
        ax.text(x + width / 2, y + height * 0.32, body,
                ha="center", va="center", fontsize=body_size,
                color="#202020", linespacing=1.12)
    else:
        ax.text(x + width / 2, y + height / 2, title,
                ha="center", va="center", fontsize=title_size,
                fontweight="bold", color=INK)


def arrow(ax, start, end, color=INK, rad=0.0, lw=0.9):
    ax.add_patch(FancyArrowPatch(
        start, end, arrowstyle="-|>", mutation_scale=8,
        linewidth=lw, color=color,
        connectionstyle=f"arc3,rad={rad}",
    ))


def make_system_figure(path: Path) -> None:
    fig, ax = plt.subplots(figsize=(3.06, 4.18), dpi=500)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    boxes = [
        (0.18, 0.84, 0.64, 0.115, "RL agent", "Q-learning table or DQN network", PALE_BLUE),
        (0.18, 0.68, 0.64, 0.115, "Action selection", "One of 120 endpoint-payload pairs", PALE_GOLD),
        (0.055, 0.49, 0.39, 0.125, "HTTP client", "GET, POST, or PUT", PALE_BLUE),
        (0.555, 0.49, 0.39, 0.125, "Juice Shop", "Eight configured endpoints", PALE_GREEN),
        (0.18, 0.315, 0.64, 0.12, "Response analyzer", "Endpoint baseline and 8-feature state", PALE_BLUE),
        (0.12, 0.135, 0.76, 0.125, "Evidence and verification gate",
         "HTTP evidence; DOM execution for XSS; benign controls", PALE_ROSE),
        (0.18, 0.012, 0.64, 0.09, "Reward and update",
         "Next state; mask verified actions only", PALE_GREEN),
    ]
    for x, y, w, h, title, body, face in boxes:
        add_box(ax, (x, y), w, h, title, body, face)

    arrow(ax, (0.50, 0.84), (0.50, 0.795))
    arrow(ax, (0.50, 0.68), (0.50, 0.626))
    arrow(ax, (0.445, 0.552), (0.555, 0.552), color=QL_COLOR)
    arrow(ax, (0.555, 0.515), (0.445, 0.515), color=DQN_COLOR)
    ax.text(0.50, 0.59, "request", ha="center", va="center", fontsize=6.7, color=QL_COLOR)
    ax.text(0.50, 0.477, "response", ha="center", va="center", fontsize=6.7, color=DQN_COLOR)
    arrow(ax, (0.50, 0.49), (0.50, 0.435))
    arrow(ax, (0.50, 0.315), (0.50, 0.26))
    arrow(ax, (0.50, 0.135), (0.50, 0.105))
    # Closed learning loop: route the updated state and reward back to the agent.
    ax.plot([0.18, 0.035, 0.035], [0.056, 0.056, 0.897], color=INK, linewidth=1.0)
    arrow(ax, (0.035, 0.897), (0.18, 0.897), color=INK, lw=1.0)
    ax.text(0.088, 0.49, "state + reward", rotation=90, ha="center", va="center",
            fontsize=6.8, color=INK)

    fig.subplots_adjust(left=0.03, right=0.97, top=0.985, bottom=0.02)
    fig.savefig(path, dpi=500, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)


def make_zap_figure(path: Path) -> None:
    fig, ax = plt.subplots(figsize=(3.06, 1.55), dpi=500)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    add_box(ax, (0.015, 0.56), 0.285, 0.31, "Python controller",
            "scope and API polling", PALE_BLUE, title_size=7.5, body_size=6.3)
    add_box(ax, (0.355, 0.56), 0.29, 0.31, "ZAP daemon",
            "spider + active scan", PALE_GOLD, title_size=7.5, body_size=6.3)
    add_box(ax, (0.70, 0.56), 0.285, 0.31, "Juice Shop",
            "search + /ftp/", PALE_GREEN, title_size=7.5, body_size=6.3)
    add_box(ax, (0.20, 0.08), 0.60, 0.27, "Relevant-alert filter",
            "risk + class + endpoint counts", PALE_ROSE, title_size=7.5, body_size=6.3)

    arrow(ax, (0.30, 0.72), (0.355, 0.72), color=QL_COLOR)
    arrow(ax, (0.645, 0.75), (0.70, 0.75), color=QL_COLOR)
    arrow(ax, (0.70, 0.65), (0.645, 0.65), color=DQN_COLOR)
    arrow(ax, (0.50, 0.56), (0.50, 0.35), color=DQN_COLOR)
    ax.text(0.55, 0.45, "alerts", ha="left", va="center", fontsize=6.2, color=DQN_COLOR)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.98, bottom=0.02)
    fig.savefig(path, dpi=500, bbox_inches="tight", pad_inches=0.025)
    plt.close(fig)


def read_agent_log(agent: str):
    rows = list(csv.DictReader((RESULTS / f"log_{agent}.csv").open(encoding="utf-8-sig", newline="")))
    discoveries = []
    seen = set()
    cumulative = []
    for episode, row in enumerate(rows, 1):
        if row["verified"].lower() == "true":
            action = int(row["action_index"])
            if action not in seen:
                seen.add(action)
                discoveries.append(episode)
        cumulative.append(len(seen))
    return rows, discoveries, cumulative


def make_result_figures() -> None:
    ql_summary = json.loads((RESULTS / "summary_ql.json").read_text(encoding="utf-8"))
    dqn_summary = json.loads((RESULTS / "summary_dqn.json").read_text(encoding="utf-8"))
    ql_counts = [ql_summary["sql_injection"], ql_summary["reflected_xss"], ql_summary["fuzzing_anomaly"]]
    dqn_counts = [dqn_summary["sql_injection"], dqn_summary["reflected_xss"], dqn_summary["fuzzing_anomaly"]]

    # Counts are taken from the latest run summaries.
    fig, ax = plt.subplots(figsize=(3.06, 1.63), dpi=500)
    x = [0, 1, 2]
    width = 0.34
    bars1 = ax.bar([v - width / 2 for v in x], ql_counts, width,
                   label="Q-learning", color=QL_COLOR)
    bars2 = ax.bar([v + width / 2 for v in x], dqn_counts, width,
                   label="DQN", color=DQN_COLOR)
    ax.set_xticks(x, ["SQL injection", "XSS", "Fuzzing / file"])
    ax.set_ylabel("Verified action-level findings")
    ax.set_ylim(0, 7.4)
    ax.set_yticks(range(0, 8, 2))
    ax.grid(axis="y", color="#dddddd", linewidth=0.5)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(frameon=False, loc="upper right", ncol=2, handlelength=1.2,
              columnspacing=0.7, borderaxespad=0.2)
    for bars in (bars1, bars2):
        for bar in bars:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.12,
                    f"{int(bar.get_height())}", ha="center", va="bottom", fontsize=7.4)
    fig.tight_layout(pad=0.45)
    fig.savefig(WORK / "figure_3_categories.png", dpi=500, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)

    _, ql_discoveries, ql_cumulative = read_agent_log("ql")
    _, dqn_discoveries, dqn_cumulative = read_agent_log("dqn")
    episodes = range(1, len(ql_cumulative) + 1)
    fig, ax = plt.subplots(figsize=(3.06, 2.0), dpi=500)
    ax.step(episodes, ql_cumulative, where="post", color=QL_COLOR,
            linewidth=1.5, label="Q-learning (14)")
    ax.step(episodes, dqn_cumulative, where="post", color=DQN_COLOR,
            linewidth=1.5, label="DQN (13)")
    ax.axvline(787, color=QL_COLOR, linewidth=0.75, linestyle="--", alpha=0.8)
    ax.axvline(443, color=DQN_COLOR, linewidth=0.75, linestyle="--", alpha=0.8)
    ax.set_xlim(0, 1585)
    ax.set_ylim(0, 15)
    ax.set_xticks([0, 400, 800, 1200, 1585], ["0", "400", "800", "1,200", "1,585"])
    ax.set_yticks([0, 5, 10, 15])
    ax.set_xlabel("Episode")
    ax.set_ylabel("Cumulative unique verified actions")
    ax.grid(color="#dddddd", linewidth=0.5)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(frameon=False, loc="lower right", borderaxespad=0.25)
    ax.annotate("DQN: 13 by 443", xy=(443, 13), xytext=(540, 11.0),
                fontsize=6.9, color=DQN_COLOR,
                arrowprops={"arrowstyle": "-", "color": DQN_COLOR, "lw": 0.65})
    ax.annotate("QL: 14 by 787", xy=(787, 14), xytext=(920, 13.0),
                fontsize=6.9, color=QL_COLOR,
                arrowprops={"arrowstyle": "-", "color": QL_COLOR, "lw": 0.65})
    fig.tight_layout(pad=0.45)
    fig.savefig(WORK / "figure_4_discovery_curve.png", dpi=500, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)


def set_paragraph_text(paragraph, text: str) -> None:
    rpr = None
    if paragraph.runs:
        first = paragraph.runs[0]._r
        old_rpr = first.find(qn("w:rPr"))
        if old_rpr is not None:
            rpr = deepcopy(old_rpr)
    for child in list(paragraph._p):
        if child.tag != qn("w:pPr"):
            paragraph._p.remove(child)
    run = paragraph.add_run(text)
    if rpr is not None:
        run._r.insert(0, rpr)


def insert_paragraph_after(anchor, style=None):
    new_p = OxmlElement("w:p")
    anchor._p.addnext(new_p)
    paragraph = Paragraph(new_p, anchor._parent)
    if style:
        paragraph.style = style
    return paragraph


def set_font(run, size, bold=None):
    run.font.name = "Times New Roman"
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), "Times New Roman")
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), "Times New Roman")
    run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold


def format_body(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    paragraph.paragraph_format.first_line_indent = Inches(0.16)
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.line_spacing = 1.0
    for run in paragraph.runs:
        set_font(run, 11)


def keep_table_together(table):
    paragraphs = []
    for row in table.rows:
        tr_pr = row._tr.get_or_add_trPr()
        if tr_pr.find(qn("w:cantSplit")) is None:
            tr_pr.append(OxmlElement("w:cantSplit"))
        for cell in row.cells:
            paragraphs.extend(cell.paragraphs)
    for index, paragraph in enumerate(paragraphs):
        paragraph.paragraph_format.keep_together = True
        paragraph.paragraph_format.keep_with_next = index < len(paragraphs) - 1


def format_caption(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.first_line_indent = Inches(0)
    paragraph.paragraph_format.space_before = Pt(2)
    paragraph.paragraph_format.space_after = Pt(4)
    paragraph.paragraph_format.keep_with_next = paragraph.text.strip().startswith("Table ")
    for run in paragraph.runs:
        set_font(run, 10)


def add_figure_after(doc, anchor, image_path: Path, caption_text: str, width: float,
                     title: str, description: str):
    image_p = insert_paragraph_after(anchor, style="Normal")
    image_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    image_p.paragraph_format.first_line_indent = Inches(0)
    image_p.paragraph_format.space_before = Pt(2)
    image_p.paragraph_format.space_after = Pt(0)
    image_p.paragraph_format.keep_together = True
    shape = image_p.add_run().add_picture(str(image_path), width=Inches(width))
    docpr = shape._inline.docPr
    docpr.set("title", title)
    docpr.set("descr", description)
    cap_p = insert_paragraph_after(image_p, style="Normal")
    cap_p.add_run(caption_text)
    format_caption(cap_p)
    return cap_p


def find_para(doc, starts: str):
    for paragraph in doc.paragraphs:
        if paragraph.text.strip().startswith(starts):
            return paragraph
    raise ValueError(f"Paragraph not found: {starts}")


def para_index(doc, target):
    for index, paragraph in enumerate(doc.paragraphs):
        if paragraph._p is target._p:
            return index
    raise ValueError("Paragraph is not in this document")


def replace_citation_numbers(doc):
    ref_heading = find_para(doc, "REFERENCES")
    in_refs = False
    for paragraph in doc.paragraphs:
        if paragraph._p is ref_heading._p:
            in_refs = True
        if not in_refs:
            text = paragraph.text
            text = re.sub(r"\[(10|[5-9])\]", lambda m: f"[{int(m.group(1)) + 2}]", text)
            if text != paragraph.text:
                set_paragraph_text(paragraph, text)


def add_related_work(doc):
    anchor = find_para(doc, "Research applying reinforcement learning to penetration testing")
    text = (
        "The Agent Web Model formalizes web hacking as reinforcement-learning tasks at several "
        "abstraction levels and discusses the role of prior knowledge in defining those tasks [5]. "
        "Related work on cyber-terrain-aware attack graphs models operational constraints in the "
        "state and reward design [6]. Together, these studies highlight that an agent's observed "
        "performance depends on how the target, available actions, and constraints are represented. "
        "The present evaluation makes those boundaries explicit and adds candidate verification "
        "before a result is counted as a finding."
    )
    paragraph = insert_paragraph_after(anchor, style="Normal")
    paragraph.add_run(text)
    format_body(paragraph)


def compact_narrative(doc):
    replacements = [
        ("Research applying reinforcement learning to penetration testing",
         "Prior penetration-testing and capture-the-flag studies highlight trade-offs between model-free exploration and prior knowledge [4]. A predefined endpoint and payload library improves repeatability but narrows the search. Here, the policy selects among human-curated endpoints, surfaces, and payloads; it does not crawl, discover routes, or generate new payloads."),
        ("The Agent Web Model formalizes web hacking",
         "The Agent Web Model and cyber-terrain-aware attack graphs emphasize that representation and operational constraints shape RL behavior [5], [6]. We disclose these boundaries and verify candidates before counting findings."),
        ("This study evaluates QL and DQN on OWASP Juice Shop",
         "This study compares QL and DQN on OWASP Juice Shop, a deliberately vulnerable security-training application [7], and reports a scoped search/FTP comparison with ZAP. Candidates require control-differential verification; XSS also requires browser execution. Results apply to this target and action set."),
        ("The evaluation addresses three descriptive questions",
         "We compare verified findings, categories, endpoint activity, reward, and discovery timing under a fixed episode budget, then describe what the non-equivalent ZAP workflows allow us to infer. No statistical significance or generalization is claimed."),
        ("The action space is the Cartesian product",
         "Action a maps to endpoint floor(a/15) and payload a modulo 15. The fixed library is selected by the policy; routes and payloads are not generated at runtime."),
        ("The state summarizes the latest response",
         "The state tuple records status, response-length category, error, reflection and vulnerability indicators, endpoint index, response-time category, and content type. It is an engineered summary, not a full application model. DQN one-hot encodes status (5), length (4), endpoint (8), response time (3), and content type (5), plus three scalar flags, for 28 inputs; QL uses the tuple as its key."),
        ("The HTTP client returns a decoded response object",
         "The analyzer lowercases decoded response text and measures its character count, not network bytes. Missing responses become error states with zero status and length and no vulnerability label."),
        ("Feature extraction then derives several signals",
         "The analyzer extracts status, latency and content-type classes, database-error patterns, payload-family matches, reflection, and baseline change. Partial reflection requires at least half of meaningful payload tokens (each at least four characters) in the response."),
        ("For response length L and the endpoint-specific baseline",
         "Before training, each endpoint receives one benign “hello” probe. A length change is significant when |L − B_e|/B_e ≥ 0.15. Categories are below 1,500, 1,500–<2,500, 2,500–<3,500, and 3,500 or more characters."),
        ("The remaining categorical fields are derived consistently",
         "Status has five classes (2xx, 3xx, 4xx, 5xx, error), response time three (<0.5 s, 0.5–<2.0 s, ≥2.0 s), and content type five (JSON, HTML, text, XML, other). The system engineers these features rather than vectorizing response text."),
        ("DQN approximates action values with a neural network",
         "DQN learns from replay transitions with a target network. Its gradual 0.9965 epsilon decay preserves exploration under random initial weights; hyperparameters follow each algorithm rather than being numerically identical."),
        ("The reward function separates a request failure",
         "Verified candidates earn +50, anomalies or inconclusive candidates +10, and normal responses −1; connection errors earn −5 without a length bonus. Completed responses also receive the category bonus in Table 4."),
        ("The implemented rule can be written as",
         "With bonus vector [0, 0, 5, 10], examples are +60 for a verified category-3 finding, +15 for an inconclusive category-2 response, +9 for a normal category-3 response, and −5 for a request error. A large response can raise reward without proving a vulnerability."),
        ("The reward is a learning signal, not a vulnerability metric",
         "Cumulative reward sums findings, anomalies, normal responses, errors, and length bonuses; it is not a coverage metric. We report it alongside verified counts, hit rate, discovery episode, and request cost."),
        ("The training protocol follows a repeatable sequence",
         "Figure 1 summarizes the loop: collect a benign baseline per endpoint, select and send an action, analyze its response, verify candidates, assign reward, and update the agent. This keeps detection, verification, and learning in sequence."),
        ("Action masking applies only to actions already confirmed",
         "Only verified vulnerable actions are masked. Failed, normal, previously attempted, and rejected actions remain selectable; both agents complete all 1,585 episodes, including after their final discovery."),
        ("HTTP candidates were checked against a benign control",
         "Each HTTP candidate was compared with a benign control and, when meaningful, a neutralized-payload control; neither could reproduce the same vulnerability class. Connection errors failed verification. XSS required an instrumented canary to execute in headless Chromium on the SPA route, using warmup and bounded polling. The separate 120-action benchmark left 46 unknown labels outside binary metrics and partly shared verification evidence."),
        ("The analyzer also applied endpoint-surface constraints",
         "Detection was surface-gated: SQLi required database-error or significant baseline-change evidence; file disclosure required recognizable content on the file surface or configured extension-bypass evidence; fuzzing required an echoed probe in a server error. Generic errors and reflection alone were excluded."),
        ("The control-differential step addresses false positives",
         "Neutralized controls test whether benign or less exploit-like input reproduces evidence; payloads that cannot be meaningfully neutralized use only the benign control. Inconclusive cases earn anomaly reward. Browser execution distinguishes reflected data from executing XSS."),
        ("The controlled ZAP comparison was restricted",
         "QL and ZAP were compared on their two shared endpoints, product search and FTP [8]. We report findings, hit rate, requests per finding, first and final discovery episode, and unique endpoint-class locations. Results are in-sample; shared scope does not equalize scan strategy, verification, or request accounting."),
        ("OWASP ZAP is organized around a local intercepting proxy",
         "ZAP provides a local proxy, Core API, spider, active scanner, passive scanner, and alert store. The controller reads HTTP history and alerts through the API; alerts include risk, URL, parameter, evidence, and attack [9]–[12]."),
        ("In this experiment, ZAP ran as a daemon",
         "ZAP 2.17 ran at localhost:8080 against Juice Shop at localhost:3000. For search and /ftp/, the Python controller established a message baseline, accessed each URL, ran the spider (maxChildren=2) to completion, then ran a nonrecursive active scan. No authenticated user or spider-wide target was configured. The report counted 590 messages (22 URL/spider and 568 active-scan) and 33 raw alerts; one High/Medium SQLi alert met the study filter."),
        ("After each phase, the controller queried the ZAP message history",
         "The controller estimated phase request counts from message-history deltas, then filtered alerts by class (SQLi, XSS, path traversal) and High/Medium risk. This is the study's comparison rule; excluded alerts may remain valid findings under other criteria."),
        ("Figure 1 summarizes this flow.",
         "Figure 2 separates the controller and alert filter from ZAP's spider and active scanner. Although passive scanning can analyze recorded traffic, this script did not run a separate passive-scan job; active scan generated attack probes."),
        ("The first finding appeared at episode 1 for both agents",
         "Both agents found their first action in episode 1. DQN reached its final count by episode 443, before QL at 787; these are milestones in one run, not evidence of convergence. Figure 3 shows cumulative unique verified actions; repeated seeds are needed to assess stability."),
        ("The difference between reward and verified-finding totals follows",
         "The higher DQN reward despite fewer findings follows from the reward design: it includes normal responses, errors, anomalies, and response-length bonuses throughout the run. Reward is an optimization signal, not a substitute for coverage."),
        ("For the two shared endpoints, the thesis reports",
         "On search and FTP, QL made 1,214 payload requests for 10 findings (121.40 per finding); ZAP made 590 requests for one relevant finding (590 per finding). Of ZAP's 33 raw alerts, one High/Medium SQLi alert met the filter; none for XSS or path traversal did. The 4.86 rate ratio is descriptive because workflows, verification, and request accounting differ."),
        ("The request-per-finding ratio of approximately 4.86",
         "The ratio does not normalize scan duration, payload complexity, severity, or review effort. A stronger study would align the endpoint allowlist, authentication, request and time budgets, payload families, counting rules, and independent manual review."),
    ]
    for prefix, text in replacements:
        set_paragraph_text(find_para(doc, prefix), text)

    for prefix in (
        "Earlier research frames penetration testing as a sequence",
        "The evaluation used one target and one seed per algorithm",
        "The ratio 590.00/121.40 is approximately",
    ):
        paragraph = find_para(doc, prefix)
        paragraph._p.getparent().remove(paragraph._p)

    additions = [
        ("The analyzer lowercases decoded response text",
         "Because this is a decoded character count, it is a deterministic content-length proxy for this implementation rather than a measure of bytes transferred. Server-side content or serialization can still affect it; endpoint-specific baselines reduce, but cannot remove, that variation."),
        ("Before training, each endpoint receives one benign",
         "The configured fallback baseline is 2,200 characters when a usable endpoint baseline is unavailable. A relative-change score is applied only when the baseline is positive, avoiding division by zero; this check is one detector feature, not a finding by itself."),
        ("Status has five classes",
         "These coarse bins make the state compact and reproducible across episodes. They discard page wording and structure, so two different server outcomes may map to the same state; the agent therefore learns over response summaries rather than a semantic model of the application."),
        ("Only verified vulnerable actions are masked",
         "The 1,585-episode budget is fixed for each agent. Summary request totals also include the eight initial endpoint-baseline probes and control transactions used after candidates, so they exceed the number of policy-selected payload requests; QL and DQN made 1,640 and 1,637 total HTTP transactions, respectively."),
        ("Each HTTP candidate was compared with a benign control",
         "The neutralized control is omitted when neutralization would leave a wildcard payload unchanged, and verification records the actual one or two controls sent. For XSS, the verifier instruments the same tag and event shape with a canary handler, then checks execution on the mapped single-page-application route; a string reflected in JSON is insufficient."),
        ("Detection was surface-gated",
         "For SQLi, qualifying evidence is a database error with an error response or a successful response with a significant change from that endpoint's baseline. File findings require confirmed content or the configured encoded-null extension bypass on the file surface; fuzzing requires a 5xx response to echo the probe. A generic 500 page, FTP listing, or reflection alone is excluded."),
        ("Detection was surface-gated",
         "The independent detector benchmark covers 120 endpoint-payload pairs against curated labels: 13 true positives, no false positives among 60 known-safe negatives, one false negative, and 46 unknown actions excluded from binary metrics. These figures show agreement on the labeled set, not independent proof of perfect detection, because verification evidence is partly shared."),
        ("ZAP 2.17 ran at localhost:8080",
         "The controller waited for spider and active-scan jobs to complete before taking message-history deltas. The 568 active-scan messages were generated after the 22 URL/spider messages, and the scan was nonrecursive. Thus the count describes this scripted scope and run; it is not a universal request cost for ZAP."),
        ("Both agents found their first action in episode 1",
         "Across the full action set, QL verified 14 actions and DQN 13, corresponding to five distinct endpoint-class locations. Multiple payloads can represent the same location, so action totals and location coverage answer different questions."),
        ("Action a maps to endpoint floor(a/15)",
         "The 120 choices are the product of eight configured endpoints and 15 predefined payloads. The policy cannot add routes or input families during a run; consequently, a high discovery count means success within this curated library, not broad or exhaustive application coverage."),
        ("DQN learns from replay transitions with a target network",
         "QL's 0.90 epsilon decay reaches its 0.1 floor around episode 22. That schedule would leave a randomly initialized DQN exploiting early, potentially arbitrary Q-value rankings for most of its budget, so DQN uses 0.9965 decay and approaches the floor around episode 657 under the per-episode update rule. The schedules support exploration for each algorithm but make this an implementation comparison rather than a controlled hyperparameter ranking."),
        ("Figure 1 summarizes the loop:",
         "Both scripts use seed 42 and run the complete budget, with no early stopping after all known findings are reached. The fixed seed makes this particular trajectory repeatable when the environment and dependencies are stable; it does not replace repeated runs or establish expected performance."),
        ("The cumulative reward should not be interpreted as a direct vulnerability-coverage metric",
         "All reported training metrics are in-sample: they summarize the same 1,585 episodes used to update the policy, and this project has no held-out test phase. Consecutive choices also depend on the evolving Q-values and discovered-action mask, so episode observations are not independent samples. The curves are descriptive evidence for these runs, not estimates of population-level performance or statistical significance."),
        ("The finite action set contains 120 choices",
         "Tabular QL stores values for observed discrete states and actions, making its behavior directly inspectable through the learned table. DQN instead shares parameters across its 28 input features, which can be useful when related states recur. However, this state space is already small and the experiment does not isolate representation learning from the effects of the exploration schedule, so the earlier DQN milestone should not be read as evidence of general algorithmic superiority."),
        ("Construct validity is limited by the operational definition",
         "The reported action-level count is the number of verified endpoint-payload pairs, while unique vulnerable locations collapse those pairs by endpoint and vulnerability class. These are intentionally different units: neither is a severity-weighted risk score, and neither indicates how many distinct production defects an organization would face."),
        ("Construct validity is limited by the operational definition",
         "The seed is fixed at 42, but the two agents have different update rules and exploration schedules. Environment response changes, browser timing, and request ordering may also alter a run. A single trajectory cannot separate those sources of variation or support a causal claim that one algorithm caused the observed difference."),
        ("External validity is limited to one version of one intentionally vulnerable application",
         "The endpoint list, surface labels, and payload library encode a human prior informed by Juice Shop's known structure. They are part of the study design, not evidence that the agent autonomously discovers an unknown attack surface. Transfer to another target would require defining its action space and verification rules independently, then evaluating on data not used to construct those rules."),
        ("Comparison validity is limited because ZAP and the RL agents use different scan workflows",
         "The shared search and FTP scope controls which two endpoints are considered, but not the number or type of opportunities each tool receives. ZAP's spider and active scanner issue their own requests; the agent selects from the fixed payload matrix and spends additional transactions verifying candidates. The resulting ratio is therefore a descriptive workload ratio under this implementation, not a normalized cost-effectiveness estimate."),
        ("Future work should run each method across multiple seeds",
         "Repeated runs should preserve per-seed logs and report uncertainty around both action-level and location-level coverage, as well as time and request budgets. A held-out target should be selected before tuning payloads or detectors. Ablation results should include false-positive review effort alongside discovery, since relaxing verification can raise apparent recall while increasing analyst workload."),
        ("For a stronger ZAP comparison, both systems should use a published endpoint allowlist",
         "A shared protocol should specify whether baseline and verification transactions count toward each budget, how repeated payload findings are consolidated, and how asynchronous scan messages map to requests. Reporting both raw HTTP transactions and policy-selected actions would make the accounting auditable and reduce ambiguity when comparing automated scanners."),
        ("Under 1,585 episodes on OWASP Juice Shop",
         "The evidence supports feasibility within this bounded action library and run configuration. It does not establish autonomous discovery, generalization to production systems, or stable superiority over ZAP or another RL method."),
    ]
    for prefix, addition in additions:
        paragraph = find_para(doc, prefix)
        set_paragraph_text(paragraph, paragraph.text + " " + addition)


def format_heading(paragraph, size, bold=True):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    paragraph.paragraph_format.first_line_indent = Inches(0)
    paragraph.paragraph_format.space_before = Pt(4 if size >= 12 else 2)
    paragraph.paragraph_format.space_after = Pt(2)
    paragraph.paragraph_format.keep_with_next = True
    for run in paragraph.runs:
        set_font(run, size, bold=bold)


def main():
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)
    WORK.mkdir(parents=True, exist_ok=True)
    system_png = WORK / "figure_1_system_workflow.png"
    zap_png = WORK / "figure_2_zap_flow.png"
    make_system_figure(system_png)
    make_zap_figure(zap_png)
    make_result_figures()

    doc = Document(str(SOURCE))
    paragraphs = doc.paragraphs

    # The title block, names, affiliation, and email were already present in the
    # author's template-derived draft and are retained as supplied.
    abstract = (
        "Abstract: This study compares tabular Q-learning (QL) and a deep Q-network (DQN) "
        "for adaptive web penetration testing on OWASP Juice Shop. Both agents operated for "
        "1,585 episodes over 120 predefined endpoint-payload actions. Candidate findings passed "
        "control-differential verification, while cross-site scripting candidates also required "
        "browser execution. QL produced 14 verified action-level findings and DQN produced 13, "
        "across five unique endpoint-class locations each. Both agents found their first verified "
        "action in episode 1; QL reached its final observed count by episode 787 and DQN by "
        "episode 443. A separate detector benchmark yielded 13 true positives, no false positives, "
        "and one false negative among labeled actions; 46 actions remained unknown. A scoped "
        "two-endpoint comparison recorded 10 QL findings and one relevant ZAP alert, but the "
        "request procedures were not equivalent. The results demonstrate feasibility on this "
        "target and action set, not generalization to other applications."
    )
    set_paragraph_text(find_para(doc, "Abstract:"), abstract)
    set_paragraph_text(find_para(doc, "Keywords:"),
                       "Keywords: Web penetration testing, Reinforcement learning, Q-learning, "
                       "Deep Q-network, OWASP Juice Shop, OWASP ZAP")

    # Renumber the existing ZAP and result graphics after adding the system figure.
    replace_citation_numbers(doc)
    add_related_work(doc)
    compact_narrative(doc)

    text_updates = {
        "1. INTRODUCTION": "1. Introduction",
        "2. MATERIALS AND METHODS": "2. Materials and Methods",
        "3. RESULTS AND DISCUSSION": "3. Results and Discussion",
        "4. CONCLUSION": "4. Conclusion",
        "3.6 Interpretation of the QL–DQN Difference": "3.5 Interpretation of the QL–DQN Difference",
        "3.7 Threats to Validity": "3.6 Threats to Validity",
        "3.8 Follow-up Experiments": "3.7 Follow-up Experiments",
        "CONFLICT OF INTEREST": "Conflict of Interest",
        "REFERENCES": "References",
        "Fig. 1. Architecture and request flow of the controlled ZAP comparison.":
            "Fig. 2. Architecture and request flow of the controlled ZAP scan.",
        "Fig. 2. Verified finding categories reported for each agent.":
            "Fig. 4. Verified action-level findings by category.",
        "TABLE 1. ENDPOINTS AND INPUT SURFACES":
            "Table 1. Configured endpoints and input surfaces.",
        "TABLE 2. OBSERVED STATE COMPONENTS":
            "Table 2. State variables and encodings.",
        "TABLE 3. AGENT CONFIGURATION":
            "Table 3. Agent hyperparameters.",
        "TABLE 4. REWARD COMPONENTS":
            "Table 4. Reward components.",
        "TABLE 5. TRAINING OUTCOMES REPORTED IN THE THESIS":
            "Table 5. Training outcomes.",
        "TABLE 6. QL REQUESTS AND VERIFIED FINDINGS BY ENDPOINT":
            "Table 6. QL requests and verified findings by endpoint.",
        "TABLE 7. DETECTOR PERFORMANCE ON LABELED ACTIONS":
            "Table 7. Detector performance on labeled actions.",
        "TABLE 8. COMPARISON ON TWO SHARED ENDPOINTS":
            "Table 8. Scoped comparison on two shared endpoints.",
    }
    for paragraph in list(doc.paragraphs):
        text = paragraph.text.strip()
        if text in text_updates:
            set_paragraph_text(paragraph, text_updates[text])

    # Keep the endpoint table in normal flow; its inherited hard page break
    # stranded a short paragraph on a nearly empty page.
    find_para(doc, "Table 6.").paragraph_format.page_break_before = False

    # Correct a stale endpoint count in prose; the latest QL CSV reports 41 FTP requests.
    for paragraph in doc.paragraphs:
        if "FTP surface produced three findings from 39 requests" in paragraph.text:
            set_paragraph_text(paragraph, paragraph.text.replace(
                "FTP surface produced three findings from 39 requests",
                "FTP surface produced three findings from 41 requests"))

    # Clarify the system workflow and figure links in the methods and results.
    training_para = find_para(doc, "Figure 1 summarizes the loop:")
    set_paragraph_text(training_para, training_para.text.replace(
        "The training protocol follows a repeatable sequence.",
        "The system workflow is summarized in Fig. 1. The training protocol follows a repeatable sequence."))
    for paragraph in doc.paragraphs:
        text = paragraph.text
        if "Figure 1 summarizes this flow." in text:
            set_paragraph_text(paragraph, text.replace("Figure 1 summarizes this flow.",
                                                       "Figure 2 summarizes this flow."))
        elif "The figure visualizes category counts" in text:
            set_paragraph_text(paragraph, text.replace("The figure visualizes category counts",
                                                       "Fig. 4 visualizes category counts"))
        elif "A single seeded trajectory cannot show whether either pattern is stable across runs." in text:
            set_paragraph_text(paragraph, text.replace(
                "A single seeded trajectory cannot show whether either pattern is stable across runs.",
                "Figure 3 shows the cumulative unique verified-action curve for each run. A single "
                "seeded trajectory cannot show whether either pattern is stable across runs."))

    # Make the action-level unit of analysis explicit throughout the headline result.
    for paragraph in doc.paragraphs:
        if paragraph.text.startswith("QL produced 14 verified findings and DQN produced 13"):
            set_paragraph_text(paragraph, paragraph.text.replace(
                "verified findings", "verified action-level findings", 1))
        if paragraph.text.startswith("Under 1,585 episodes on OWASP Juice Shop"):
            set_paragraph_text(paragraph, paragraph.text.replace(
                "14 verified findings and DQN obtained 13", 
                "14 verified action-level findings and DQN obtained 13"))

    category_summary = find_para(doc, "The category counts show six SQLi")
    set_paragraph_text(category_summary,
                       "The category counts show six SQLi and five XSS action-level findings for each agent, "
                       "while QL reported one additional fuzzing/file finding (Fig. 4).")
    finding_unit = find_para(doc, "Both agents reported six SQLi findings.")
    set_paragraph_text(finding_unit,
                       "These are action-level findings, not 14 or 13 independently confirmed production "
                       "vulnerabilities. Multiple payloads can map to one endpoint-class location; each run "
                       "covered five distinct locations.")

    # Replace the existing figure content with fresh values from the current run.
    old_zap_caption = find_para(doc, "Fig. 2. Architecture and request flow")
    old_zap_image = next((p for p in doc.paragraphs
                          if p._p.xpath('.//w:drawing') and p is not None
                          and p._p is not old_zap_caption._p), None)
    # Identify the ZAP figure by its position between the caption and category section.
    body_paras = doc.paragraphs
    cap_index = para_index(doc, old_zap_caption)
    zap_image = next(p for p in body_paras[cap_index + 1:]
                     if p._p.xpath('.//w:drawing'))
    zap_image._p.addnext(old_zap_caption._p)  # IJIES places figure captions below figures.
    zap_image.clear()
    zap_image.alignment = WD_ALIGN_PARAGRAPH.CENTER
    zap_image.paragraph_format.first_line_indent = Inches(0)
    zap_image.paragraph_format.keep_together = True
    zap_shape = zap_image.add_run().add_picture(str(zap_png), width=Inches(3.05))
    zap_shape._inline.docPr.set("title", "Controlled ZAP scan flow")
    zap_shape._inline.docPr.set(
        "descr", "Python controller directs ZAP spider and active scan against Juice Shop; relevant alerts are filtered and counted.")
    for shape in doc.inline_shapes:
        docpr = shape._inline.docPr
        if "ZAP" in (docpr.get("descr") or "") or "ZAP" in (docpr.get("title") or ""):
            docpr.set("title", "Controlled ZAP scan flow")
            docpr.set("descr", "Python controller, ZAP spider and active scanner, target, and alert filter.")
            shape.width = Inches(3.05)

    categories_caption = find_para(doc, "Fig. 4. Verified action-level findings")
    body_paras = doc.paragraphs
    cat_index = para_index(doc, categories_caption)
    categories_image = next(p for p in body_paras[cat_index + 1:]
                            if p._p.xpath('.//w:drawing'))
    # Keep the current category plot in place but replace stale bitmap contents.
    categories_image.clear()
    categories_image.alignment = WD_ALIGN_PARAGRAPH.CENTER
    categories_image.paragraph_format.first_line_indent = Inches(0)
    categories_shape = categories_image.add_run().add_picture(
        str(WORK / "figure_3_categories.png"), width=Inches(3.05))
    categories_shape._inline.docPr.set("title", "Verified findings by class")
    categories_shape._inline.docPr.set(
        "descr", "Q-learning and DQN verified action-level outcomes for SQL injection, XSS, and fuzzing or file probes.")
    categories_image._p.addnext(categories_caption._p)

    # Insert Figure 1 in the methods section after the shared training protocol.
    add_figure_after(
        doc, training_para, system_png,
        "Fig. 1. System workflow for reinforcement-learning-based web testing.",
        3.05, "RL web-testing system workflow",
        "Agent selects one of 120 actions; HTTP request and response are analyzed, verified, and returned as state and reward.")

    # Add a learning-trajectory figure after the paragraph describing the final discovery episode.
    milestone_para = find_para(doc, "Both agents found their first action in episode 1.")
    add_figure_after(
        doc, milestone_para, WORK / "figure_4_discovery_curve.png",
        "Fig. 3. Cumulative unique verified-action discoveries by episode.",
        3.05, "Cumulative verified-action discoveries",
        "Step curves show unique verified endpoint-payload actions discovered over 1,585 episodes for Q-learning and DQN.")

    # Cite the system figure in the prose; the old figure number now refers to ZAP.
    # Correct endpoint-only comparison language to make the unit and request count explicit.
    for paragraph in doc.paragraphs:
        if "For the two shared endpoints, the thesis reports" in paragraph.text:
            set_paragraph_text(paragraph, paragraph.text.replace(
                "the thesis reports", "the QL run log records"))
        if "The category counts show six SQLi findings for each agent." in paragraph.text:
            set_paragraph_text(paragraph, paragraph.text.replace(
                "The category counts show six SQLi findings for each agent.",
                "The category counts show six SQLi and five XSS action-level findings for each agent."))
        if "The false negative was the SVG XSS action on the track-order route." in paragraph.text:
            set_paragraph_text(paragraph, paragraph.text.replace(
                "The false negative was the SVG XSS action on the track-order route.",
                "The false negative was the SVG XSS action on the track-order route."))

    # Rebuild the bibliography in IJIES style with verified primary references.
    references = [
        "[1] C. J. C. H. Watkins and P. Dayan, “Q-learning,” Machine Learning, Vol. 8, No. 3–4, pp. 279–292, 1992, doi: 10.1007/BF00992698.",
        "[2] R. S. Sutton and A. G. Barto, Reinforcement Learning: An Introduction, 2nd ed., MIT Press, Cambridge, MA, 2018.",
        "[3] V. Mnih et al., “Human-level control through deep reinforcement learning,” Nature, Vol. 518, pp. 529–533, 2015, doi: 10.1038/nature14236.",
        "[4] F. M. Zennaro and L. Erdodi, “Modeling penetration testing with reinforcement learning using capture-the-flag challenges: Trade-offs between model-free learning and a priori knowledge,” arXiv:2005.12632, 2020.",
        "[5] L. Erdodi and F. M. Zennaro, “The Agent Web Model: Modelling web hacking for reinforcement learning,” arXiv:2009.11274, 2020.",
        "[6] R. Gangupantulu, T. Cody, P. Park, A. Rahman, L. Eisenbeiser, D. Radke, and R. Clark, “Using cyber terrain in reinforcement learning for penetration testing,” arXiv:2108.07124, 2021.",
        "[7] OWASP Foundation, “OWASP Juice Shop,” [Online]. Available: https://owasp.org/projects/juice-shop?tab=overview. Accessed: Oct. 12, 2026.",
        "[8] OWASP ZAP, “Automation Framework,” [Online]. Available: https://www.zaproxy.org/docs/automate/automation-framework/. Accessed: Oct. 12, 2026.",
        "[9] OWASP ZAP, “Getting Started,” [Online]. Available: https://www.zaproxy.org/docs/desktop/start/. Accessed: Oct. 12, 2026.",
        "[10] OWASP ZAP, “API Reference,” [Online]. Available: https://www.zaproxy.org/docs/api/. Accessed: Oct. 12, 2026.",
        "[11] OWASP ZAP, “Passive Scanner Add-on,” [Online]. Available: https://www.zaproxy.org/docs/desktop/addons/passive-scanner/. Accessed: Oct. 12, 2026.",
        "[12] OWASP ZAP, “Automation Framework: Active Scan Job,” [Online]. Available: https://www.zaproxy.org/docs/desktop/addons/automation-framework/job-ascan/. Accessed: Oct. 12, 2026.",
    ]
    refs_heading = find_para(doc, "References")
    heading_idx = para_index(doc, refs_heading)
    existing_ref_paras = []
    for p in doc.paragraphs[heading_idx + 1:]:
        if p.text.strip().startswith("["):
            existing_ref_paras.append(p)
        elif existing_ref_paras:
            break
    for i, text in enumerate(references):
        if i < len(existing_ref_paras):
            set_paragraph_text(existing_ref_paras[i], text)
            format_body(existing_ref_paras[i])
        else:
            p = insert_paragraph_after(existing_ref_paras[-1], style="Normal")
            p.add_run(text)
            format_body(p)
            existing_ref_paras.append(p)
    for p in existing_ref_paras[len(references):]:
        p._p.getparent().remove(p._p)
    for p in existing_ref_paras[:len(references)]:
        p.paragraph_format.keep_together = True

    # Use the author's confirmed conflict-of-interest declaration.
    coi = find_para(doc, "Conflict of interest:")
    set_paragraph_text(coi, "The author declares that there is no conflict of interest.")

    # Align manuscript headings and figure/table captions with the template.
    heading_sizes = {
        "1. Introduction": 12,
        "2. Materials and Methods": 12,
        "3. Results and Discussion": 12,
        "4. Conclusion": 12,
        "Conflict of Interest": 12,
        "References": 12,
    }
    for p in doc.paragraphs:
        text = p.text.strip()
        if text in heading_sizes:
            format_heading(p, heading_sizes[text])
        elif re.match(r"^(2\.[1-4](?:\.1)?|3\.[1-7])\s", text):
            format_heading(p, 11)
        elif text.startswith("Table ") and re.match(r"^Table \d+\.", text):
            format_caption(p)
        elif text.startswith("Fig. ") and re.match(r"^Fig\. \d+\.", text):
            format_caption(p)

    # Keep the benchmark and comparison tables intact while allowing them to
    # flow naturally into the next column when the current one is too short.
    find_para(doc, "Table 7.").paragraph_format.page_break_before = False
    find_para(doc, "Table 8.").paragraph_format.page_break_before = False
    keep_table_together(doc.tables[6])
    keep_table_together(doc.tables[7])

    # Keep title and author block aligned to the IJIES template's title scale.
    title = find_para(doc, "Adaptive Web Penetration Testing")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.first_line_indent = Inches(0)
    for r in title.runs:
        set_font(r, 14, bold=True)
    author = find_para(doc, "Kevin Imanuel Setiawan")
    author.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for r in author.runs:
        set_font(r, 11, bold=True)

    # Add accessible descriptions to the retained masthead and all remaining images.
    for idx, shape in enumerate(doc.inline_shapes):
        docpr = shape._inline.docPr
        if not docpr.get("title"):
            if idx == 0:
                docpr.set("title", "IJIES journal masthead")
                docpr.set("descr", "International Journal of Intelligent Engineering and Systems masthead.")
            else:
                docpr.set("title", f"Article figure {idx}")
                docpr.set("descr", "Original figure in the manuscript.")

    doc.core_properties.title = "Adaptive Web Penetration Testing with Q-Learning and Deep Q-Networks on OWASP Juice Shop"
    doc.core_properties.subject = "IJIES manuscript on reinforcement-learning-based web penetration testing"
    doc.save(str(OUTPUT))
    print(f"Wrote {OUTPUT}")
    print(f"Paragraphs: {len(doc.paragraphs)}; tables: {len(doc.tables)}; inline shapes: {len(doc.inline_shapes)}")
    print(f"Abstract words: {len(abstract.split())}")
    print(f"Body word count: {sum(len(p.text.split()) for p in doc.paragraphs)}")


if __name__ == "__main__":
    main()
