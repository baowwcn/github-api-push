#!/usr/bin/env python3
"""
push via GitHub REST API — 绕过 git 协议，适用于 git push 被网络拦截的环境。

原理：Git 本质是 blob / tree / commit / ref 四种对象的链。
本脚本用 API 直接创建这些对象，等价于一次 git commit + push。

用法：
  python3 github_api_push.py <本地目录> <owner> <repo> [分支] [提交说明]

凭证来源（按优先级）：
  1. 环境变量 GH_TOKEN
  2. macOS 钥匙串: security find-internet-password -s github.com -w
"""
import base64
import json
import os
import subprocess
import sys
from pathlib import Path

# ---------- 参数 ----------
if len(sys.argv) < 4:
    sys.exit("用法: python3 github_api_push.py <目录> <owner> <repo> [分支] [说明]")

REPO_DIR = Path(sys.argv[1]).resolve()
OWNER = sys.argv[2]
REPO = sys.argv[3]
BRANCH = sys.argv[4] if len(sys.argv) > 4 else "main"
MSG = sys.argv[5] if len(sys.argv) > 5 else "Upload files via GitHub API"

if not REPO_DIR.is_dir():
    sys.exit(f"目录不存在: {REPO_DIR}")

# ---------- 读取 token ----------
token = os.environ.get("GH_TOKEN", "").strip()
if not token:
    token = subprocess.run(
        ["security", "find-internet-password", "-s", "github.com", "-w"],
        capture_output=True, text=True,
    ).stdout.strip()
if not token:
    sys.exit("未找到 token：请设置 GH_TOKEN 或确认钥匙串中有 github.com 凭证")

# ---------- API 封装 ----------
def api(method, path, payload=None):
    """用 curl 调 API（curl 通常能通，而 git 协议可能被拦）。"""
    cmd = ["curl", "-s", "--max-time", "30", "-X", method,
           "-u", f"{OWNER}:{token}",
           "-H", "Accept: application/vnd.github+json",
           "-H", "Content-Type: application/json",
           f"https://api.github.com/repos/{OWNER}/{REPO}{path}"]
    if payload is not None:
        cmd += ["-d", json.dumps(payload)]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    try:
        return json.loads(out)
    except Exception:
        raise RuntimeError(f"API {method} {path} 返回异常: {out[:200]}")

# ---------- 收集要上传的文件 ----------
skip_dirs = {".git", "__pycache__", "node_modules", ".DS_Store"}
skip_names = {".DS_Store"}
files = []
for f in sorted(REPO_DIR.rglob("*")):
    if not f.is_file():
        continue
    rel = f.relative_to(REPO_DIR)
    if any(p in skip_dirs for p in rel.parts) or f.name in skip_names or f.name.endswith(".pyc"):
        continue
    files.append((rel.as_posix(), f))

# ---------- 前置：确保分支存在（空仓库需先建一个初始提交）----------
cur = api("GET", f"/commits/{BRANCH}")
if cur.get("sha"):
    base_tree = cur["commit"]["tree"]["sha"]
    parent = cur["sha"]
    print(f"基于现有提交 {parent[:12]}")
else:
    # 空仓库：用 Contents API 放一个占位文件建立初始提交
    seed = {"message": "init", "content": base64.b64encode(b"# init\n").decode(), "branch": BRANCH}
    r = api("PUT", "/contents/.gitkeep", seed)
    cur = api("GET", f"/commits/{BRANCH}")
    base_tree = cur["commit"]["tree"]["sha"]
    parent = cur["sha"]
    print(f"空仓库已初始化，基线提交 {parent[:12]}")

# ---------- 1. 上传每个文件为 blob ----------
tree_items = []
for rel_path, f in files:
    encoded = base64.b64encode(f.read_bytes()).decode("ascii")
    blob = api("POST", "/git/blobs", {"content": encoded, "encoding": "base64"})
    if not blob.get("sha"):
        raise RuntimeError(f"blob 创建失败: {rel_path} -> {blob}")
    tree_items.append({"path": rel_path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
    print(f"  blob  {rel_path}")

# ---------- 2. 组装 tree ----------
tree = api("POST", "/git/trees", {"base_tree": base_tree, "tree": tree_items})
if not tree.get("sha"):
    raise RuntimeError(f"tree 创建失败: {tree}")

# ---------- 3. 创建 commit（必须带 parents，否则会脱离分支）----------
commit = api("POST", "/git/commits", {
    "message": MSG,
    "tree": tree["sha"],
    "parents": [parent],
})
if not commit.get("sha"):
    raise RuntimeError(f"commit 创建失败: {commit}")

# ---------- 4. 更新 ref 指向新 commit ----------
ref = api("PATCH", f"/git/refs/heads/{BRANCH}", {"sha": commit["sha"], "force": False})
if not ref.get("object"):
    # 分支不存在时改用 POST 创建
    ref = api("POST", "/git/refs", {"ref": f"refs/heads/{BRANCH}", "sha": commit["sha"]})

print(f"\n完成：{len(files)} 个文件 -> {OWNER}/{REPO}@{BRANCH}")
print(f"commit: {commit['sha'][:12]}")
print(f"地址: https://github.com/{OWNER}/{REPO}")
