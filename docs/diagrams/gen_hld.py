#!/usr/bin/env python3
"""Generate a draw.io (diagrams.net) HLD with REAL AWS icons.

Diagrams-as-code: emits ``paved-cdk-hld.drawio`` with two pages -
"As-Is (current)" and "To-Be (target)" - using the official AWS 2019 shape
library (``mxgraph.aws4.*``), so Lambda/DynamoDB/S3/SageMaker/KMS/CloudFormation
render as the real AWS glyphs in draw.io.

Run:  python3 docs/diagrams/gen_hld.py
Open: docs/diagrams/paved-cdk-hld.drawio in https://app.diagrams.net
"""

from __future__ import annotations

import html
from pathlib import Path

from defusedxml.minidom import parseString  # hardened XML parser (no XXE)

# --- AWS 2019 resource-icon category colours (approximate brand colours; the
#     glyph itself is what identifies the service) ---------------------------
AWS_COLOR = {
    "user": "#232F3E",
    "cloudformation": "#E7157B",
    "dynamodb": "#C925D1",
    "s3": "#7AA116",
    "lambda": "#ED7100",
    "identity_and_access_management": "#DD344C",
    "api_gateway": "#E7157B",
    "step_functions": "#E7157B",
    "aurora": "#C925D1",
    "simple_notification_service": "#E7157B",
    "elastic_container_registry": "#ED7100",
    "sagemaker": "#01A88D",
    "key_management_service": "#DD344C",
    "virtual_private_cloud": "#8C4FFF",
}


def icon_style(res_icon: str) -> str:
    color = AWS_COLOR[res_icon]
    return (
        "sketch=0;outlineConnect=0;fontColor=#232F3E;gradientColor=none;"
        f"fillColor={color};strokeColor=none;dashed=0;verticalLabelPosition=bottom;"
        "verticalAlign=top;align=center;html=1;fontSize=10;fontStyle=0;aspect=fixed;"
        f"shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.{res_icon};"
    )


ACCOUNT_GROUP = (
    "sketch=0;outlineConnect=0;gradientColor=none;html=1;whiteSpace=wrap;fontSize=12;"
    "fontStyle=1;container=0;pointerEvents=0;collapsible=0;shape=mxgraph.aws4.group;"
    "grpIcon=mxgraph.aws4.group_account;strokeColor=#CD2264;fillColor=none;"
    "verticalAlign=top;align=left;fontColor=#CD2264;"
)
GITHUB_FRAME = (
    "rounded=1;whiteSpace=wrap;html=1;strokeColor=#24292E;fillColor=#F6F8FA;"
    "verticalAlign=top;align=left;fontColor=#24292E;fontStyle=1;"
)
STEPS_FRAME = (
    "rounded=1;whiteSpace=wrap;html=1;strokeColor=#B85450;fillColor=#FDEDEC;"
    "verticalAlign=top;align=center;fontColor=#B85450;fontStyle=1;"
)
BOX = "rounded=1;whiteSpace=wrap;html=1;strokeColor=#6C8EBF;fillColor=#DAE8FC;fontSize=10;"
BOX_GREEN = "rounded=1;whiteSpace=wrap;html=1;strokeColor=#82B366;fillColor=#D5E8D4;fontSize=10;"
BOX_RED = "rounded=1;whiteSpace=wrap;html=1;strokeColor=#B85450;fillColor=#F8CECC;fontSize=10;"
GHA = "rounded=1;whiteSpace=wrap;html=1;strokeColor=#1F6FEB;fillColor=#DDF4FF;fontSize=10;fontStyle=1;"

EDGE = "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;strokeColor=#333333;fontSize=9;"
EDGE_DASH = "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=open;dashed=1;strokeColor=#666;fontSize=9;"
EDGE_RED = "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=open;dashed=1;strokeColor=#B85450;strokeWidth=2;fontColor=#B85450;fontSize=9;"
EDGE_GREEN = "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=open;dashed=1;strokeColor=#82B366;strokeWidth=2;fontColor=#5E8E3E;fontSize=9;"


