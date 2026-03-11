#!/usr/bin/env python3
"""
MLVCS - ML Versioning Control System CLI
Usage: python mlvcs.py [command] [options]
"""
import argparse
import json
import os
import sys
import requests
from pathlib import Path

API_URL = os.environ.get("MLVCS_API_URL", "http://localhost:8000")
CONFIG_FILE = Path.home() / ".mlvcs_config.json"


def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}


def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def get_api_url():
    cfg = load_config()
    return cfg.get("api_url", API_URL)


def api(method, path, **kwargs):
    url = f"{get_api_url()}/api/v1{path}"
    try:
        r = getattr(requests, method)(url, **kwargs)
        if r.status_code >= 400:
            print(f"❌ Error {r.status_code}: {r.text}")
            sys.exit(1)
        if r.content and r.headers.get("content-type", "").startswith("application/json"):
            return r.json()
        return r
    except requests.ConnectionError:
        print(f"❌ Cannot connect to API at {get_api_url()}")
        print("   Make sure the server is running: docker-compose up -d")
        sys.exit(1)


def fmt_json(data):
    print(json.dumps(data, indent=2, default=str, ensure_ascii=False))


# ── config ────────────────────────────────────────────────────────────────────

def cmd_config(args):
    if args.api_url:
        cfg = load_config()
        cfg["api_url"] = args.api_url
        save_config(cfg)
        print(f"✅ API URL set to: {args.api_url}")
    else:
        cfg = load_config()
        print(f"API URL: {cfg.get('api_url', API_URL)}")


# ── health ────────────────────────────────────────────────────────────────────

def cmd_health(args):
    url = f"{get_api_url()}/health"
    try:
        r = requests.get(url)
        data = r.json()
        print(f"✅ API Status: {data.get('status', 'unknown')}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")


# ── projects ──────────────────────────────────────────────────────────────────

def cmd_project_create(args):
    data = api("post", "/projects/", json={"name": args.name, "description": args.description})
    print(f"✅ Project created: {data['name']} (id: {data['id']})")
    cfg = load_config()
    cfg["current_project"] = data["id"]
    cfg["current_project_name"] = data["name"]
    save_config(cfg)
    print(f"📌 Set as current project")


def cmd_project_list(args):
    projects = api("get", "/projects/")
    if not projects:
        print("No projects found. Create one with: mlvcs project create <name>")
        return
    print(f"\n{'ID':<38} {'NAME':<30} {'CREATED'}")
    print("-" * 85)
    for p in projects:
        created = p['created_at'][:10] if p.get('created_at') else '-'
        print(f"{p['id']:<38} {p['name']:<30} {created}")


def cmd_project_use(args):
    projects = api("get", "/projects/")
    found = next((p for p in projects if p['name'] == args.name or p['id'] == args.name), None)
    if not found:
        print(f"❌ Project '{args.name}' not found")
        sys.exit(1)
    cfg = load_config()
    cfg["current_project"] = found["id"]
    cfg["current_project_name"] = found["name"]
    save_config(cfg)
    print(f"✅ Using project: {found['name']} (id: {found['id']})")


def get_current_project():
    cfg = load_config()
    pid = cfg.get("current_project")
    if not pid:
        print("❌ No project selected. Use: mlvcs project use <name>")
        sys.exit(1)
    return pid, cfg.get("current_project_name", pid)


# ── experiments ───────────────────────────────────────────────────────────────

def cmd_exp_create(args):
    pid, pname = get_current_project()
    params = json.loads(args.params) if args.params else None
    tags = args.tags.split(",") if args.tags else None
    data = api("post", f"/projects/{pid}/experiments", json={
        "name": args.name,
        "description": args.description,
        "params": params,
        "tags": tags,
        "git_commit_hash": args.commit,
    })
    print(f"✅ Experiment created: {data['name']} (id: {data['id']})")
    cfg = load_config()
    cfg["current_experiment"] = data["id"]
    cfg["current_experiment_name"] = data["name"]
    save_config(cfg)
    print(f"📌 Set as current experiment")


def cmd_exp_list(args):
    pid, pname = get_current_project()
    experiments = api("get", f"/projects/{pid}/experiments")
    if not experiments:
        print(f"No experiments in project '{pname}'")
        return
    print(f"\nProject: {pname}")
    print(f"{'ID':<38} {'NAME':<30} {'STATUS':<12} {'CREATED'}")
    print("-" * 95)
    for e in experiments:
        created = e['created_at'][:10] if e.get('created_at') else '-'
        print(f"{e['id']:<38} {e['name']:<30} {e['status']:<12} {created}")


