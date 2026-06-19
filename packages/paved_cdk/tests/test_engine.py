"""Declarative engine: the YAML manifest parses into the shared ServiceSpec, so a
manifest yields the same governed resources as the SDK and Copier variants. Here we
check the manifest -> spec mapping (resource correctness is covered by test_service.py)."""

from __future__ import annotations

from paved_cdk.engine import manifest


def test_manifest_parses_functions_data_apis_and_meta(tmp_path, monkeypatch):
    (tmp_path / "service.yaml").write_text(
        "service_id: scoring-service\n"
        "owner: alice@example.com\n"
        "team: ds-risk\n"
        'cost_center: "4711"\n'
        "data_apis:\n"
        "  - scoring-data\n"
        "functions:\n"
        "  - name: predict\n"
    )
    monkeypatch.chdir(tmp_path)

    spec = manifest.load("service.yaml")
    assert [f.name for f in spec.functions] == ["predict"]
    assert [d.name for d in spec.data_apis] == ["scoring-data"]

    meta = manifest.read_meta("service.yaml")
    assert meta["team"] == "ds-risk"
    assert meta["cost_center"] == "4711"


def test_data_apis_accept_mapping_form(tmp_path, monkeypatch):
    (tmp_path / "service.yaml").write_text(
        "service_id: s\ndata_apis:\n  - {name: ledger-data}\n"
    )
    monkeypatch.chdir(tmp_path)
    spec = manifest.load("service.yaml")
    assert [d.name for d in spec.data_apis] == ["ledger-data"]


def test_main_wires_team_into_account_and_stack_name(tmp_path, monkeypatch):
    """Regression: the engine must pass the manifest's team to PlatformStack, so the
    stack resolves the team's account (not CDK_DEFAULT_*) and is named $stage-$project.
    Uses a functions-less manifest to avoid Code.from_asset staging (whose relative path
    resolves against the jsii process cwd, not chdir)."""
    import glob
    import json

    (tmp_path / "service.yaml").write_text(
        "service_id: demo\nowner: a@x.io\nteam: ds\ncost_center: \"1\"\n"
        "data_apis:\n  - demo-data\n"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PAVED_CDK_STAGE", "dev")
    monkeypatch.setenv("CDK_OUTDIR", str(tmp_path / "cdk.out"))

    from paved_cdk.engine import synth

    synth.main()

    manifest_json = json.load(open(glob.glob(str(tmp_path / "cdk.out" / "manifest.json"))[0]))
    stacks = {
        k: v
        for k, v in manifest_json["artifacts"].items()
        if v.get("type") == "aws:cloudformation:stack"
    }
    assert "dev-demo" in stacks  # $stage-$project
    assert stacks["dev-demo"]["environment"] == "aws://111111111111/eu-west-1"  # ds dev