class Page:
    def __init__(self, name: str, pid: str):
        self.name = name
        self.pid = pid
        self.cells: list[str] = []

    def _esc(self, value: str) -> str:
        return html.escape(value, quote=True)

    def node(self, cid, value, style, x, y, w, h):
        self.cells.append(
            f'<mxCell id="{self.pid}_{cid}" value="{self._esc(value)}" style="{style}" '
            f'vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" '
            f'height="{h}" as="geometry"/></mxCell>'
        )

    def icon(self, cid, res_icon, label, x, y, size=48):
        self.node(cid, label, icon_style(res_icon), x, y, size, size)

    def edge(self, cid, src, tgt, label="", style=EDGE):
        self.cells.append(
            f'<mxCell id="{self.pid}_{cid}" value="{self._esc(label)}" style="{style}" '
            f'edge="1" parent="1" source="{self.pid}_{src}" target="{self.pid}_{tgt}">'
            f'<mxGeometry relative="1" as="geometry"/></mxCell>'
        )

    def xml(self) -> str:
        body = "".join(self.cells)
        return (
            f'<diagram name="{self._esc(self.name)}" id="{self.pid}">'
            f'<mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" guides="1" '
            f'tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
            f'pageWidth="1169" pageHeight="826" math="0" shadow="0"><root>'
            f'<mxCell id="0"/><mxCell id="1" parent="0"/>{body}</root></mxGraphModel></diagram>'
        )


def br(*lines: str) -> str:
    return "<br>".join(lines)


# ====================== Page 1: As-Is (current) ============================
asis = Page("As-Is (current)", "asis")
asis.icon("dev", "user", "Developer", 40, 300)
asis.node("repo", br("GitHub repo", "branches: development / main / production"),
          GITHUB_FRAME, 120, 295, 240, 60)
asis.node("gha", "GitHub Actions CI/CD", GHA, 170, 405, 190, 46)
asis.node("steps", "CDK Pipeline Steps", STEPS_FRAME, 140, 495, 280, 300)
steps = [
    ("s1", "1 · Install deps (Python + CDK CLI)", BOX),
    ("s2", "2 · Authenticate via OIDC (assume roles)", BOX),
    ("s3", "3 · Fetch config from DynamoDB (VPC, subnets, stack name)", BOX_RED),
    ("s4", "4 · CDK bootstrap (if first deploy)", BOX),
    ("s5", "5 · CDK synth (Python -> CFN JSON)", BOX),
    ("s6", "6 · CDK deploy", BOX),
    ("s7", "7 · Archive template to S3 + log to DynamoDB", BOX),
]
y = 525
for cid, label, style in steps:
    asis.node(cid, label, style, 155, y, 250, 30)
    y += 38
# governance account
asis.node("govgrp", "Backend AWS Account - Central Governance", ACCOUNT_GROUP, 480, 60, 440, 230)
asis.icon("cfgdb", "dynamodb", br("Config Table", "Project+Branch -> Params"), 520, 110)
asis.icon("logdb", "dynamodb", "Log Table", 720, 110)
asis.icon("arch", "s3", "Template Archive", 620, 205)
# cfn + resource account
asis.icon("cfn", "cloudformation", "CloudFormation Stack", 470, 560)
asis.node("resgrp", "Resource AWS Account - Target Environment", ACCOUNT_GROUP, 590, 470, 470, 330)
res_icons = [
    ("rl", "lambda", "Lambda", 630, 520), ("ri", "identity_and_access_management", "IAM Roles", 770, 520),
    ("rg", "api_gateway", "API Gateway", 910, 520),
    ("rs", "s3", "S3 Buckets", 630, 630), ("rsf", "step_functions", "Step Functions", 770, 630),
    ("ra", "aurora", "Aurora DB", 910, 630),
    ("rsn", "simple_notification_service", "SNS Topics", 630, 730), ("re", "elastic_container_registry", "ECR Repos", 770, 730),
    ("rv", "virtual_private_cloud", "VPC Endpoints", 910, 730),
]
for cid, res, label, x, yy in res_icons:
    asis.icon(cid, res, label, x, yy)
# edges
asis.edge("e1", "dev", "repo", "git push")
asis.edge("e2", "repo", "gha", "triggers on push")
asis.edge("e3", "gha", "s1")
for a, b in [("s1", "s2"), ("s2", "s3"), ("s3", "s4"), ("s4", "s5"), ("s5", "s6"), ("s6", "s7")]:
    asis.edge(f"c{a}{b}", a, b)