def cmd_exp_update(args):
    pid, _ = get_current_project()
    cfg = load_config()
    eid = cfg.get("current_experiment")
    if not eid:
        print("❌ No experiment selected")
        sys.exit(1)

    payload = {}
    if args.status:
        payload["status"] = args.status
    if args.metrics:
        payload["metrics"] = json.loads(args.metrics)

    data = api("patch", f"/projects/{pid}/experiments/{eid}", json=payload)
    print(f"✅ Experiment updated: {data['name']} status={data['status']}")
    if data.get('metrics'):
        print(f"   Metrics: {json.dumps(data['metrics'], indent=4)}")


def cmd_exp_show(args):
    pid, _ = get_current_project()
    cfg = load_config()
    eid = cfg.get("current_experiment")
    if not eid:
        print("❌ No experiment selected")
        sys.exit(1)
    data = api("get", f"/projects/{pid}/experiments/{eid}")
    fmt_json(data)


# ── models ────────────────────────────────────────────────────────────────────

def cmd_model_register(args):
    cfg = load_config()
    eid = cfg.get("current_experiment")
    if not eid:
        print("❌ No experiment selected")
        sys.exit(1)

    params = json.loads(args.params) if args.params else None
    metrics = json.loads(args.metrics) if args.metrics else None
    tags = args.tags.split(",") if args.tags else None

    data = api("post", f"/experiments/{eid}/models", json={
        "version": args.version,
        "model_name": args.name,
        "framework": args.framework,
        "params": params,
        "metrics": metrics,
        "tags": tags,
        "git_commit_hash": args.commit,
    })
    print(f"✅ Model registered: {data['model_name']} v{data['version']} (id: {data['id']})")
    cfg["current_model"] = data["id"]
    save_config(cfg)


def cmd_model_upload(args):
    cfg = load_config()
    eid = cfg.get("current_experiment")
    mid = cfg.get("current_model")
    if not eid or not mid:
        print("❌ No experiment/model selected")
        sys.exit(1)

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"❌ File not found: {args.file}")
        sys.exit(1)

    print(f"⬆️  Uploading {file_path.name} ({file_path.stat().st_size} bytes)...")
    with open(file_path, "rb") as f:
        result = api("post", f"/experiments/{eid}/models/{mid}/upload",
                     files={"file": (file_path.name, f, "application/octet-stream")})
    print(f"✅ Uploaded: {result['path']} ({result['size_bytes']} bytes)")


def cmd_model_list(args):
    cfg = load_config()
    eid = cfg.get("current_experiment")
    if not eid:
        print("❌ No experiment selected")
        sys.exit(1)

    models = api("get", f"/experiments/{eid}/models")
    if not models:
        print("No model versions found")
        return
    print(f"\n{'ID':<38} {'NAME':<25} {'VERSION':<10} {'FRAMEWORK':<12} {'PROD':<5} {'CREATED'}")
    print("-" * 105)
    for m in models:
        created = m['created_at'][:10] if m.get('created_at') else '-'
        prod = "✅" if m.get('is_production') else ""
        print(f"{m['id']:<38} {m['model_name']:<25} {m['version']:<10} {(m.get('framework') or '-'):<12} {prod:<5} {created}")


def cmd_model_promote(args):
    cfg = load_config()
    eid = cfg.get("current_experiment")
    mid = cfg.get("current_model")
    if not eid or not mid:
        print("❌ No experiment/model selected")
        sys.exit(1)
    result = api("patch", f"/experiments/{eid}/models/{mid}/promote")
    print(f"✅ {result['message']}")


# ── commits ───────────────────────────────────────────────────────────────────

def cmd_commit(args):
    pid, pname = get_current_project()
    files = []
    if args.files:
        for fp in args.files:
            p = Path(fp)
            if p.exists():
                files.append({"path": p.name, "content": p.read_text(errors="replace")})
            else:
                print(f"⚠️  File not found, skipping: {fp}")

    data = api("post", f"/projects/{pid}/commits", json={
        "message": args.message,
        "author": args.author,
        "branch": args.branch,
        "files": files,
    })
    print(f"✅ Committed: {data['commit_hash'][:7]} - {data['message']}")
    if data.get("files_changed"):
        print(f"   Files: {', '.join(data['files_changed'])}")


def cmd_log(args):
    pid, pname = get_current_project()
    result = api("get", f"/projects/{pid}/history", params={"limit": args.limit})
    commits = result.get("commits", [])
    if not commits:
        print("No commits found")
        return
    print(f"\nProject: {pname}")
    print("-" * 70)
    for c in commits:
        date = c.get('date', '')[:16]
        print(f"  {c['short_hash']}  {date}  {c['author']}")
        print(f"           {c['message']}")
        if c.get('files'):
            print(f"           Files: {', '.join(c['files'][:5])}")
        print()


