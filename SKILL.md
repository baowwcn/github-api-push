---
name: github-api-push
description: Push local files to a GitHub repository via the REST API when git push fails or the git protocol is blocked. This skill should be used when the user asks to 上传文件到GitHub / push到GitHub / git push失败 / Empty reply from server / 用API提交GitHub / 绕过git协议推送, or when `git push` returns network errors but `curl` to api.github.com works. It builds commit objects directly through the API (blobs/tree/commit/ref) without the git protocol.
agent_created: true
---

# GitHub API Push

## Overview

Push a local directory to a GitHub repository using the REST API, bypassing the git protocol entirely. Use this when `git push` fails (e.g. `Empty reply from server`, connection blocked) but HTTPS requests to `api.github.com` succeed. The bundled script builds Git objects directly (blob → tree → commit → ref), reproducing what `git commit && git push` does.

## When to Use

- `git push` fails with network errors while curl to GitHub API works
- User asks to 用 API 上传 GitHub / 绕过 git 协议推送
- Environment has no git credentials but has a GitHub token in keychain or `GH_TOKEN`
- Need to create a repo and push files without git CLI

Do NOT use for normal environments where `git push` works — plain git is simpler there.

## Credentials

The script reads a token in this order:
1. `GH_TOKEN` environment variable
2. macOS keychain: `security find-internet-password -s github.com -w`

The token needs `repo` scope (classic) or Contents read/write (fine-grained). Never print the token into chat or logs. To inspect scope without exposing it:

```bash
curl -s -D - -o /dev/null -u "USER:TOKEN" https://api.github.com/user | grep -i x-oauth-scopes
```

## Workflow

### Step 1 — Confirm the diagnosis
Verify that git protocol fails but the API works:

```bash
git ls-remote https://github.com/OWNER/REPO.git HEAD   # often fails
curl -s -u "OWNER:TOKEN" https://api.github.com/user    # should return user JSON
```

If both work, recommend plain git instead. If only the API works, continue.

### Step 2 — Ensure the repository exists
If the target repo does not exist, create it via API:

```bash
curl -s -u "OWNER:TOKEN" -X POST https://api.github.com/user/repos \
  -H "Content-Type: application/json" \
  -d '{"name":"REPO","description":"...","private":false,"auto_init":false}'
```

### Step 3 — Push with the bundled script
```bash
python3 <skill>/scripts/github_api_push.py <本地目录> <owner> <repo> [branch] [commit message]
```

The script handles: empty-repo initialization, uploading each file as a blob, assembling a tree, creating a commit with the correct `parents`, and moving the branch ref. It skips `.git`, `node_modules`, `__pycache__`, `.pyc`, `.DS_Store`.

### Step 4 — Verify
Check the branch tree and confirm no secrets were uploaded:

```bash
curl -s -u "OWNER:TOKEN" \
  "https://api.github.com/repos/OWNER/REPO/git/trees/BRANCH?recursive=1"
```

If credentials were ever placed in a remote URL, clear them:
```bash
git remote set-url origin https://github.com/OWNER/REPO.git
```

## Critical Details

Consult `references/api_reference.md` for the endpoint list and pitfalls. The three most important:
- Empty repos reject Git Data API with `409` — seed a file via `PUT /contents` first.
- Commits must include `parents: [current_sha]`; an empty array creates an orphan commit and the branch ref will not move.
- `base_tree` must be the current tree sha for incremental changes.

## Resources

### scripts/
- `github_api_push.py` — main script; token via `GH_TOKEN` or macOS keychain; builds blobs/tree/commit/ref through the API

### references/
- `api_reference.md` — Git object model, endpoint table, pitfalls, credential handling, security notes
