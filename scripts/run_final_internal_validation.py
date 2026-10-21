#!/usr/bin/env python3
"""Run one frozen final internal-validation study and its prespecified analyses."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from diabetes_pipeline.evaluation.selective_prediction import (
    run_selective_prediction_analysis,
)
from diabetes_pipeline.evaluation.subgroup_analysis import run_subgroup_analysis


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset", required=True, choices=("pidd", "sylhet", "brfss", "hospital130")
    )
    parser.add_argument(
        "--study-dir",
        type=Path,
        help="Resume prespecified dependent analyses without rerunning the benchmark",
    )
    args = parser.parse_args()

    models = (
        "logistic_regression",
        "random_forest",
        "xgboost",
        "lightgbm",
        "catboost",
    )
    if args.study_dir is None:
        if args.dataset in {"pidd", "sylhet"}:
            from diabetes_pipeline.runner import run_nested_benchmark

            benchmark = run_nested_benchmark(
                args.dataset,
                profile_name="final_internal_validation",
                models=models,
            )
        else:
            from diabetes_pipeline.holdout_runner import run_holdout_benchmark

            benchmark = run_holdout_benchmark(
                args.dataset,
                profile_name="final_internal_validation",
                models=models,
            )
        study_dir = benchmark.output_dir
    else:
        study_dir = args.study_dir.resolve()

    from diabetes_pipeline.routing import (
        evaluate_runtime_policy,
        run_availability_routing,
    )

    routing = run_availability_routing(args.dataset, study_dir)
    policy = evaluate_runtime_policy(study_dir)
    selective = run_selective_prediction_analysis(study_dir)
    subgroup = run_subgroup_analysis(
        study_dir,
        system="availability_router",
        scenarios=("runtime_fallback_policy",),
    )
    if args.dataset in {"pidd", "sylhet"}:
        from diabetes_pipeline.explainability import run_study_explainability

        explanation = run_study_explainability(
            args.dataset,
            study_dir,
            maximum_samples_per_fold=1000,
            background_size=100,
            top_k=5,
            seed=42,
        )
    else:
        from diabetes_pipeline.explainability import run_holdout_explainability

        explanation = run_holdout_explainability(
            args.dataset,
            study_dir,
            maximum_samples_per_model=1000,
            background_size=100,
            top_k=5,
            seed=42,
        )
    survey = None
    if args.dataset == "brfss":
        from diabetes_pipeline.evaluation.survey_sensitivity import (
            run_brfss_survey_sensitivity,
        )

        survey = run_brfss_survey_sensitivity(
            study_dir,
            n_bootstrap=2000,
            seed=42,
        )
    print(
        json.dumps(
            {
                "dataset": args.dataset,
                "study_dir": str(study_dir),
                "routing": str(routing.output_dir),
                "runtime_policy": str(policy.output_dir),
                "selective_prediction": str(selective.output_dir),
                "subgroup_analysis": str(subgroup.output_dir),
                "explainability": str(explanation.output_dir),
                "survey_sensitivity": str(survey.output_dir) if survey else None,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