asis.edge("e_cfg", "s3", "cfgdb", "reads config", EDGE_RED)
asis.edge("e_arch", "s7", "arch", "stores template", EDGE_DASH)
asis.edge("e_log", "s7", "logdb", "logs deployment", EDGE_DASH)
asis.edge("e_dep", "s6", "cfn", "deploys stack")
asis.edge("e_cre", "cfn", "rl", "creates / updates")

# ====================== Page 2: To-Be (target) =============================
tobe = Page("To-Be (target)", "tobe")
tobe.icon("dev", "user", "Developer", 30, 320)
tobe.node("repo", br("GitHub consumer repo", "trunk: main"), GITHUB_FRAME, 150, 318, 230, 56)
# platform repo frame + contents
tobe.node("platrepo", "Platform repo - single source of truth", GITHUB_FRAME, 110, 40, 340, 200)
tobe.node("lib", "Library: constructs + governance + resolver", BOX, 128, 80, 304, 34)
tobe.node("reg", "AccountRegistry (static in code)", BOX_GREEN, 128, 128, 304, 34)
tobe.node("tpl", "Copier template", BOX, 128, 176, 304, 34)
# pipeline
tobe.node("rw", br("Reusable workflow", "(workflow_call)"), GHA, 520, 60, 200, 50)
tobe.node("val", br("validate", "ruff + pytest + synth", "(no AWS login)"), BOX_GREEN, 520, 260, 200, 64)
tobe.node("ddev", "deploy -> dev", BOX, 540, 390, 150, 38)
tobe.node("dtest", "deploy -> preprod", BOX, 540, 460, 150, 38)
tobe.node("dprod", br("deploy -> prod", "(required reviewers)"), BOX, 540, 530, 150, 46)
# accounts
tobe.node("devgrp", "AWS dev account", ACCOUNT_GROUP, 780, 330, 470, 120)
tobe.icon("d_cfn", "cloudformation", "CloudFormation", 810, 365)
tobe.icon("d_api", "api_gateway", "API Gateway (private)", 910, 365)
tobe.icon("d_s3", "s3", "S3 (KMS)", 1010, 365)
tobe.icon("d_kms", "key_management_service", "KMS", 1110, 365)
tobe.node("testgrp", "AWS preprod account", ACCOUNT_GROUP, 780, 470, 470, 95)
tobe.icon("t_cfn", "cloudformation", "CloudFormation (same baseline)", 810, 500)
tobe.node("prodgrp", "AWS prod account", ACCOUNT_GROUP, 780, 585, 470, 95)
tobe.icon("p_cfn", "cloudformation", "CloudFormation (same baseline)", 810, 615)
# governance (audit only)
tobe.node("govgrp", "Backend account - Governance (audit only)", ACCOUNT_GROUP, 780, 40, 470, 130)
tobe.icon("g_arch", "s3", "Template archive", 820, 80)
tobe.icon("g_log", "dynamodb", "Log table", 1000, 80)
# edges
tobe.edge("e1", "dev", "repo", "git push")
tobe.edge("e2", "repo", "rw", "uses @tag")
tobe.edge("e_lib", "lib", "repo", "pinned by tag", EDGE_DASH)
tobe.edge("e_tpl", "tpl", "repo", "scaffolds", EDGE_DASH)
tobe.edge("e3", "rw", "val")
tobe.edge("e_reg", "reg", "val", "resolved at synth", EDGE_GREEN)
tobe.edge("c1", "val", "ddev")
tobe.edge("c2", "ddev", "dtest")
tobe.edge("c3", "dtest", "dprod")
tobe.edge("o1", "ddev", "devgrp", "OIDC")
tobe.edge("o2", "dtest", "testgrp", "OIDC")
tobe.edge("o3", "dprod", "prodgrp", "OIDC")
tobe.edge("e_audit", "dprod", "govgrp", "archive + log", EDGE_DASH)

# ====================== Page 3: Repos & Workflows ==========================
LANE = ("rounded=0;whiteSpace=wrap;html=1;fillColor=#F6F8FA;strokeColor=#24292E;"
        "verticalAlign=top;align=left;fontStyle=1;fontSize=13;fontColor=#24292E;")
