#!/usr/bin/env python3
"""
DevOps verifier for Learn to Cloud style capstone projects.

What it checks:
- Docker setup (Dockerfile, .dockerignore, best-practice hints)
- CI/CD setup (GitHub Actions workflows and common pipeline signals)
- Testing and quality signals (tests, lint/format config)
- IaC signals (Terraform, Bicep, CloudFormation)
- Documentation signals (README, architecture docs)

Usage:
  python devops-verification.py
  python devops-verification.py --path .
  python devops-verification.py --json
"""

from __future__ import annotations

import argparse
import json
import re
from fnmatch import fnmatch
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


IGNORE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    ".terraform",
    ".idea",
    ".vscode",
    "__pycache__",
    "dist",
    "build",
}


@dataclass
class CheckResult:
    category: str
    name: str
    passed: bool
    severity: str  # info | warning | critical
    details: str


@dataclass
class Report:
    root: str
    score: float
    passed: int
    failed: int
    checks: list[CheckResult]


def safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def iter_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*"):
        if any(part in IGNORE_DIRS for part in p.parts):
            continue
        if p.is_file():
            yield p


def find_files(root: Path, names: Iterable[str]) -> list[Path]:
    wanted = {n.lower() for n in names}
    found: list[Path] = []
    for p in iter_files(root):
        if p.name.lower() in wanted:
            found.append(p)
    return found


def has_any_file(root: Path, patterns: Iterable[str]) -> bool:
    for p in iter_files(root):
        rel = str(p.relative_to(root)).replace("\\", "/")
        for pattern in patterns:
            if fnmatch(rel, pattern) or fnmatch(p.name, pattern):
                return True
    return False


def find_text_in_files(root: Path, patterns: Iterable[str], file_globs: Iterable[str]) -> bool:
    file_patterns = list(file_globs)
    for p in iter_files(root):
        rel = str(p.relative_to(root)).replace("\\", "/")
        if not any(fnmatch(rel, g) or fnmatch(p.name, g) for g in file_patterns):
            continue
        content = safe_read(p).lower()
        if any(pattern.lower() in content for pattern in patterns):
            return True
    return False


