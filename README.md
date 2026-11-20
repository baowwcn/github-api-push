# github-api-push

绕过 git 协议，用 GitHub REST API 直接推送文件到仓库。

适用于 **`git push` 被网络层拦截**（报 `Empty reply`、`Could not resolve host`、超时等），但 `curl` 能访问 `api.github.com` 的环境。

## 为什么需要它

Git 本质是四种对象串成的链：

```
文件内容 → blob（存内容）
一堆 blob + 路径 → tree（目录结构）
tree + 父提交 → commit（一次变更）
commit → ref（把分支指针挪过去）
```

这个 Skill 用 REST API 直接创建这四种对象，等价于一次 `git commit + push`，全程不碰 git 协议。

## 安装

作为 WorkBuddy Skill 使用，克隆到用户级 skills 目录：

```bash
git clone https://github.com/baowwcn/github-api-push.git ~/.workbuddy/skills/github-api-push
```

重启 WorkBuddy 后生效。

## 使用

### 方式一：直接说（推荐）

> "帮我把这个目录 push 到 GitHub"
> "git push 失败了，用 API 上传"

Agent 会自动加载 Skill，诊断网络、必要时建仓库、推送并验证。

### 方式二：直接跑脚本

```bash
python3 scripts/github_api_push.py <本地目录> <owner> <repo> [分支] [提交说明]

# 示例
python3 scripts/github_api_push.py ./myproject baowwcn myrepo main "Initial commit"
```

默认分支为 `main`，默认提交说明为 `Upload files via GitHub API`。

## 凭证

按优先级读取：

1. 环境变量 `GH_TOKEN`
2. macOS 钥匙串：`security find-internet-password -s github.com -w`

token 需要 `repo` 权限。凭证不会写入日志，也不会存进仓库。

## 目录结构

```
github-api-push/
├── SKILL.md                    4 步工作流 + 触发词 + 凭证说明
├── scripts/
│   └── github_api_push.py      主脚本（实战验证）
└── references/
    └── api_reference.md        Git 对象模型、API 端点、踩坑记录
```

## 已处理的坑

- 空仓库不能用 Git Data API → 先用 Contents API 建初始提交
- commit 必须带 `parents` → 否则变成孤立提交，ref 更新失败
- `base_tree` 填旧 tree sha → 增量追加而非替换整个仓库
- 分支不存在时自动改用 `POST /git/refs` 创建

## License

MIT
