# Architecture — Paved CDK

Diagrams of the **currently built** architecture (reference PoC). Source of truth is the
code under `packages/paved_cdk/` and `template/`; the ADRs under `docs/adr/`
record the rationale.

> **Draw.io / diagrams.net:** every Mermaid diagram can be imported directly:
> `Arrange → Insert → Advanced → Mermaid…`, then paste the code block. The diagrams stay
> editable and live next to the code.
>
> **HLD with real AWS icons:** `docs/diagrams/paved-cdk-hld.drawio` — open in
> [app.diagrams.net](https://app.diagrams.net). Two pages (*As-Is* / *To-Be*) using the
> official AWS 2019 shape library (real Lambda/DynamoDB/S3/SageMaker/KMS/CloudFormation
> glyphs). Static exports for slides: `docs/diagrams/hld-as-is.png`,
> `docs/diagrams/hld-to-be.png`.
>
> Generated from `docs/diagrams/gen_hld.py` (diagrams-as-code). Regenerate the `.drawio`
> with `python3 docs/diagrams/gen_hld.py`. For PNGs, the `drawio` CLI `--page-index` flag is
> unreliable (it re-exports page 0); the robust recipe is to **split the multi-page file and
> export each single page**:
> ```bash
> python3 - <<'PY'
> import re, pathlib
> xml = pathlib.Path("docs/diagrams/paved-cdk-hld.drawio").read_text()
> for name, d in zip(["asis","tobe","repos"], re.findall(r"<diagram\b.*?</diagram>", xml, re.S)):
>     pathlib.Path(f"/tmp/page-{name}.drawio").write_text(f'<mxfile>{d}</mxfile>')
> PY
> drawio -x -f png --scale 2 -o docs/diagrams/hld-as-is.png            /tmp/page-asis.drawio  --no-sandbox
> drawio -x -f png --scale 2 -o docs/diagrams/hld-to-be.png            /tmp/page-tobe.drawio  --no-sandbox
> drawio -x -f png --scale 2 -o docs/diagrams/hld-repos-workflows.png  /tmp/page-repos.drawio --no-sandbox
> ```
> (Or open the `.drawio` in draw.io and `File → Export as → PNG` per page.)

---

## 1. HLD — As-Is vs To-Be

The two diagrams below are meant for a side-by-side, stakeholder-facing comparison.

### 1a. As-Is (current HLD)

```mermaid
flowchart TB
  DEV([Developer]) -->|git push| REPO["GitHub repo<br/>branches: development / main / production"]
  REPO -->|triggers on push| GHA["GitHub Actions CI/CD"]

  subgraph gov["Backend AWS Account — Central Governance"]
    CFGDB[(DynamoDB Config Table<br/>Project + Branch then Params)]
    LOGDB[(DynamoDB Log Table)]
    ARCH[(S3 — Template Archive)]
  end

  subgraph steps["CDK Pipeline Steps"]
    direction TB
    S1["1 · Install deps (Python + CDK CLI)"]
    S2["2 · Authenticate via OIDC (assume roles)"]
    S3["3 · Fetch config from DynamoDB<br/>(VPC, subnets, stack name)"]
    S4["4 · CDK bootstrap (if first deploy)"]
    S5["5 · CDK synth (Python then CFN JSON)"]
    S6["6 · CDK deploy"]
    S7["7 · Archive template to S3 + log to DynamoDB"]
    S1 --> S2 --> S3 --> S4 --> S5 --> S6 --> S7
  end

  GHA --> S1
  S3 -.reads config.-> CFGDB
  S7 -.stores template.-> ARCH
  S7 -.logs deployment.-> LOGDB
  S6 -->|deploys stack| CFN["CloudFormation Stack"]

  subgraph res["Resource AWS Account — Target Environment"]
    CFN --> R["Lambda · IAM · API GW · S3 · Step Functions<br/>Aurora · SNS · ECR · VPC Endpoints"]
  end

  classDef bad fill:#fdd,stroke:#c33,stroke-width:2px
  class CFGDB,S3 bad
```

**What undermines the design (red nodes + structure):**

1. **Config in DynamoDB, fetched at synth (step 3).** Non-deterministic (same commit can
   synth differently), a *second* source of truth outside Git, no PR/diff/test on config
   changes. It also reduces CDK to a templater fed by a table — which is exactly why "why
   even use CDK?" comes up.
2. **No validation/governance gate.** No `ruff` / `pytest` / `cdk-nag` step before deploy.
3. **Branch-per-environment** (development/main/production → DEV/TEST/PROD) invites drift
   between branches and merge pain.
4. **The platform itself is invisible** — only pipeline + config fetch are shown; the
   construct library, governance and the DS-facing interface (the actual product) are not.

### 1b. To-Be (target)

```mermaid
flowchart TB
  DEV([Developer]) -->|"PR / push to main"| REPO["GitHub consumer repo<br/>single trunk: main"]
  REPO -->|"uses reusable workflow @tag"| RW["Reusable workflow (platform repo)"]

  subgraph platform["Platform repo — single source of truth"]
    LIB["Library: constructs + governance<br/>+ PlatformEnvironment"]
    REG[(AccountRegistry<br/>static in code)]
    TPL["Copier template"]
  end

  RW --> VAL["validate<br/>ruff + pytest + cdk synth + cdk-nag<br/>(no AWS login)"]
  VAL --> DEVS["deploy → dev"] --> TESTS["deploy → preprod"] --> PRODS["deploy → prod<br/>(required reviewers)"]

  REG -.resolved at synth.-> VAL
  LIB -.pinned by tag.-> REPO
  TPL -.scaffolds.-> REPO

  DEVS -.OIDC.-> ADEV[(AWS dev)]
  TESTS -.OIDC.-> ATEST[(AWS preprod)]
  PRODS -.OIDC.-> APROD[(AWS prod)]

  subgraph govt["Backend account — Governance (audit only)"]
    ARCH[(S3 template archive)]
    LOGDB[(DynamoDB log table)]
  end
  PRODS -.archive + log.-> ARCH & LOGDB

  classDef good fill:#dfd,stroke:#3a3,stroke-width:2px
  class REG,VAL good
```

**What changes:** DynamoDB **config** table removed → static `AccountRegistry` in the repo
(deterministic, PR-reviewed); a **validate gate** (ruff + pytest + cdk-nag) runs before any
deploy, with **no AWS login** because synth is offline; **branch-per-env → single trunk +
stage promotion** (dev → preprod → prod via GitHub Environments); the **library + Copier
template** are first-class. The DynamoDB **log** table and S3 **template archive** stay —
that is a legitimate audit trail.

---

## 2. Three-layer overview

What the Data Scientist touches, what the platform does automatically, and where the
account-specific values come from.

```mermaid
flowchart TB
  DS([Data Scientist<br/>no IaC experience])

  subgraph tpl["Template layer — Copier"]
    COPIER[copier copy / update]
    ANS[".copier-answers.yml<br/>Owner · Team · CostCenter · platform_version"]
  end

  subgraph proj["Consumer project (rendered)"]
    APP["app.py ~10 lines<br/>PlatformStack + SecureDataApi"]
    PYPROJ["pyproject.toml<br/>git-tag pin on the library"]
    CALLER[".github/workflows/deploy.yml<br/>thin caller of the reusable pipeline"]
  end

  subgraph lib["Library layer — paved_cdk (the product)"]
    PS[PlatformStack]
    ENV[PlatformEnvironment<br/>resolver]
    REG[(AccountRegistry<br/>static in code · source of truth)]
    GOV[apply_platform_governance<br/>Aspects + cdk-nag]
    L3[SecureDataApi L3]
  end

  subgraph acct["Target AWS account (Landing Zone)"]
    VPC[(Shared VPC + private subnets)]
    KMS[(KMS data key)]
    PB[(Permissions boundary policy)]
  end

  DS -->|answers questions| COPIER
  COPIER --> ANS
  COPIER --> APP & PYPROJ & CALLER
  APP --> PS
  PYPROJ -.git tag.-> lib
  PS --> ENV
  PS --> GOV
  APP --> L3
  L3 -->|PlatformEnvironment.of| ENV
  ENV -->|resolve account_id, concrete IDs| REG
  REG -.IDs reference.-> VPC & KMS & PB

  classDef ds fill:#fde,stroke:#c39
  classDef plat fill:#def,stroke:#39c
  class DS ds
  class PS,ENV,GOV,L3,REG plat
```

**Key point:** the DS declares *what* they want (a notebook). *How* (VPC, subnet, KMS, IAM
boundary, tags, compliance) is resolved by the library from the account. No `vpc=`, `env=`,
`kms=` in user code.

---

## 3. Deterministic config resolution (static registry)

The subtlest and most important part: how the target account becomes the typed
`PlatformConfig` — **deterministically, without AWS access** (ADR 0008).

```mermaid
sequenceDiagram
    autonumber
    participant CLI as cdk synth/deploy
    participant PS as PlatformStack
    participant ENV as PlatformEnvironment
    participant REG as AccountRegistry (in code)
    participant CFG as PlatformConfig

    CLI->>PS: instantiate (env from CDK_DEFAULT_ACCOUNT/REGION)
    PS->>ENV: resolve(self)
    Note over ENV: Guard: fails if account/region<br/>is a token (concrete env required)

    ENV->>REG: resolve(account_id)
    alt account in registry
        REG-->>ENV: PlatformAccount<br/>(VPC, subnets, AZs, KMS, SG, boundary, env)
    else unknown
        REG-->>ENV: PlatformConfigError<br/>"onboard via pull request"
    end

    rect rgb(235,255,235)
    Note over ENV: Built from CONCRETE strings — no AWS call:<br/>from_vpc_attributes / from_key_arn / from_security_group_id<br/>Branch on env: prod → RETAIN, else DESTROY
    ENV->>CFG: PlatformConfig (frozen dataclass)
    end

    CFG-->>PS: returned (once per stack, cached via .of())
    PS->>PS: apply_platform_governance(...)
```

Same commit → same template. Each field of a `PlatformAccount` flows into the template via
a CDK importer, no lookup:

| Field (`PlatformAccount`) | Used by | Result in the template |
|---|---|---|
| `vpc_id`, `private_subnet_ids`, `availability_zones` | `Vpc.from_vpc_attributes` | `IVpc`, concrete subnet ids |
| `execute_api_vpc_endpoint_id` | `InterfaceVpcEndpoint.from_interface_vpc_endpoint_attributes` | `IInterfaceVpcEndpoint` (private API) |
| `kms_key_arn` | `Key.from_key_arn` | `IKey`, concrete key id |
| `permissions_boundary_arn` | set by `PermissionsBoundaryAspect` | ARN on **every** `CfnRole` |
| `environment` | branch in the resolver | `prod → RemovalPolicy.RETAIN`, log retention, `Environment` tag |

> The only SSM-like element in a synthesized template is CDK's own `BootstrapVersion`
> parameter — unavoidable and unrelated to our config.

> **Account ids come from the environment.** To keep real account numbers out of the repo,
> `account_id` is read per stage from `PAVED_CDK_{DEV,PREPROD,PROD}_ACCOUNT_ID` (placeholder
> fallback for offline import/tests), and the KMS/boundary ARNs are *built* from the resolved
> id. The rest of the baseline stays static. Resolution is still deterministic for a given
> environment — the env vars are set once per deploy target, not fetched at synth.

---

## 4. Governance every stack gets

`apply_platform_governance(stack, cfg, tags)` — guardrails enforced in code, not by docs or
discipline (ADR 0005).

```mermaid
flowchart LR
  START([PlatformStack constructor]) --> G[apply_platform_governance]

  G --> PB["1 · PermissionsBoundaryAspect<br/>sets boundary on EVERY CfnRole<br/>(incl. vendor constructs)"]
  G --> TAGS["2 · Default tags + Environment tag"]
  G --> VAL{"3 · Mandatory tags present?<br/>Owner · Team · CostCenter · Environment"}
  G --> ENC["4 · EncryptionEnforcerAspect<br/>fail-closed on missing encryption"]
  G --> NAG["5 · cdk-nag AwsSolutionsChecks<br/>at app scope (once)"]

  VAL -- no --> ERR[["PlatformConfigError<br/>with remediation → synth fails"]]
  VAL -- yes --> OK([continue])
  NAG --> SUP["pre-registered NagSuppressions<br/>IAM4/IAM5 with justification<br/>→ DS never reads nag output"]

  classDef fail fill:#fdd,stroke:#c33
  class ERR fail
```

---

## 5. Uniform pipeline — event-driven, 3 stages, platform-owned auth (ADR 0011)

One reusable workflow; the master and every consumer call it with a thin caller pinned by
`@tag` (ADR 0007). The event decides what happens; the Data Scientist sets **nothing
AWS-specific**.

```mermaid
flowchart TB
  subgraph consumer["Consumer / master repo"]
    THIN[".github/workflows/deploy.yml<br/>uses: …/cdk-deploy.yml@tag<br/>with: stack_name (NO secrets)"]
  end

  subgraph platform["Platform repo — central source of truth"]
    RW["cdk-deploy.yml (workflow_call)"]
    REG[(AccountRegistry<br/>static in code)]
    VARS[["GitHub variables (platform-set):<br/>PAVED_CDK_*_ACCOUNT_ID<br/>→ OIDC role by convention"]]
  end

  THIN -->|"@tag"| RW
  RW --> V["validate<br/>ruff · cdk synth · cdk-nag<br/>(no AWS login)"]
  V --> D{"Event?"}

  D -- "PR (same-repo)" --> PV["preview → dev<br/>pr-N-stack (ephemeral)"]
  D -- "PR closed" --> PD["destroy pr-N-stack"]
  D -- "push main" --> DEV
  D -- "push tag vX.Y.Z" --> DEV

  subgraph stages["release promotion (tag only)"]
    DEV["deploy → dev"] --> PRE["deploy → preprod"] --> PROD["deploy → prod<br/>(required reviewers)"]
  end

  PV -.OIDC.-> ADEV[(AWS dev)]
  PD -.OIDC.-> ADEV
  DEV -.OIDC.-> ADEV
  PRE -.OIDC.-> APRE[(AWS preprod)]
  PROD -.OIDC.-> APROD[(AWS prod)]
  VARS -.role ARN + account id.-> DEV & PRE & PROD & PV
  REG -.baseline per account.-> ADEV & APRE & APROD

  classDef prod fill:#fee,stroke:#c33
  class PROD,APROD prod
```

**Mechanics:**
- **dev** gets every `main` push; **preprod & prod only a release tag** `vX.Y.Z` (prod with
  Required Reviewers). A **PR** gets a live, ephemeral `pr-<n>-<slug>` preview in **dev**
  (same-repo only), destroyed when the PR closes — the prefix comes from `STACK_PREFIX`, which
  `PlatformStack` applies transparently.
- **Deploy auth is platform-owned:** per-stage account ids are GitHub **variables**
  (not secrets), the OIDC role ARN is derived by convention; the same ids feed the registry so
  synth resolves the baseline. The thin caller passes **no secrets and no AWS config**.
- Pipeline updates = bump the `@tag` in the caller (via `copier update`).

---

## 6. Template distribution & update propagation (Copier)

Why Copier over Cookiecutter: `copier update` pulls platform improvements into existing
projects via a 3-way merge.

```mermaid
flowchart LR
  subgraph t["Platform repo /template"]
    CY[copier.yml<br/>questions]
    TPL["project/*.jinja"]
  end

  CY & TPL -->|"copier copy<br/>v0.1.0"| P0["Project @v0.1.0<br/>+ .copier-answers.yml<br/>(stores answers + version)"]

  TPL -.->|platform releases v0.2.0| T2[new template tag]
  P0 -->|copier update| MERGE{{"3-way merge:<br/>old template ↔ new template ↔ local changes"}}
  T2 --> MERGE
  MERGE --> P1["Project @v0.2.0<br/>pipeline ref + lib pin bumped"]

  note["keep app.py thin →<br/>opinion in the library, else merge conflicts"]:::n
  MERGE -.- note
  classDef n fill:#ffd,stroke:#cc3
```

**Library distribution** (no CodeArtifact, ADR 0006): the rendered `pyproject.toml` pins the
library directly by git tag —
`[tool.uv.sources] paved-cdk = { git = …, tag = "v0.1.0", subdirectory = … }`.
`copier update` bumps this tag in lockstep with the pipeline tag.

---

## 7. Library components (class / module view)

```mermaid
classDiagram
  class PlatformStack {
    +platform_config: PlatformConfig
    +__init__(scope, id, tags)
    -env from CDK_DEFAULT_ACCOUNT/REGION
    -resolve() once, then via .of()
  }
  class PlatformEnvironment {
    +resolve(scope) PlatformConfig
    +of(scope) PlatformConfig
  }
  class PlatformConfig {
    <<frozen dataclass>>
    +account, region, environment
    +vpc: IVpc
    +private_subnet_ids: list
    +execute_api_vpc_endpoint: IInterfaceVpcEndpoint
    +kms_key: IKey
    +permissions_boundary_arn: str
    +log_retention
    +is_production: bool
  }
  class SecureDataApi {
    <<catalog: paved_cdk.storage>>
    +api_name
    -bucket: KMS-encrypted, no public access
    -api: PRIVATE, VPC-endpoint only
    -prod → RETAIN
  }
  class SecureLambda {
    <<catalog: paved_cdk.compute>>
    +code, handler, runtime
    -in-VPC, KMS-encrypted env
    -dedicated log group
  }
  class AccountRegistry {
    <<source of truth>>
    resolve(account_id) PlatformAccount
  }
  class PlatformAccount {
    <<frozen dataclass>>
    +account_id, region, environment, team
    +vpc_id, private_subnet_ids, availability_zones
    +execute_api_vpc_endpoint_id
    +kms_key_arn, permissions_boundary_arn
  }
  class PermissionsBoundaryAspect
  class EncryptionEnforcerAspect

  PlatformStack --> PlatformEnvironment : resolve()
  PlatformStack ..> PlatformConfig : holds
  PlatformStack --> PermissionsBoundaryAspect : Aspect
  PlatformStack --> EncryptionEnforcerAspect : Aspect
  PlatformEnvironment --> AccountRegistry : resolve(account_id)
  AccountRegistry ..> PlatformAccount : provides
  PlatformEnvironment ..> PlatformConfig : builds from PlatformAccount
  SecureDataApi --> PlatformEnvironment : .of(self)
  SecureDataApi ..> PlatformConfig : consumes
  SecureLambda --> PlatformEnvironment : .of(self)
  SecureLambda ..> PlatformConfig : consumes
```

> **Catalog pattern:** constructs are an à-la-carte catalog (namespaced
> `paved_cdk.storage` / `paved_cdk.compute`). A consumer instantiates only what it needs;
> importing the library deploys nothing (*instantiation ≠ deployment*). `SecureLambda` shows
> the "secure envelope vs filling" split — the library wraps the resource securely, the
> workload supplies the code via `Code.from_asset(...)`. See [building-blocks](building-blocks.md).

---

## 8. C4 — Container diagram (static account registry, GitOps)

The current architecture: GitHub as source of truth, static registry, deterministic.

```mermaid
C4Container
    title Container diagram — Paved CDK

    Person(ds, "Data Scientist", "No/no desired IaC experience")
    Person(pe, "Platform Engineer", "Maintains library, template, registry")

    Enterprise_Boundary(gh, "GitHub — source of truth") {
        System_Boundary(plat, "Platform repo") {
            Container(lib, "Library paved_cdk", "Python / aws-cdk-lib", "PlatformStack, constructs, resolver, governance")
            ContainerDb(reg, "AccountRegistry", "Python classes in code", "All accounts + baseline; deterministic, PR-reviewed")
            Container(tpl, "Copier template", "Jinja", "Scaffolds consumer projects")
            Container(pipe, "Reusable pipeline", "GitHub Actions", "validate then dev then preprod then prod")
        }
        System_Boundary(cons, "Consumer repo — per DS project") {
            Container(app, "CDK app", "Python", "app.py ~10 lines + .copier-answers")
        }
    }

    System_Ext(aws, "AWS accounts", "dev / preprod / prod per team")

    Rel(pe, reg, "PR: new PlatformAccount", "git")
    Rel(ds, tpl, "copier copy / update", "git+https @tag")
    Rel(tpl, app, "renders")
    Rel(app, lib, "pins @git-tag, imports")
    Rel(lib, reg, "resolve(account) at synth", "in-process")
    Rel(app, pipe, "uses: workflow_call @tag")
    Rel(pipe, aws, "cdk deploy via OIDC", "CloudFormation")

    UpdateLayoutConfig($c4ShapeInRow="2", $c4BoundaryInRow="1")
```

> Note: `AccountRegistry` is drawn as a separate "ContainerDb" to stress its role as the
> *data source* — technically it is a module **inside** the library.

## 9. C4 — Component diagram (inside the library)

How resolution is wired internally — the single seam `PlatformEnvironment`.

```mermaid
C4Component
    title Component diagram — Library paved_cdk

    Person(ds, "Data Scientist", "Writes ~10 lines")

    Container_Boundary(lib, "Library paved_cdk") {
        Component(stack, "PlatformStack", "cdk.Stack subclass", "Sets env, resolves config once, applies governance")
        Component(env, "PlatformEnvironment", "Resolver / the seam", "resolve(scope) returns PlatformConfig")
        Component(reg, "AccountRegistry", "Static config", "account id to PlatformAccount")
        Component(acct, "PlatformAccount", "frozen dataclass", "One account's baseline (VPC, KMS, boundary)")
        Component(cfg, "PlatformConfig", "frozen dataclass", "Resolved, typed config")
        Component(gov, "Governance Aspects + cdk-nag", "cdk.IAspect", "Boundary, tags, encryption, compliance")
        Component(nb, "SecureDataApi", "L3 construct", "Encrypted bucket + private API, consumes PlatformConfig")
    }

    Rel(ds, stack, "PlatformStack(app, id, tags)")
    Rel(ds, nb, "SecureDataApi(stack, id)")
    Rel(stack, env, "resolve(self)")
    Rel(env, reg, "resolve(account_id)")
    Rel(reg, acct, "provides")
    Rel(env, cfg, "builds from PlatformAccount")
    Rel(stack, gov, "apply_platform_governance")
    Rel(nb, env, "of(self)")
    Rel(nb, cfg, "reads KMS / VPC endpoint")

    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")
```

---

## Known sharp edges (carry these honestly into the presentation)

- **Default-VPC PoC baseline** — the example registry is verified offline (8 tests green)
  and was deployed end-to-end into a `dev` account (private API + KMS bucket + boundary +
  tags confirmed on real infra). The baseline is wired to the account's **default VPC**;
  a real deployment uses dedicated private subnets. Account ids are read from environment
  variables (`PAVED_CDK_{DEV,PREPROD,PROD}_ACCOUNT_ID`), with placeholders as fallback.
- **The registry must stay in sync with reality** — baseline values now live in code, not
  live in SSM. If the LZ rotates a subnet/KMS, a PR must update the registry, and consumers
  pick it up only via `copier update` (pull, not automatic). Mitigation: generate the
  registry from AWS Organizations in CI + a freshness gate in the pipeline that flags stale
  pins.
- **VPC endpoints are a prerequisite** — a notebook with `internet=Disabled` is only usable
  with interface endpoints (`sagemaker.api/.runtime/.notebook`), an S3 gateway, and egress
  rules to the package source. Otherwise: creatable but no `pip`/`uv install`.
- **`copier update` not yet exercised** — the real USP over Cookiecutter is unproven until a
  v1→v2 merge is tested.
- **SageMaker notebook instances are effectively legacy** — fine as a wiring demo; SageMaker
  Studio would be the more realistic paved road.
```

