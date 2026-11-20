# GitHub REST API 推送参考

## 为什么需要这条路

在某些网络环境下 `git push` 会失败（`Empty reply from server` 等），但 `curl` 访问 `api.github.com` 正常。此时可用 REST API 直接构造 Git 对象完成推送，不依赖 git 协议。

## Git 对象模型

一次提交由四种对象串成：

```
文件内容 --base64--> blob（内容）
blob + 路径 --------> tree（目录结构）
tree + 父提交 ------> commit（一次变更）
commit -------------> ref（分支指针移动）
```

## 端点清单

所有请求带认证：`curl -u "OWNER:TOKEN" -H "Accept: application/vnd.github+json"`

| 步骤 | 方法 | 路径 | 关键参数 |
|---|---|---|---|
| 建初始提交 | `PUT` | `/repos/{o}/{r}/contents/{path}` | message, content(base64), branch |
| 上传文件 | `POST` | `/repos/{o}/{r}/git/blobs` | content(base64), encoding:"base64" |
| 组装目录树 | `POST` | `/repos/{o}/{r}/git/trees` | base_tree(旧tree sha), tree:[{path,mode,type,sha}] |
| 创建提交 | `POST` | `/repos/{o}/{r}/git/commits` | message, tree(sha), parents:[旧commit sha] |
| 移动分支 | `PATCH` | `/repos/{o}/{r}/git/refs/heads/{branch}` | sha(新commit sha), force:false |
| 新建分支 | `POST` | `/repos/{o}/{r}/git/refs` | ref:"refs/heads/{branch}", sha |
| 查当前提交 | `GET` | `/repos/{o}/{r}/commits/{branch}` | 返回 sha 与 commit.tree.sha |
| 建仓库 | `POST` | `/user/repos` | name, description, private, auto_init:false |

## 关键坑（务必遵守）

1. **空仓库不能用 Git Data API**：`POST /git/blobs` 会报 `409 Git Repository is empty`。先用 `PUT /contents/{path}` 放一个文件建立初始提交。
2. **commit 必须带 parents**：传空数组会创建孤立提交，ref 更新后分支仍指向旧内容。把当前分支的 commit sha 放进 `parents`。
3. **base_tree 填旧 tree sha**：保证增量修改而非整仓替换。
4. **PATCH ref 失败时改用 POST**：分支不存在时 PATCH 返回无 object，此时用 `POST /git/refs` 创建。
5. **token 权限**：Personal Access Token 需 `repo` scope（经典 token）或 Contents 读写权限（fine-grained token）。

## 凭证获取（macOS）

本机凭证常存在钥匙串，避免硬编码：

```bash
# 读取（不会回显内容到日志，注意不要打印）
security find-internet-password -s github.com -w

# 检查权限范围
curl -s -D - -o /dev/null -u "USER:TOKEN" https://api.github.com/user | grep -i x-oauth-scopes
```

环境变量方式（更安全，推荐）：

```bash
export GH_TOKEN="your_token"
python3 scripts/github_api_push.py <目录> <owner> <repo> [分支] [说明]
```

脚本读取优先级：`GH_TOKEN` 环境变量 → macOS 钥匙串。

## 安全注意

- 绝不要把 token 打印到聊天、日志或命令行历史
- 推送后如曾把凭证写进 remote URL，用 `git remote set-url origin https://github.com/OWNER/REPO.git` 清除
- 提交前检查 `.gitignore`，避免 credentials / .env / 密钥文件被上传
