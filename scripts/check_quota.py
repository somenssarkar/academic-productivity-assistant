#!/usr/bin/env python
"""
EduFlow — Vertex AI Quota Usage Checker
========================================
Auto-discovers correct metric names then fetches usage + limits.

Usage (run from project root):
    python scripts/check_quota.py
"""

import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv

load_dotenv("eduflow_agents/.env")

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "genai-apac-hackathon-491601")
LOCATION   = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
DIVIDER    = "-" * 72


# ── Auth ──────────────────────────────────────────────────────────────────────

def _get_token() -> str:
    import google.auth
    import google.auth.transport.requests
    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


def _get(url: str, token: str) -> dict:
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {token}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        return {"_error": f"HTTP {e.code}: {body}"}
    except Exception as e:
        return {"_error": str(e)}


def _run(cmd: str) -> str:
    """Run a shell command (shell=True for Windows gcloud.cmd support)."""
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    return (r.stdout or r.stderr or "").strip()


# ── Step 1: Discover available aiplatform metric names ────────────────────────

def discover_metrics(token: str) -> list[str]:
    """
    Lists all metric descriptors under aiplatform.googleapis.com
    and returns those mentioning 'generate_content' or 'token'.
    """
    url = (
        f"https://monitoring.googleapis.com/v3/projects/{PROJECT_ID}"
        f"/metricDescriptors"
        f"?filter={urllib.parse.quote('metric.type=starts_with(\"aiplatform.googleapis.com\")')}"
        f"&pageSize=200"
    )
    data = _get(url, token)
    if "_error" in data:
        return []
    found = []
    for d in data.get("metricDescriptors", []):
        t = d.get("type", "")
        if any(k in t for k in ["generate_content", "token", "request"]):
            found.append(t)
    return sorted(found)


# ── Step 2: Fetch usage timeseries for discovered metrics ─────────────────────

def fetch_usage(token: str, metric_type: str, minutes: int = 60) -> dict[str, float]:
    """Returns {model: total_value} for a metric over last `minutes` minutes."""
    now   = datetime.now(timezone.utc)
    start = now - timedelta(minutes=minutes)

    filter_str = f'metric.type="{metric_type}"'
    if LOCATION:
        filter_str += f' AND resource.labels.location="{LOCATION}"'

    url = (
        f"https://monitoring.googleapis.com/v3"
        f"/projects/{PROJECT_ID}/timeSeries"
        f"?{urllib.parse.urlencode({'filter': filter_str})}"
        f"&interval.startTime={start.strftime('%Y-%m-%dT%H:%M:%SZ')}"
        f"&interval.endTime={now.strftime('%Y-%m-%dT%H:%M:%SZ')}"
        f"&aggregation.alignmentPeriod=3600s"
        f"&aggregation.perSeriesAligner=ALIGN_SUM"
    )
    data = _get(url, token)
    if "_error" in data:
        return {"_error": data["_error"]}

    results = {}
    for series in data.get("timeSeries", []):
        labels = series.get("metric", {}).get("labels", {})
        model  = labels.get("base_model") or labels.get("model") or "unknown"
        points = series.get("points", [])
        total  = sum(
            float(p.get("value", {}).get("int64Value", 0) or
                  p.get("value", {}).get("doubleValue", 0))
            for p in points
        )
        results[model] = results.get(model, 0) + total
    return results


# ── Step 3: Quota limits via gcloud ──────────────────────────────────────────

def fetch_limits_gcloud() -> str:
    """Try multiple gcloud approaches to get quota limits."""
    attempts = [
        # approach 1 — services quota list (GA command)
        (
            "gcloud services quota list "
            f"--service=aiplatform.googleapis.com "
            f"--project={PROJECT_ID} "
            "--format=\"table(metric,quotas.limit)\" "
            "--filter=\"metric~generate_content\""
        ),
        # approach 2 — alpha variant
        (
            "gcloud alpha services quota list "
            f"--service=aiplatform.googleapis.com "
            f"--project={PROJECT_ID} "
            "--format=\"table(metric,quotas.limit)\" "
            "--filter=\"metric~generate_content\""
        ),
        # approach 3 — compute quotas fallback
        (
            f"gcloud compute project-info describe "
            f"--project={PROJECT_ID} "
            "--format=\"table(quotas.metric,quotas.limit,quotas.usage)\""
        ),
    ]
    for cmd in attempts:
        out = _run(cmd)
        if out and "ERROR" not in out[:20] and len(out) > 20:
            return out
    return "  gcloud quota commands returned no data for this project/service."


# ── Step 4: Direct Vertex AI quota check via REST ────────────────────────────