def cmd_diff(args):
    pid, _ = get_current_project()
    result = api("get", f"/projects/{pid}/commits/{args.commit}/diff")
    print(result.get("diff", "No diff available"))


def cmd_branches(args):
    pid, pname = get_current_project()
    result = api("get", f"/projects/{pid}/branches")
    branches = result.get("branches", [])
    print(f"\nBranches for project '{pname}':")
    for b in branches:
        print(f"  • {b}")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(prog="mlvcs", description="ML Versioning Control System CLI")
    sub = parser.add_subparsers(dest="command")

    # config
    p_cfg = sub.add_parser("config", help="Configure CLI")
    p_cfg.add_argument("--api-url", help="Set API URL")

    # health
    sub.add_parser("health", help="Check API health")

    # project
    p_proj = sub.add_parser("project", help="Project management")
    proj_sub = p_proj.add_subparsers(dest="subcommand")
    p_create = proj_sub.add_parser("create", help="Create a project")
    p_create.add_argument("name")
    p_create.add_argument("--description", "-d", default=None)
    proj_sub.add_parser("list", help="List projects")
    p_use = proj_sub.add_parser("use", help="Switch to project")
    p_use.add_argument("name")

    # experiment
    p_exp = sub.add_parser("experiment", help="Experiment management")
    exp_sub = p_exp.add_subparsers(dest="subcommand")
    p_ec = exp_sub.add_parser("create", help="Create experiment")
    p_ec.add_argument("name")
    p_ec.add_argument("--description", "-d", default=None)
    p_ec.add_argument("--params", "-p", help='JSON params e.g. \'{"lr": 0.001}\'')
    p_ec.add_argument("--tags", help="Comma-separated tags")
    p_ec.add_argument("--commit", help="Git commit hash")
    exp_sub.add_parser("list", help="List experiments")
    p_eu = exp_sub.add_parser("update", help="Update experiment")
    p_eu.add_argument("--status", choices=["created", "running", "completed", "failed"])
    p_eu.add_argument("--metrics", help='JSON metrics e.g. \'{"accuracy": 0.95}\'')
    exp_sub.add_parser("show", help="Show current experiment details")

    # model
    p_model = sub.add_parser("model", help="Model version management")
    model_sub = p_model.add_subparsers(dest="subcommand")
    p_mr = model_sub.add_parser("register", help="Register a model version")
    p_mr.add_argument("name")
    p_mr.add_argument("--version", "-v", default="1.0.0")
    p_mr.add_argument("--framework", "-f", default=None)
    p_mr.add_argument("--params", help="JSON params")
    p_mr.add_argument("--metrics", help="JSON metrics")
    p_mr.add_argument("--tags", help="Comma-separated tags")
    p_mr.add_argument("--commit", help="Git commit hash")
    p_mu = model_sub.add_parser("upload", help="Upload model artifact")
    p_mu.add_argument("file", help="Path to model file")
    model_sub.add_parser("list", help="List model versions")
    model_sub.add_parser("promote", help="Promote model to production")

    # commit
    p_com = sub.add_parser("commit", help="Commit code files")
    p_com.add_argument("--message", "-m", required=True, help="Commit message")
    p_com.add_argument("--author", "-a", default="MLVCS User")
    p_com.add_argument("--branch", "-b", default="main")
    p_com.add_argument("--files", "-f", nargs="+", help="Files to commit")

    # log
    p_log = sub.add_parser("log", help="Show commit history")
    p_log.add_argument("--limit", type=int, default=20)

    # diff
    p_diff = sub.add_parser("diff", help="Show commit diff")
    p_diff.add_argument("commit", help="Commit hash")

    # branches
    sub.add_parser("branches", help="List branches")

    args = parser.parse_args()

    dispatch = {
        ("config", None): cmd_config,
        ("health", None): cmd_health,
        ("project", "create"): cmd_project_create,
        ("project", "list"): cmd_project_list,
        ("project", "use"): cmd_project_use,
        ("experiment", "create"): cmd_exp_create,
        ("experiment", "list"): cmd_exp_list,
        ("experiment", "update"): cmd_exp_update,
        ("experiment", "show"): cmd_exp_show,
        ("model", "register"): cmd_model_register,
        ("model", "upload"): cmd_model_upload,
        ("model", "list"): cmd_model_list,
        ("model", "promote"): cmd_model_promote,
        ("commit", None): cmd_commit,
        ("log", None): cmd_log,
        ("diff", None): cmd_diff,
        ("branches", None): cmd_branches,
    }

    key = (args.command, getattr(args, "subcommand", None))
    fn = dispatch.get(key)
    if fn:
        fn(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
