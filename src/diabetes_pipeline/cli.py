"""Command-line entry points for Block A audit and split generation."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from collections.abc import Iterable

from diabetes_pipeline.data.loaders import load_dataset
from diabetes_pipeline.data.manifests import write_audit
from diabetes_pipeline.settings import load_dataset_registry
from diabetes_pipeline.splitting.registry import create_and_write_split_manifest


MODEL_CHOICES = (
    "logistic_regression",
    "random_forest",
    "xgboost",
    "lightgbm",
    "catboost",
)


LOGGER = logging.getLogger(__name__)


def _dataset_names(requested: str) -> Iterable[str]:
    registry = load_dataset_registry()
    if requested == "all":
        return registry.keys()
    if requested not in registry:
        raise ValueError(f"Unknown dataset '{requested}'. Available: {sorted(registry)}")
    return [requested]


def command_audit(dataset_name: str) -> None:
    for name in _dataset_names(dataset_name):
        dataset = load_dataset(name)
        json_path, md_path, audit = write_audit(dataset)
        LOGGER.info(
            "Audit complete: %s rows=%d prevalence=%.4f -> %s",
            name,
            audit["retained_rows"],
            audit["positive_prevalence"],
            json_path,
        )
        LOGGER.info("Human-readable audit: %s", md_path)


def command_splits(dataset_name: str, seed: int) -> None:
    for name in _dataset_names(dataset_name):
        dataset = load_dataset(name)
        csv_path, metadata_path, manifest = create_and_write_split_manifest(
            dataset, seed=seed
        )
        LOGGER.info(
            "Split manifest complete: %s rows=%d -> %s",
            name,
            len(manifest),
            csv_path,
        )
        LOGGER.info("Split metadata: %s", metadata_path)


def command_block_a(dataset_name: str, seed: int) -> None:
    for name in _dataset_names(dataset_name):
        dataset = load_dataset(name)
        _, _, audit = write_audit(dataset)
        split_path, metadata_path, manifest = create_and_write_split_manifest(
            dataset, seed=seed
        )
        print(
            json.dumps(
                {
                    "dataset": name,
                    "rows": audit["retained_rows"],
                    "prevalence": audit["positive_prevalence"],
                    "manifest_rows": len(manifest),
                    "split_path": str(split_path),
                    "split_metadata": str(metadata_path),
                },
                sort_keys=True,
            )
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log-level", default="INFO")
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser("audit", help="Load, validate, and audit raw datasets")
    audit.add_argument("--dataset", default="all")

    splits = subparsers.add_parser("make-splits", help="Generate immutable split manifests")
    splits.add_argument("--dataset", default="all")
    splits.add_argument("--seed", type=int, default=42)

    block_a = subparsers.add_parser("block-a", help="Run audits and split generation")
    block_a.add_argument("--dataset", default="all")
    block_a.add_argument("--seed", type=int, default=42)

    research_audit = subparsers.add_parser(
        "research-audit",
        help="Audit missingness, grouping, survey design, and split leakage controls",
    )
    research_audit.add_argument("--seed", type=int, default=42)

    concealment = subparsers.add_parser(
        "test-concealment",
        help="Write and validate an outcome-blind development holdout manifest",
    )
    concealment.add_argument("--dataset", required=True, choices=("brfss", "hospital130"))
    concealment.add_argument("--seed", type=int, default=42)

    feature_map = subparsers.add_parser(
        "feature-map",
        help="Validate and write the complete cross-dataset feature dictionary",
    )

    benchmark = subparsers.add_parser(
        "benchmark", help="Run a nested-CV benchmark profile"
    )
    benchmark.add_argument("--dataset", required=True)
    benchmark.add_argument("--profile", default="smoke")
    benchmark.add_argument(
        "--models",
        nargs="+",
        default=list(MODEL_CHOICES),
        choices=list(MODEL_CHOICES),
    )

    holdout = subparsers.add_parser(
        "benchmark-holdout",
        help="Run a development-locked holdout benchmark",
    )
    holdout.add_argument("--dataset", required=True)
    holdout.add_argument("--profile", default="smoke")
    holdout.add_argument(
        "--models",
        nargs="+",
        default=list(MODEL_CHOICES),
        choices=list(MODEL_CHOICES),
    )

    survey_sensitivity = subparsers.add_parser(
        "brfss-survey-sensitivity",
        help="Evaluate a completed BRFSS holdout with survey weights and PSU uncertainty",
    )
    survey_sensitivity.add_argument("--study-dir", type=Path, required=True)
    survey_sensitivity.add_argument("--n-bootstrap", type=int, default=200)
    survey_sensitivity.add_argument("--seed", type=int, default=42)

    explain = subparsers.add_parser(
        "explain", help="Generate held-out SHAP explanations for a completed study"
    )
    explain.add_argument("--dataset", required=True)
    explain.add_argument("--study-dir", type=Path, required=True)
    explain.add_argument("--maximum-samples-per-fold", type=int, default=1_000)
    explain.add_argument("--background-size", type=int, default=100)
    explain.add_argument("--top-k", type=int, default=5)
    explain.add_argument("--seed", type=int, default=42)

    explain_holdout = subparsers.add_parser(
        "explain-holdout",
        help="Generate test-only SHAP explanations for a holdout study",
    )
    explain_holdout.add_argument("--dataset", required=True)
    explain_holdout.add_argument("--study-dir", type=Path, required=True)
    explain_holdout.add_argument("--maximum-samples-per-model", type=int, default=1_000)
    explain_holdout.add_argument("--background-size", type=int, default=100)
    explain_holdout.add_argument("--top-k", type=int, default=5)
    explain_holdout.add_argument("--seed", type=int, default=42)

    routing = subparsers.add_parser(
        "evaluate-routing",
        help="Evaluate development-only feature-availability model routing",
    )
    routing.add_argument("--dataset", required=True)
    routing.add_argument("--study-dir", type=Path, required=True)

    panel_contrasts = subparsers.add_parser(
        "matched-panel-contrasts",
        help="Compare reduced and full feature panels on identical participants",
    )
    panel_contrasts.add_argument("--study-dir", type=Path, required=True)
    panel_contrasts.add_argument("--n-bootstrap", type=int)
    panel_contrasts.add_argument("--seed", type=int)

    ablations = subparsers.add_parser(
        "artifact-ablations",
        help="Run paired ablations supported by completed prediction artifacts",
    )
    ablations.add_argument("--study-dir", type=Path, required=True)
    ablations.add_argument("--n-bootstrap", type=int)
    ablations.add_argument("--seed", type=int)

    patient_result = subparsers.add_parser(
        "patient-result",
        help="Generate a probability-first research report for one patient",
    )
    patient_result.add_argument("--dataset", required=True)
    patient_result.add_argument("--routing-dir", type=Path, required=True)
    patient_input = patient_result.add_mutually_exclusive_group(required=True)
    patient_input.add_argument(
        "--patient-json", help="A JSON object containing available patient features"
    )
    patient_input.add_argument(
        "--patient-file", type=Path, help="Path to a JSON object with patient features"
    )
    patient_result.add_argument("--scenario")
    patient_result.add_argument("--top-k", type=int, default=5)
    patient_result.add_argument(
        "--format", choices=("json", "markdown"), default="json"
    )
    patient_result.add_argument(
        "--allow-out-of-range",
        action="store_true",
        help="Warn instead of abstaining outside observed reference ranges",
    )
    patient_result.add_argument(
        "--output",
        type=Path,
        help="Optional JSON output path; patient data are not persisted by default",
    )

    mixed_result = subparsers.add_parser(
        "mixed-patient-result",
        help="Route one patient with dataset-namespaced attributes to one screening expert",
    )
    mixed_result.add_argument(
        "--routing-dir",
        action="append",
        required=True,
        metavar="DATASET=PATH",
        help="Repeat once per dataset router, for example pidd=outputs/.../availability_routing",
    )
    mixed_input = mixed_result.add_mutually_exclusive_group(required=True)
    mixed_input.add_argument(
        "--patient-json",
        help="JSON object keyed by dataset, then by feature name",
    )
    mixed_input.add_argument(
        "--patient-file",
        type=Path,
        help="Path to a JSON object keyed by dataset, then by feature name",
    )
    mixed_result.add_argument("--prefer-dataset")
    mixed_result.add_argument(
        "--allow-experimental-auto-selection",
        action="store_true",
        help=(
            "Permit the unvalidated cross-dataset heuristic for software "
            "demonstration only; never use its output as a paper or clinical result"
        ),
    )
    mixed_result.add_argument("--top-k", type=int, default=5)
    mixed_result.add_argument(
        "--format", choices=("json", "markdown"), default="json"
    )
    mixed_result.add_argument(
        "--allow-out-of-range",
        action="store_true",
        help="Warn instead of abstaining outside observed reference ranges",
    )
    mixed_result.add_argument(
        "--output",
        type=Path,
        help="Optional output path; patient data are not persisted by default",
    )

    readiness = subparsers.add_parser(
        "publication-readiness",
        help="Audit frozen studies and manuscript safeguards before submission",
    )
    readiness.add_argument(
        "--study-dir",
        action="append",
        required=True,
        type=Path,
        help="Repeat once for each primary dataset study",
    )
    readiness.add_argument(
        "--protocol",
        type=Path,
        default=Path("config/publication_protocol.yaml"),
    )
    readiness.add_argument(
        "--format", choices=("json", "markdown"), default="markdown"
    )
    readiness.add_argument("--output", type=Path)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    if args.command == "audit":
        command_audit(args.dataset)
    elif args.command == "make-splits":
        command_splits(args.dataset, args.seed)
    elif args.command == "block-a":
        command_block_a(args.dataset, args.seed)
    elif args.command == "research-audit":
        from diabetes_pipeline.data.research_audit import write_research_audit

        json_path, md_path, audit = write_research_audit(seed=args.seed)
        print(
            json.dumps(
                {
                    "evidence_tier": audit["evidence_tier"],
                    "final_outcome_access_authorized": audit[
                        "final_outcome_access_authorized"
                    ],
                    "json": str(json_path),
                    "markdown": str(md_path),
                },
                sort_keys=True,
            )
        )
    elif args.command == "test-concealment":
        from diabetes_pipeline.splitting.concealment import (
            write_development_concealment_test,
        )

        manifest_path, metadata_path, metadata = write_development_concealment_test(
            load_dataset(args.dataset), seed=args.seed
        )
        print(
            json.dumps(
                {
                    "dataset": args.dataset,
                    "purpose": metadata["purpose"],
                    "outcome_blind": metadata["outcome_blind"],
                    "manifest": str(manifest_path),
                    "metadata": str(metadata_path),
                    "manifest_sha256": metadata["manifest_sha256"],
                },
                sort_keys=True,
            )
        )
    elif args.command == "feature-map":
        from diabetes_pipeline.features import write_feature_ontology

        result = write_feature_ontology()
        print(
            json.dumps(
                {
                    "dictionary": str(result.dictionary_path),
                    "report": str(result.report_path),
                    "metadata": str(result.metadata_path),
                },
                sort_keys=True,
            )
        )
    elif args.command == "benchmark":
        from diabetes_pipeline.runner import run_nested_benchmark

        result = run_nested_benchmark(
            args.dataset, profile_name=args.profile, models=args.models
        )
        print(
            json.dumps(
                {
                    "experiment_id": result.experiment_id,
                    "output_dir": str(result.output_dir),
                    "summary": str(result.summary_path),
                },
                sort_keys=True,
            )
        )
    elif args.command == "benchmark-holdout":
        from diabetes_pipeline.holdout_runner import run_holdout_benchmark

        result = run_holdout_benchmark(
            args.dataset, profile_name=args.profile, models=args.models
        )
        print(
            json.dumps(
                {
                    "experiment_id": result.experiment_id,
                    "output_dir": str(result.output_dir),
                    "summary": str(result.summary_path),
                },
                sort_keys=True,
            )
        )
    elif args.command == "brfss-survey-sensitivity":
        from diabetes_pipeline.evaluation.survey_sensitivity import (
            run_brfss_survey_sensitivity,
        )

        result = run_brfss_survey_sensitivity(
            args.study_dir,
            n_bootstrap=args.n_bootstrap,
            seed=args.seed,
        )
        print(
            json.dumps(
                {
                    "study_dir": str(result.study_dir),
                    "output_dir": str(result.output_dir),
                    "metrics": str(result.metrics_path),
                    "intervals": str(result.intervals_path),
                    "report": str(result.report_path),
                },
                sort_keys=True,
            )
        )
    elif args.command == "explain":
        from diabetes_pipeline.explainability import run_study_explainability

        result = run_study_explainability(
            args.dataset,
            args.study_dir,
            maximum_samples_per_fold=args.maximum_samples_per_fold,
            background_size=args.background_size,
            top_k=args.top_k,
            seed=args.seed,
        )
        print(
            json.dumps(
                {
                    "study_dir": str(result.study_dir),
                    "output_dir": str(result.output_dir),
                    "global_importance": str(result.global_importance_path),
                    "stability": str(result.stability_path),
                },
                sort_keys=True,
            )
        )
    elif args.command == "explain-holdout":
        from diabetes_pipeline.explainability import run_holdout_explainability

        result = run_holdout_explainability(
            args.dataset,
            args.study_dir,
            maximum_samples_per_model=args.maximum_samples_per_model,
            background_size=args.background_size,
            top_k=args.top_k,
            seed=args.seed,
        )
        print(
            json.dumps(
                {
                    "study_dir": str(result.study_dir),
                    "output_dir": str(result.output_dir),
                    "global_importance": str(result.global_importance_path),
                },
                sort_keys=True,
            )
        )
    elif args.command == "evaluate-routing":
        from diabetes_pipeline.routing import run_availability_routing

        result = run_availability_routing(args.dataset, args.study_dir)
        print(
            json.dumps(
                {
                    "study_dir": str(result.study_dir),
                    "output_dir": str(result.output_dir),
                    "selections": str(result.selections_path),
                    "summary": str(result.summary_path),
                },
                sort_keys=True,
            )
        )
    elif args.command == "matched-panel-contrasts":
        from diabetes_pipeline.routing.panel_contrasts import (
            run_matched_panel_contrasts,
        )

        result = run_matched_panel_contrasts(
            args.study_dir,
            n_bootstrap=args.n_bootstrap,
            seed=args.seed,
        )
        print(
            json.dumps(
                {
                    "study_dir": str(result.study_dir),
                    "output_dir": str(result.output_dir),
                    "predictions": str(result.predictions_path),
                    "contrasts": str(result.contrasts_path),
                    "report": str(result.report_path),
                },
                sort_keys=True,
            )
        )
    elif args.command == "artifact-ablations":
        from diabetes_pipeline.evaluation.ablations import (
            run_artifact_ablation_suite,
        )

        result = run_artifact_ablation_suite(
            args.study_dir,
            n_bootstrap=args.n_bootstrap,
            seed=args.seed,
        )
        print(
            json.dumps(
                {
                    "study_dir": str(result.study_dir),
                    "output_dir": str(result.output_dir),
                    "inventory": str(result.inventory_path),
                    "report": str(result.report_path),
                },
                sort_keys=True,
            )
        )
    elif args.command == "patient-result":
        import pandas as pd

        from diabetes_pipeline.reporting import (
            generate_patient_result,
            render_patient_result_markdown,
        )

        payload_text = (
            args.patient_json
            if args.patient_json is not None
            else args.patient_file.read_text(encoding="utf-8")
        )
        patient_payload = json.loads(payload_text)
        if not isinstance(patient_payload, dict):
            parser.error("Patient input must be one JSON object")
        routing_dir = args.routing_dir.resolve()
        bundle_paths = sorted((routing_dir / "router_bundles").glob("*.joblib"))
        if not bundle_paths:
            parser.error(f"No router bundles found under {routing_dir}")
        reference = load_dataset(args.dataset)
        result = generate_patient_result(
            bundle_paths,
            pd.DataFrame([patient_payload]),
            reference,
            scenario_name=args.scenario,
            top_k=args.top_k,
            abstain_outside_reference=not args.allow_out_of_range,
        )
        rendered = (
            json.dumps(result, indent=2, sort_keys=True, allow_nan=False)
            if args.format == "json"
            else render_patient_result_markdown(result)
        )
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered.rstrip() + "\n", encoding="utf-8")
        print(rendered.rstrip())
    elif args.command == "mixed-patient-result":
        from diabetes_pipeline.reporting import (
            generate_mixed_patient_result,
            render_mixed_patient_result_markdown,
        )

        payload_text = (
            args.patient_json
            if args.patient_json is not None
            else args.patient_file.read_text(encoding="utf-8")
        )
        patient_payload = json.loads(payload_text)
        if not isinstance(patient_payload, dict) or not all(
            isinstance(value, dict) for value in patient_payload.values()
        ):
            parser.error(
                "Mixed patient input must be an object keyed by dataset, with "
                "one feature object per dataset"
            )
        routing_directories: dict[str, Path] = {}
        for definition in args.routing_dir:
            if "=" not in definition:
                parser.error("--routing-dir values must use DATASET=PATH")
            dataset_name, raw_path = definition.split("=", 1)
            dataset_name = dataset_name.strip()
            if not dataset_name or dataset_name in routing_directories:
                parser.error(f"Duplicate or empty routing dataset: {dataset_name!r}")
            routing_directories[dataset_name] = Path(raw_path).expanduser().resolve()
        bundle_registry: dict[str, list[Path]] = {}
        references = {}
        for dataset_name, routing_dir in routing_directories.items():
            bundle_paths = sorted((routing_dir / "router_bundles").glob("*.joblib"))
            if not bundle_paths:
                parser.error(f"No router bundles found for {dataset_name} under {routing_dir}")
            bundle_registry[dataset_name] = bundle_paths
            references[dataset_name] = load_dataset(dataset_name)
        result = generate_mixed_patient_result(
            bundle_registry,
            patient_payload,
            references,
            preferred_dataset=args.prefer_dataset,
            allow_experimental_auto_selection=args.allow_experimental_auto_selection,
            top_k=args.top_k,
            abstain_outside_reference=not args.allow_out_of_range,
        )
        rendered = (
            json.dumps(result, indent=2, sort_keys=True, allow_nan=False)
            if args.format == "json"
            else render_mixed_patient_result_markdown(result)
        )
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered.rstrip() + "\n", encoding="utf-8")
        print(rendered.rstrip())
    elif args.command == "publication-readiness":
        from diabetes_pipeline.reporting import (
            audit_publication_readiness,
            render_publication_readiness_markdown,
        )

        result = audit_publication_readiness(
            args.study_dir,
            protocol_path=args.protocol,
        )
        rendered = (
            json.dumps(result, indent=2, sort_keys=True, allow_nan=False)
            if args.format == "json"
            else render_publication_readiness_markdown(result)
        )
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered.rstrip() + "\n", encoding="utf-8")
        print(rendered.rstrip())
    else:
        parser.error(f"Unknown command {args.command}")


if __name__ == "__main__":
    main()