LANE_C = ("rounded=0;whiteSpace=wrap;html=1;fillColor=#EFF6FF;strokeColor=#1F6FEB;"
          "verticalAlign=top;align=left;fontStyle=1;fontSize=13;fontColor=#1F6FEB;")

repos = Page("Repos & Workflows", "repos")
# --- Lane A: Platform repo (source of truth) ---
repos.node("laneA", "Platform repo - michaelfecher/paved-cdk  (source of truth)",
           LANE, 40, 40, 1180, 230)
repos.node("lib", "Library (constructs + governance + resolver)", BOX, 70, 80, 250, 30)
repos.node("reg", "AccountRegistry (static config)", BOX_GREEN, 340, 80, 230, 30)
repos.node("tpl", "Copier template", BOX, 590, 80, 160, 30)
repos.node("rwf", "Reusable workflow (cdk-deploy.yml)", GHA, 770, 80, 240, 30)
repos.node("a_pr", "PR: add account /<br>new construct / template change", BOX, 70, 160, 190, 50)
repos.node("a_ci", "CI: ruff + pytest +<br>cdk synth", GHA, 300, 160, 180, 50)
repos.node("a_merge", "merge -> main", BOX, 520, 165, 130, 40)
repos.node("a_rel", "tag release vX.Y.Z<br>(GitHub Release)", BOX_GREEN, 690, 160, 170, 50)
repos.edge("a1", "a_pr", "a_ci")
repos.edge("a2", "a_ci", "a_merge")
repos.edge("a3", "a_merge", "a_rel")

# --- Lane B: Consumer repo (per DS project) ---
repos.node("laneB", "Consumer repo - per DS project", LANE_C, 40, 310, 1180, 300)
repos.node("b_scaffold", "copier copy @tag<br>(one-time scaffold)", BOX, 70, 360, 150, 48)
repos.node("b_edit", "DS edits app.py<br>(PR / push to main)", BOX, 250, 360, 150, 48)
repos.node("b_call", "thin caller:<br>uses reusable workflow @tag", GHA, 430, 360, 180, 48)
repos.node("b_val", "validate<br>(no AWS login)", BOX_GREEN, 640, 360, 150, 48)
repos.node("b_dev", "deploy -> dev", BOX, 820, 360, 120, 36)
repos.node("b_test", "deploy -> preprod", BOX, 820, 420, 120, 36)
repos.node("b_prod", "deploy -> prod<br>(reviewers)", BOX, 820, 480, 120, 44)
repos.icon("c_dev", "cloudformation", "AWS dev", 1000, 356, 44)
repos.icon("c_test", "cloudformation", "AWS preprod", 1000, 416, 44)
repos.icon("c_prod", "cloudformation", "AWS prod", 1000, 478, 44)
repos.edge("b1", "b_scaffold", "b_edit")
repos.edge("b2", "b_edit", "b_call")
repos.edge("b3", "b_call", "b_val")
repos.edge("b4", "b_val", "b_dev")
repos.edge("b5", "b_dev", "b_test")
repos.edge("b6", "b_test", "b_prod")
repos.edge("bo1", "b_dev", "c_dev", "OIDC")
repos.edge("bo2", "b_test", "c_test", "OIDC")
repos.edge("bo3", "b_prod", "c_prod", "OIDC")

# --- Cross-lane handoffs (how the two workflows interlock) ---
# Force a vertical drop (exit bottom of source, enter top of target) so labels
# land in the inter-lane gap instead of overlapping the top-lane boxes.
_drop = ";exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;"
repos.edge("x_tag", "a_rel", "b_call", "git tag vX.Y.Z - pinned by consumer", EDGE_DASH + _drop)
repos.edge("x_tpl", "tpl", "b_scaffold", "copier copy / update", EDGE_DASH + _drop)
repos.edge("x_reg", "reg", "b_val", "resolved at synth", EDGE_GREEN + _drop)

# ====================== Assemble & write ===================================
xml = f'<mxfile host="app.diagrams.net" type="device">{asis.xml()}{tobe.xml()}{repos.xml()}</mxfile>'
parseString(xml)  # well-formedness assertion

out = Path(__file__).with_name("paved-cdk-hld.drawio")
out.write_text(xml, encoding="utf-8")
print(f"wrote {out} ({len(xml)} bytes); XML is well-formed")
