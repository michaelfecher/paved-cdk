# Consumption models — decision aid (choose with your customers)

All variants run on the **same Paved CDK kernel**: deterministic per-stage config from
the in-code registry (VPC/subnet/KMS/boundary, Databricks via Secrets-Manager reference),
governance (boundary/KMS/tags/cdk-nag), the event-driven pipeline (PR preview → dev,
release tag → preprod → prod), versioned-dependency distribution, and **CDK only in CI**.
The variants differ **only at the consumer authoring surface**.

This is intentionally a set of **1–3 options to pick from** — not a single mandated path.

## Decision matrix

| Kriterium | **SDK (Decorators)** | **Copier / explicit** | **Declarative (YAML)** |
|---|---|---|---|
| Consumer schreibt | nur Handler + `@api/@scheduled` | `app.py` (Bricks/`ServiceSpec`) + Handler | `service.yaml` + Handler |
| **Deklarativer Code (YAML/JSON)?** | **nein** | **nein** | **ja** |
| **Eine Sprache (nur Python)?** | **ja** | **ja** | nein |
| Consumer muss CDK können? | nein | etwas | nein |
| Consumer-IaC-Aufwand (Ziel: minimal) | **am wenigsten** | mittel | wenig |
| Flexibilität / Edge-Cases | SDK-Vokabular (+ Escape nötig) | **maximal** (rohes CDK möglich) | Schema-Grenze (kein Escape) |
| Anzahl-Varianz (3 vs 5 Lambdas) | trivial | trivial | trivial |
| Typ-Varianz (Notebook/ECS/Glue …) | nur was das SDK anbietet | **alles** (Katalog + rohes CDK) | nur was das Schema kennt |
| Bootstrap = 1× Plattform-PR | ✔ | ✔ | ✔ |
| Updates = nur Pin-Bump, kein Überschreiben | ✔ | ✔ (+`_skip_if_exists`) | ✔ |
| Per-Stage-Config vorkonfiguriert | ✔ (Kern) | ✔ (Kern) | ✔ (Kern) |

## Auf die Leitziele gemünzt
- **„So wenig wie möglich deklarativ / alles Python":** schließt **YAML-Variante** faktisch aus; **SDK** und **Copier/explizit** sind beide Python-only.
- **„Einfachste für den Data Scientist":** **SDK** — der DS schreibt praktisch nur seinen Compute-Code.
- **„Mehrere Consumer, versch. Anforderungen":** Anzahl-Varianz lösen alle trivial; **Typ-Varianz** ist durch **Katalog-/SDK-Umfang** begrenzt — Copier hat als einziges einen Escape-Hatch (rohes CDK).
- **„Kein händisches Kopieren / automatisierbar":** in allen Varianten ist die Plattform eine **versionierte Dependency**; Onboarding = **ein** Plattform-PR; Updates = Pin-Bump. Runtime-Code wird nie überschrieben.

## Übliches Zielbild
**SDK als Default** (einfachste DS-Erfahrung, Python-only) **+ Copier/explizit als Escape-Hatch** für Teams mit echten Sonderfällen. Die **YAML-Variante** nur, wenn bewusst ein sprach-agnostisches, auditierbares Manifest gewünscht ist (widerspricht „kein YAML").

→ Die Auswahl trefft **du + deine Kunden**; alle drei sind hier lauffähig und liefern dasselbe governte Ergebnis (siehe Parität in [`README.md`](README.md)).
