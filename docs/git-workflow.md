# SellPilot 分支与 Tag 规则

SellPilot 采用最简 Git Flow，不提前创建大量分支，也不建立成员个人长期分支。

```text
main
└── develop
    ├── feature/具体任务
    ├── fix/具体问题
    └── docs/具体文档
```

核心原则：

- `main` 保存稳定里程碑和 Tag 基线。
- `develop` 保存当前日常集成结果。
- 每次只为当前可验收任务创建一个短期分支。
- 所有分支合并均通过 Pull Request。
- 任务合并后删除短期分支。
- Tag 只由组长在 `main` 上创建。

## 分支用途

| 分支 | 用途 | 长期保留 |
| --- | --- | ---: |
| `main` | 稳定版本和 Tag 基线 | 是 |
| `develop` | 日常集成 | 是 |
| `feature/*` | 新功能开发 | 否 |
| `fix/*` | 普通 Bug 修复 | 否 |
| `docs/*` | 独立文档修改 | 否 |
| `hotfix/*` | 已打 Tag 版本的紧急修复 | 否 |

不创建成员个人永久分支，例如 `member1`、`member2` 或 `frontend-personal`。一个短期分支必须对应一个可明确验收的任务。

## 分支命名

功能分支使用小写英文和短横线：

```text
feature/<模块>-<任务>
```

示例：

```text
feature/market-data-import
feature/product-management
feature/selection-scoring
feature/review-analysis
feature/content-generation
feature/customer-service
feature/rag-knowledge-base
feature/order-management
```

修复和文档分支示例：

```text
fix/sidebar-overflow
fix/order-pagination
docs/api-documentation
docs/user-manual
```

禁止使用 `feature/frontend`、`feature/backend`、`feature/my-work` 或 `feature/update` 等无法明确验收的宽泛名称。

## 开始任务

每次从最新的 `develop` 创建短期分支：

```powershell
git switch develop
git pull --ff-only origin develop
git switch -c feature/market-data-import
git push -u origin feature/market-data-import
```

随后只在任务分支开发。禁止直接在 `main` 或 `develop` 上开发业务代码。

## 提交规则

提交信息格式：

```text
<类型>: <简短说明>
```

允许的类型：

| 类型 | 用途 |
| --- | --- |
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档 |
| `refactor` | 不改变功能的重构 |
| `test` | 测试 |
| `build` | 依赖和构建配置 |
| `chore` | 普通维护 |
| `ci` | CI 配置 |

规则：

1. 一个提交只处理一个主题。
2. 不使用“update”“修改一下”“final”等模糊说明。
3. 不提交测试失败的代码。
4. 不提交 `.env`、密钥、缓存、构建产物、真实个人数据或真实店铺数据。
5. 不把其他成员的无关文件混入提交。
6. 提交前执行对应模块检查和测试。

## 功能完成与 Pull Request

### 1. 同步最新 `develop`

在任务分支执行：

```powershell
git fetch origin
git merge origin/develop
```

如有冲突，在当前任务分支解决，不在 `develop` 上解决功能分支冲突。

### 2. 完成检查

基础检查：

```powershell
git status
git diff --check
```

后端任务：

```powershell
cd backend
uv run ruff format --check .
uv run ruff check .
uv run pytest -q
```

前端任务：

```powershell
cd frontend
npm run format:check
npm run lint
npm run typecheck
npm run test:run
npm run build
```

单模块任务可执行对应模块测试；合并关键版本前必须执行全量检查。

### 3. 创建 PR

推送任务分支后创建 Pull Request：

```text
base: develop
compare: feature/market-data-import
```

普通任务不得错误选择 `main` 作为目标分支。PR 至少说明：

- 修改了什么。
- 没有修改什么。
- 检查和测试结果。
- 适用的页面截图或接口示例。
- 已知问题。
- 是否影响其他模块。

### 4. 合并后删除分支

```powershell
git switch develop
git pull --ff-only origin develop
git branch -d feature/market-data-import
git push origin --delete feature/market-data-import
```

短期任务分支不长期保留。

## 直接修改 `develop` 的边界

队友原则上不得直接提交到 `develop`。新业务功能、数据库结构、API、页面、Agent、RAG、依赖升级和较大 Bug 修复都必须创建任务分支。