def fetch_limits_rest(token: str) -> list[dict]:
    """
    Queries the Service Usage v1beta1 API for aiplatform quota metrics.
    Returns parsed rows.
    """
    url = (
        f"https://serviceusage.googleapis.com/v1beta1"
        f"/projects/{PROJECT_ID}"
        f"/services/aiplatform.googleapis.com/consumerQuotaMetrics"
        f"?pageSize=200&view=FULL"
    )
    data = _get(url, token)
    if "_error" in data:
        return [{"error": data["_error"]}]

    rows = []
    for m in data.get("metrics", []):
        metric = m.get("metric", "")
        if "generate_content" not in metric:
            continue
        display = m.get("displayName", metric.split("/")[-1])
        for ql in m.get("consumerQuotaLimits", []):
            unit = ql.get("unit", "")
            for bucket in ql.get("quotaBuckets", []):
                rows.append({
                    "display": display,
                    "metric":  metric,
                    "unit":    unit,
                    "limit":   bucket.get("effectiveLimit", "?"),
                })
    return rows


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{'=' * 72}")
    print(f"  EduFlow — Vertex AI Quota Usage Report")
    print(f"  Project : {PROJECT_ID}   Location: {LOCATION}")
    print(f"  Time    : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 72}\n")

    print("  Getting ADC token...")
    try:
        token = _get_token()
        print("  OK.\n")
    except Exception as e:
        print(f"  FAILED: {e}\n  Run: gcloud auth application-default login")
        sys.exit(1)

    # ── Discover metrics ──────────────────────────────────────────────────────
    print(DIVIDER)
    print("  STEP 1 — Discover available aiplatform metrics")
    print(DIVIDER)
    metrics = discover_metrics(token)
    if metrics:
        print(f"  Found {len(metrics)} generate_content/token metrics:\n")
        for m in metrics:
            print(f"    {m}")
    else:
        print("  No metrics found via descriptor API.")
        print("  Using known metric names as fallback.\n")
        metrics = [
            "aiplatform.googleapis.com/quota/generate_content_requests_per_minute_per_project_per_base_model/usage",
            "aiplatform.googleapis.com/quota/generate_content_input_tokens_per_minute_per_project_per_base_model/usage",
        ]

    # ── Usage ─────────────────────────────────────────────────────────────────
    print(f"\n{DIVIDER}")
    print("  STEP 2 — Usage last 60 minutes (Cloud Monitoring)")
    print(DIVIDER)

    usage_metrics = [m for m in metrics if m.endswith("/usage")]
    if not usage_metrics:
        usage_metrics = metrics  # try all if no /usage suffix found

    all_usage: dict[str, dict[str, float]] = {}
    for metric in usage_metrics:
        label = metric.split("/")[-2] if "/" in metric else metric
        label = label.replace("generate_content_", "").replace("_per_minute_per_project_per_base_model", "")
        result = fetch_usage(token, metric, minutes=60)
        if "_error" not in result:
            for model, val in result.items():
                if model not in all_usage:
                    all_usage[model] = {}
                all_usage[model][label] = val

    if all_usage:
        for model in sorted(all_usage.keys()):
            tag = ""
            if "2.5-flash" in model and "lite" not in model:
                tag = "  ◄ MAIN AGENTS"
            elif "lite" in model:
                tag = "  ◄ AUDIO TRANSCRIPTION"
            print(f"\n  Model: {model}{tag}")
            for metric_label, val in sorted(all_usage[model].items()):
                print(f"    {metric_label:<40}: {int(val):>10,}")
    else:
        print("\n  No usage data returned.")
        print("  Cloud Monitoring metrics may take 2-3 min to appear after API calls.")

    # ── Limits via REST ───────────────────────────────────────────────────────
    print(f"\n{DIVIDER}")
    print("  STEP 3 — Quota Limits (Service Usage API)")
    print(DIVIDER)
    limits = fetch_limits_rest(token)
    if limits and "error" not in limits[0]:
        print(f"\n  {'Name':<50} {'Limit':>12}  Unit")
        print(f"  {'-'*50} {'-'*12}  {'-'*15}")
        for row in limits:
            name = row["display"][:50]
            lim  = row["limit"]
            lim_fmt = f"{int(lim):,}" if isinstance(lim, (int, float)) else str(lim)
            print(f"  {name:<50} {lim_fmt:>12}  {row['unit']}")
    else:
        err = limits[0].get("error", "") if limits else ""
        print(f"\n  Service Usage API error: {err}")

    # ── gcloud fallback ───────────────────────────────────────────────────────
    print(f"\n{DIVIDER}")
    print("  STEP 4 — Quota Limits (gcloud CLI fallback)")
    print(DIVIDER)
    print(fetch_limits_gcloud())

    # ── Manual check instructions ─────────────────────────────────────────────
    print(f"\n{DIVIDER}")
    print("  STEP 5 — Manual GCP Console Check (always reliable)")
    print(DIVIDER)
    console_url = (
        f"https://console.cloud.google.com/apis/api/aiplatform.googleapis.com/quotas"
        f"?project={PROJECT_ID}"
    )
    print(f"""
  Open this URL to see exact limits and current usage:
  {console_url}

  Filter by: "gemini-2.5-flash"
  Columns to check:
    - generate_content_requests_per_minute  →  your RPM limit
    - generate_content_input_tokens_per_minute  →  your TPM limit

  EduFlow uses ~5-7 LLM calls per planning request.
  If RPM limit < 60, expect 429s during testing.
  Request increase: click the metric → "Edit Quota" → request higher value.
""")
    print(f"{'=' * 72}\n")


if __name__ == "__main__":
    main()
