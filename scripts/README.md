# Scripts

本目录保存可复用的演示初始化和发布检查脚本。所有脚本都从仓库根目录定位文件，
不内嵌密码、API Key 或本机绝对路径。

## Demo 初始化

```powershell
.\scripts\init-demo.ps1 -AdminUsername admin
```

脚本会升级 PostgreSQL、在没有管理员时交互式创建管理员，并幂等导入 Mock 商业数据。
需要同时导入仓库内的 Mock 知识文档时使用 `-IncludeKnowledge`。管理员密码仅在后端 CLI
的隐藏提示中输入，不会写入参数、日志或脚本。

## 就绪检查

后端运行后执行：

```powershell
.\scripts\check-demo-readiness.ps1
```

知识数据缺失会明确标记 `BLOCKED_RAG_DATA`，但不会把其他已就绪能力判为失败。
发布前要求知识数据也完成时增加 `-RequireKnowledge`。

## API E2E Smoke

```powershell
.\scripts\e2e-smoke.ps1 -Username admin
```

密码通过隐藏提示读取。默认仅执行只读链路；需要验证 Confirmation、取消、确认和重复确认时
显式增加 `-IncludeWrites`。脚本只调用真实 HTTP API，不直接访问数据库。
