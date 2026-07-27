# Contributing to SellPilot

感谢参与 SellPilot。当前项目处于 **Phase 1 / Project Initialization**，请保持变更与当前阶段及既定边界一致。

## 开始前

提交变更前，请阅读：

- `README.md`
- `AGENTS.md`
- `docs/requirements/README.md`
- `docs/architecture/README.md`
- `docs/git-workflow.md`

不得把计划能力描述为已实现，不得暗示已接入真实 Shopee。

## 分支

- `main`：稳定发布分支。
- `develop`：日常集成分支。
- `feature/<简短功能名>`：新功能开发。
- `fix/<简短问题名>`：问题修复。
- `docs/<简短文档名>`：文档变更。
- `release/v<版本号>`：发布准备。

禁止直接向 `main` 提交业务开发代码。功能分支必须从最新 `develop` 创建，并通过 Pull Request 合并到 `develop`。发布版本由 `develop` 合并到 `main`。

## 提交信息

使用以下提交类型：

- `feat:`
- `fix:`
- `docs:`
- `refactor:`
- `test:`
- `chore:`
- `build:`
- `ci:`

一个提交只处理一个明确主题。提交信息应说明变更意图，避免混入无关修改。

## Pull Request

Pull Request 应说明变更、关联任务、测试情况、风险与影响，并完成模板中的检查清单。新增功能必须包含必要测试和相关文档更新。

## 安全与仓库卫生

不提交生成物、缓存、虚拟环境、`node_modules`、本地数据库、`.env`、密钥、API Key、Token、密码或真实用户数据。日志、截图和示例必须脱敏。