组长仅可在工作区干净且没有成员同时修改相同文件时，直接处理以下极小且低风险的变更：

- README 错字或一两行文档修正。
- 明确且低风险的配置修正。
- 打 Tag 前的版本号和说明同步。

即使由组长操作，数据库、公共 API、公共组件接口、依赖、Agent 状态、跨模块变更或可能影响其他成员的修改仍须创建分支并通过 PR。

判断标准：修改失败后如果可能影响其他成员开发，就必须创建分支。

## `main` 与里程碑

`main` 只保存经过验证的稳定里程碑。禁止在 `main` 开发功能、解决普通 Bug、运行实验性修改，或在功能未完成时合并 `develop`。

正常流程：

```text
feature/*、fix/*、docs/*
          ↓ PR
       develop
          ↓ 完整测试和里程碑 PR
         main
          ↓
         Tag
```

## 版本与 Tag

版本采用语义化格式 `v主版本.次版本.修订版本`：

- 主版本，如 `v1.0.0`：最终完整版本、大规模架构变更或不兼容调整。
- 次版本，如 `v0.2.0`：一组可验收的新功能形成的稳定里程碑。
- 修订版本，如 `v0.2.1`：修复已有版本问题，不增加主要功能。

建议里程碑：

| Tag | 建议范围 |
| --- | --- |
| `v0.1.0` | 后端公共底座、前端框架、组件库和 Dashboard |
| `v0.2.0` | 市场数据、商品、订单、库存和 Mock 业务能力 |
| `v0.3.0` | 智能选品、评论分析、产品改良和内容生成 |
| `v0.4.0` | 智能客服和 RAG |
| `v0.5.0` | AI 运营助手和跨模块编排 |
| `v0.9.0` | 完整集成演示候选版 |
| `v1.0.0` | 最终提交和答辩版本 |

这些版本不是必须凑齐；只有形成稳定里程碑才打 Tag。

## Tag 创建规则

Tag 只能由组长创建，并且必须满足：

1. Tag 创建在 `main` 上。
2. `main` 已同步远程。
3. 工作区干净。
4. 前后端适用测试通过。
5. README 版本说明正确。
6. 当前提交确实对应目标版本。
7. Tag 名称尚不存在。

创建附注 Tag 前先检查：

```powershell
git switch main
git pull --ff-only origin main
git status
git log --oneline --decorate -8
git tag --list
```

创建、核对并推送：

```powershell
git tag -a v0.2.0 -m "SellPilot v0.2.0 data and commerce foundation"
git rev-parse "v0.2.0^{}"
git rev-parse main
git push origin v0.2.0
```

`git rev-parse` 的两个结果必须相同。

## Tag 与 GitHub Release

- 内部里程碑和阶段验收通常只创建 Git Tag。
- 最终交付版需要正式展示或上传附件时，可创建 GitHub Release。
- `v0.1.0` 及通常的中间版本不创建 GitHub Release。

已推送的 Tag 不得移动或强制覆盖。版本发布后发现问题，应修复并增加 Patch 版本，例如从 `v0.1.0` 增加到 `v0.1.1`。

## 紧急修复

已打 Tag 的 `main` 版本出现严重问题时，从最新 `main` 创建短期 Hotfix 分支：

```powershell
git switch main
git pull --ff-only origin main
git switch -c hotfix/v0.1.1
```

修复和测试后通过 PR 合并到 `main`，由组长创建 Patch Tag；同时必须通过 PR 将修复同步回 `develop`，避免后续版本再次出现相同问题。

## 团队规则摘要

1. `main` 只保存稳定里程碑和 Tag。
2. `develop` 用于日常集成。
3. 所有成员从最新 `develop` 创建短期任务分支。
4. 不建立个人永久分支。
5. 一个分支只处理一个明确任务。
6. 所有分支合并均通过 PR；普通任务 PR 合并到 `develop`。
7. 任务合并后删除短期分支。
8. 队友不得直接向 `main` 或 `develop` 提交业务代码。
9. 组长仅可直接处理 `develop` 上极小、低风险的文档或版本修改。
10. Tag 只能由组长在 `main` 的已测试提交上创建。
11. 中间里程碑通常只创建 Tag，不创建 GitHub Release。
12. 已推送 Tag 不得移动；出现问题时增加 Patch 版本。
13. 最终完整版本使用 `v1.0.0`。