def check_docker(root: Path) -> list[CheckResult]:
    results: list[CheckResult] = []

    dockerfiles = [p for p in iter_files(root) if p.name.lower() == "dockerfile"]
    results.append(
        CheckResult(
            category="Docker",
            name="Dockerfile exists",
            passed=bool(dockerfiles),
            severity="critical",
            details="Found Dockerfile(s)." if dockerfiles else "No Dockerfile found.",
        )
    )

    dockerignore = find_files(root, [".dockerignore"])
    results.append(
        CheckResult(
            category="Docker",
            name=".dockerignore exists",
            passed=bool(dockerignore),
            severity="warning",
            details="Found .dockerignore." if dockerignore else "Missing .dockerignore (recommended).",
        )
    )

    if dockerfiles:
        for df in dockerfiles:
            content = safe_read(df)
            rel = str(df.relative_to(root))

            from_match = re.search(r"^\s*FROM\s+(.+)$", content, re.MULTILINE | re.IGNORECASE)
            results.append(
                CheckResult(
                    category="Docker",
                    name=f"{rel}: has FROM",
                    passed=bool(from_match),
                    severity="critical",
                    details="Base image is specified." if from_match else "Missing FROM instruction.",
                )
            )

            latest_tag = False
            if from_match:
                image = from_match.group(1)
                latest_tag = ":latest" in image.lower() or image.strip().endswith(":")
            results.append(
                CheckResult(
                    category="Docker",
                    name=f"{rel}: avoids latest tag",
                    passed=not latest_tag,
                    severity="warning",
                    details="Pinned image tag detected." if not latest_tag else "Image uses latest tag (pin versions).",
                )
            )

            has_user = re.search(r"^\s*USER\s+.+$", content, re.MULTILINE | re.IGNORECASE) is not None
            results.append(
                CheckResult(
                    category="Docker",
                    name=f"{rel}: non-root USER set",
                    passed=has_user,
                    severity="warning",
                    details="USER instruction found." if has_user else "No USER instruction found (runs as root by default).",
                )
            )

            has_healthcheck = (
                re.search(r"^\s*HEALTHCHECK\b", content, re.MULTILINE | re.IGNORECASE) is not None
            )
            results.append(
                CheckResult(
                    category="Docker",
                    name=f"{rel}: HEALTHCHECK present",
                    passed=has_healthcheck,
                    severity="info",
                    details="HEALTHCHECK found." if has_healthcheck else "No HEALTHCHECK found.",
                )
            )

    compose_exists = has_any_file(root, ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"])
    results.append(
        CheckResult(
            category="Docker",
            name="Compose file exists",
            passed=compose_exists,
            severity="info",
            details="Found Docker Compose file." if compose_exists else "No Compose file found (optional).",
        )
    )

    return results


def check_cicd(root: Path) -> list[CheckResult]:
    results: list[CheckResult] = []

    workflows_dir = root / ".github" / "workflows"
    workflow_files = []
    if workflows_dir.exists() and workflows_dir.is_dir():
        workflow_files = [p for p in workflows_dir.iterdir() if p.suffix.lower() in {".yml", ".yaml"}]

    results.append(
        CheckResult(
            category="CI/CD",
            name="GitHub Actions workflows exist",
            passed=bool(workflow_files),
            severity="critical",
            details="Workflow files found." if workflow_files else "No workflow files in .github/workflows.",
        )
    )

    combined = "\n".join(safe_read(p) for p in workflow_files)
    lower = combined.lower()

    trigger_ok = any(k in lower for k in ["pull_request", "push", "workflow_dispatch"])
    results.append(
        CheckResult(
            category="CI/CD",
            name="Pipeline has triggers",
            passed=trigger_ok,
            severity="critical",
            details="Found common triggers." if trigger_ok else "No common CI triggers found.",
        )
    )

    checkout_ok = "actions/checkout" in lower
    results.append(
        CheckResult(
            category="CI/CD",
            name="Pipeline checks out code",
            passed=checkout_ok,
            severity="warning",
            details="actions/checkout found." if checkout_ok else "No checkout step found.",
        )
    )

    test_ok = any(
        key in lower
        for key in [
            "pytest",
            "npm test",
            "go test",
            "dotnet test",
            "mvn test",
            "gradle test",
            "unittest",
        ]
    )
    results.append(
        CheckResult(
            category="CI/CD",
            name="Pipeline runs tests",
            passed=test_ok,
            severity="critical",
            details="Test command detected." if test_ok else "No obvious test step detected.",
        )
    )

    build_ok = any(key in lower for key in ["docker build", "buildx", "build and push", "publish", "package"])
    results.append(
        CheckResult(
            category="CI/CD",
            name="Pipeline has build/package step",
            passed=build_ok,
            severity="warning",
            details="Build/package keywords found." if build_ok else "No clear build/package step detected.",
        )
    )

    security_ok = any(key in lower for key in ["codeql", "trivy", "snyk", "bandit", "gitleaks", "dependency-review-action"])
    results.append(
        CheckResult(
            category="CI/CD",
            name="Pipeline has security scanning",
            passed=security_ok,
            severity="info",
            details="Security scan keyword found." if security_ok else "No security scan detected.",
        )
    )

    registry_ok = any(
        key in lower
        for key in [
            "docker/login-action",
            "docker/build-push-action",
            "docker push",
            "buildx",
            "ecr",
            "gcr.io",
            "ghcr.io",
            "acr",
        ]
    )
    results.append(
        CheckResult(
            category="CI/CD",
            name="Pipeline pushes image to registry",
            passed=registry_ok,
            severity="critical",
            details="Registry push/login step detected." if registry_ok else "No registry push/login detected.",
        )
    )

    deploy_ok = any(
        key in lower
        for key in [
            "kubectl apply",
            "kubectl rollout",
            "helm upgrade",
            "helm install",
            "terraform apply",
            "pulumi up",
            "ecs deploy",
            "azure/webapps-deploy",
            "gcloud run deploy",
        ]
    )
    results.append(
        CheckResult(
            category="CI/CD",
            name="Pipeline deploys application",
            passed=deploy_ok,
            severity="critical",
            details="Deploy step detected." if deploy_ok else "No deploy step detected.",
        )
    )

    return results


def check_quality_and_tests(root: Path) -> list[CheckResult]:
    results: list[CheckResult] = []

    test_patterns = [
        "tests",
        "test",
        "*_test.py",
        "test_*.py",
        "*.spec.js",
        "*.test.js",
        "*.spec.ts",
        "*.test.ts",
    ]

    has_tests = (root / "tests").exists() or (root / "test").exists() or any(root.rglob(p) for p in test_patterns[2:])

    results.append(
        CheckResult(
            category="Quality",
            name="Automated tests present",
            passed=has_tests,
            severity="critical",
            details="Found test files/directories." if has_tests else "No test files/directories detected.",
        )
    )

    lint_config_names = [
        ".flake8",
        "pyproject.toml",
        "ruff.toml",
        ".eslintrc",
        ".eslintrc.js",
        ".eslintrc.json",
        "eslint.config.js",
        "pylintrc",
    ]
    has_lint = bool(find_files(root, lint_config_names))

    results.append(
        CheckResult(
            category="Quality",
            name="Lint/format config present",
            passed=has_lint,
            severity="warning",
            details="Lint/format config found." if has_lint else "No lint/format config detected.",
        )
    )

    return results


def check_iac(root: Path) -> list[CheckResult]:
    results: list[CheckResult] = []

    terraform = list(root.rglob("*.tf"))
    bicep = list(root.rglob("*.bicep"))
    cfn = list(root.rglob("template.yaml")) + list(root.rglob("template.yml"))

    has_iac = bool(terraform or bicep or cfn)
    details = []
    if terraform:
        details.append(f"Terraform: {len(terraform)} file(s)")
    if bicep:
        details.append(f"Bicep: {len(bicep)} file(s)")
    if cfn:
        details.append(f"CloudFormation-like templates: {len(cfn)} file(s)")

    results.append(
        CheckResult(
            category="IaC",
            name="Infrastructure as Code present",
            passed=has_iac,
            severity="warning",
            details="; ".join(details) if details else "No IaC files detected.",
        )
    )

    iac_text = ""
    for p in terraform + bicep + cfn:
        iac_text += "\n" + safe_read(p).lower()

    compute_ok = any(key in iac_text for key in ["ecs", "eks", "container", "app_service", "cloud run", "kubernetes"])
    network_ok = any(key in iac_text for key in ["vpc", "subnet", "security_group", "network", "route"])
    db_ok = any(key in iac_text for key in ["postgres", "rds", "sql", "db_instance", "database"])

    results.append(
        CheckResult(
            category="IaC",
            name="IaC defines compute resources",
            passed=compute_ok,
            severity="warning",
            details="Compute keywords detected." if compute_ok else "No obvious compute resources detected.",
        )
    )

    results.append(
        CheckResult(
            category="IaC",
            name="IaC defines networking resources",
            passed=network_ok,
            severity="warning",
            details="Networking keywords detected." if network_ok else "No obvious networking resources detected.",
        )
    )

    results.append(
        CheckResult(
            category="IaC",
            name="IaC defines database resources",
            passed=db_ok,
            severity="warning",
            details="Database keywords detected." if db_ok else "No obvious database resources detected.",
        )
    )

    return results


def check_kubernetes(root: Path) -> list[CheckResult]:
    results: list[CheckResult] = []

    k8s_dirs = {"k8s", "kubernetes", "manifests", "deploy", "deployment", "helm"}
    yaml_files: list[Path] = []
    for p in iter_files(root):
        if p.suffix.lower() not in {".yml", ".yaml"}:
            continue
        parts = {part.lower() for part in p.parts}
        if parts.intersection(k8s_dirs) or "k8s" in p.name.lower():
            yaml_files.append(p)

    results.append(
        CheckResult(
            category="Kubernetes",
            name="Kubernetes manifests present",
            passed=bool(yaml_files),
            severity="critical",
            details="K8s YAML files found." if yaml_files else "No Kubernetes YAML files detected.",
        )
    )

    kinds: set[str] = set()
    secrets_text = ""
    service_text = ""
    for p in yaml_files:
        content = safe_read(p)
        for match in re.finditer(r"^\s*kind:\s*([A-Za-z0-9]+)\s*$", content, re.MULTILINE):
            kinds.add(match.group(1).lower())
        if "secret" in content.lower():
            secrets_text += "\n" + content.lower()
        if "service" in content.lower():
            service_text += "\n" + content.lower()

    required_kinds = {"deployment", "service", "configmap", "secret"}
    for kind in sorted(required_kinds):
        results.append(
            CheckResult(
                category="Kubernetes",
                name=f"Kubernetes {kind.title()} manifest",
                passed=kind in kinds,
                severity="critical" if kind in {"deployment", "service"} else "warning",
                details=f"Found {kind} manifest." if kind in kinds else f"Missing {kind} manifest.",
            )
        )

    service_type_ok = any(t in service_text for t in ["type: loadbalancer", "type: nodeport"])
    results.append(
        CheckResult(
            category="Kubernetes",
            name="Service exposes app (NodePort/LoadBalancer)",
            passed=service_type_ok,
            severity="warning",
            details="Service type exposes app." if service_type_ok else "No NodePort/LoadBalancer detected.",
        )
    )

    llm_keys = ["openai_api_key", "anthropic_api_key", "llm_api_key", "azure_openai_api_key", "gemini_api_key"]
    secret_env_ok = any(k in secrets_text for k in llm_keys) or "secretkeyref" in secrets_text
    results.append(
        CheckResult(
            category="Kubernetes",
            name="LLM API key stored in Secret",
            passed=secret_env_ok,
            severity="critical",
            details="Secret references LLM key." if secret_env_ok else "No LLM key found in Secret manifest.",
        )
    )

    helm_ok = has_any_file(root, ["Chart.yaml", "charts/*/Chart.yaml"])
    results.append(
        CheckResult(
            category="Kubernetes",
            name="Helm chart present (optional)",
            passed=helm_ok,
            severity="info",
            details="Helm chart found." if helm_ok else "No Helm chart found.",
        )
    )

    return results


def check_observability(root: Path) -> list[CheckResult]:
    results: list[CheckResult] = []

    prometheus_ok = has_any_file(
        root,
        [
            "prometheus.yml",
            "prometheus.yaml",
            "k8s/prometheus*.yml",
            "k8s/prometheus*.yaml",
            "manifests/prometheus*.yml",
            "manifests/prometheus*.yaml",
        ],
    )
    results.append(
        CheckResult(
            category="Observability",
            name="Prometheus config/manifests present",
            passed=prometheus_ok,
            severity="warning",
            details="Prometheus config/manifests found." if prometheus_ok else "No Prometheus config/manifests detected.",
        )
    )

    grafana_ok = has_any_file(
        root,
        [
            "grafana/*.json",
            "dashboards/*.json",
            "grafana/dashboards/*.json",
        ],
    )
    results.append(
        CheckResult(
            category="Observability",
            name="Grafana dashboard present",
            passed=grafana_ok,
            severity="warning",
            details="Grafana dashboard(s) found." if grafana_ok else "No Grafana dashboard JSON detected.",
        )
    )

    prom_client_ok = find_text_in_files(
        root,
        ["prometheus_client", "prometheus-client"],
        ["pyproject.toml", "requirements*.txt", "poetry.lock", "Pipfile", "Pipfile.lock"],
    )
    results.append(
        CheckResult(
            category="Observability",
            name="App dependencies include prometheus_client",
            passed=prom_client_ok,
            severity="warning",
            details="prometheus_client dependency detected." if prom_client_ok else "No prometheus_client dependency detected.",
        )
    )

    metrics_endpoint_ok = find_text_in_files(root, ["/metrics"], ["**/*.py"])
    results.append(
        CheckResult(
            category="Observability",
            name="Metrics endpoint exposed",
            passed=metrics_endpoint_ok,
            severity="warning",
            details="Metrics endpoint found." if metrics_endpoint_ok else "No /metrics endpoint detected.",
        )
    )

    llm_metrics_ok = find_text_in_files(root, ["llm", "token", "latency"], ["**/*.py"])
    results.append(
        CheckResult(
            category="Observability",
            name="LLM metrics instrumentation",
            passed=llm_metrics_ok,
            severity="info",
            details="LLM metric keywords detected." if llm_metrics_ok else "No LLM-specific metrics detected.",
        )
    )

    return results


def check_docs(root: Path) -> list[CheckResult]:
    results: list[CheckResult] = []

    readme = find_files(root, ["readme.md", "readme"])
    architecture_doc = has_any_file(
        root,
        [
            "docs/architecture.md",
            "docs/adr/*.md",
            "ARCHITECTURE.md",
            "architecture.md",
        ],
    )

    results.append(
        CheckResult(
            category="Docs",
            name="README present",
            passed=bool(readme),
            severity="critical",
            details="README found." if readme else "Missing README.",
        )
    )

    readme_ok = False
    readme_text = ""
    if readme:
        readme_text = safe_read(readme[0]).lower()
        required_terms = ["ci/cd", "kubernetes", "monitoring", "deployment", "grafana", "prometheus"]
        readme_ok = all(term in readme_text for term in required_terms)
    results.append(
        CheckResult(
            category="Docs",
            name="README covers CI/CD, K8s, Monitoring",
            passed=readme_ok,
            severity="warning",
            details="README references required topics." if readme_ok else "README missing required topics.",
        )
    )

    screenshots_ok = bool(re.search(r"!\[[^\]]*\]\([^)]+\.(png|jpg|jpeg|gif)\)", readme_text))
    results.append(
        CheckResult(
            category="Docs",
            name="Screenshots/diagrams referenced",
            passed=screenshots_ok,
            severity="info",
            details="README references images." if screenshots_ok else "No images referenced in README.",
        )
    )

    results.append(
        CheckResult(
            category="Docs",
            name="Architecture documentation present",
            passed=architecture_doc,
            severity="info",
            details="Architecture docs found." if architecture_doc else "No architecture docs detected.",
        )
    )

    return results


def compute_score(checks: list[CheckResult]) -> float:
    weights = {"critical": 3.0, "warning": 2.0, "info": 1.0}
    total = sum(weights[c.severity] for c in checks)
    got = sum(weights[c.severity] for c in checks if c.passed)
    return round((got / total) * 100, 2) if total else 0.0


def run_all_checks(root: Path) -> Report:
    checks: list[CheckResult] = []
    checks.extend(check_docker(root))
    checks.extend(check_cicd(root))
    checks.extend(check_quality_and_tests(root))
    checks.extend(check_iac(root))
    checks.extend(check_kubernetes(root))
    checks.extend(check_observability(root))
    checks.extend(check_docs(root))

    passed = sum(1 for c in checks if c.passed)
    failed = len(checks) - passed
    return Report(root=str(root), score=compute_score(checks), passed=passed, failed=failed, checks=checks)


def print_human(report: Report) -> None:
    print("=" * 72)
    print("DevOps Verification Report")
    print("=" * 72)
    print(f"Project: {report.root}")
    print(f"Score:   {report.score}%")
    print(f"Passed:  {report.passed}")
    print(f"Failed:  {report.failed}")
    print("-" * 72)

    grouped: dict[str, list[CheckResult]] = {}
    for c in report.checks:
        grouped.setdefault(c.category, []).append(c)

    for category, items in grouped.items():
        print(f"\n[{category}]")
        for c in items:
            mark = "✅" if c.passed else "❌"
            print(f"  {mark} {c.name} ({c.severity})")
            print(f"     {c.details}")

    print("\nRecommendations:")
    for c in report.checks:
        if not c.passed and c.severity in {"critical", "warning"}:
            print(f"  - {c.name}: {c.details}")


def to_json(report: Report) -> str:
    payload = {
        "root": report.root,
        "score": report.score,
        "passed": report.passed,
        "failed": report.failed,
        "checks": [asdict(c) for c in report.checks],
    }
    return json.dumps(payload, indent=2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify DevOps principles in a project repo.")
    parser.add_argument("--path", default=".", help="Path to repository root (default: current directory)")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    parser.add_argument("--fail-on-critical", action="store_true", help="Exit with code 1 if any critical check fails")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.path).resolve()

    if not root.exists() or not root.is_dir():
        print(f"Invalid path: {root}")
        return 2

    report = run_all_checks(root)

    if args.json:
        print(to_json(report))
    else:
        print_human(report)

    if args.fail_on_critical and any((not c.passed and c.severity == "critical") for c in report.checks):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())