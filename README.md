# Zotero Web API Organizer

一个以 Zotero 官方 Web API 为唯一写入通道的轻量整理工具。它适用于创建收藏夹、为已有条目添加收藏夹归属，以及导入经人工审核的题录元数据。

## 为什么使用这条路线

Zotero 的本地 SQLite 数据库是桌面端的内部缓存；外部程序直接修改它会绕过校验和同步机制。本项目通过官方 Web API 写入，由服务端生成对象键，并通过版本号和写入令牌处理并发与重试。

## 安全设计

- API Key 仅从环境变量 `ZOTERO_API_KEY` 读取，不接受命令行传参，也不会输出到终端。
- 所有变更命令默认只输出预览；必须额外传入 `--apply` 才会写入。
- 为已有条目添加收藏夹时，会保留其现有收藏夹归属。
- 更新既有对象会携带当前版本；若远端发生变化，工具会停止并要求刷新后复核。
- 本项目不写入 `zotero.sqlite`、`syncCache` 或本地附件目录。

## 使用前准备

1. 在 Zotero 账户页面创建一把权限范围符合任务需要的 API Key。
2. 将 Key 保存到你自己的安全凭据管理器或 CI secret 中，再在运行时注入环境变量 `ZOTERO_API_KEY`。
3. 不要把 Key 写入代码、提交记录、issue、截图或 README。
4. 使用 Python 3.10 或更高版本；本项目仅使用标准库。

Windows PowerShell 示例（只在当前窗口生效）：

```powershell
$env:ZOTERO_API_KEY = '<从安全凭据存储读取的值>'
python zotero_web_api.py verify
```

## 常用命令

```powershell
# 验证 API 可用性及权限（只读）
python zotero_web_api.py verify

# 查看云端收藏夹（只读）
python zotero_web_api.py list-collections

# 先预览创建收藏夹
python zotero_web_api.py create-collection --name '待阅读'

# 确认无误后才实际创建
python zotero_web_api.py create-collection --name '待阅读' --apply

# 将一篇已存在的条目加入指定收藏夹；不会移除已有归属
python zotero_web_api.py add-to-collection --item-key ITEMKEY --collection-key COLLECTIONKEY --apply

# 从已审核的 JSON 题录预演创建；确认后才加 --apply
python zotero_web_api.py create-items --json-file examples/items-plan.json
python zotero_web_api.py create-items --json-file examples/items-plan.json --apply
```

## 下载后即可运行：最短完整流程

本项目没有第三方依赖，也不需要安装 Zotero 插件。下载或克隆后，打开 PowerShell 并进入项目目录：

```powershell
cd <项目下载目录>\zotero-web-api-organizer
python --version
```

然后从你自己的受控凭据来源读取 Key，只给**当前** PowerShell 窗口设置环境变量，再执行验证：

```powershell
$env:ZOTERO_API_KEY = '<从 Windows 凭据管理器或其他密钥服务读取>'
python .\zotero_web_api.py verify
```

只有 `library_access` 和 `write_access` 都为 `true` 时，才可进行整理。下面是一轮可复现的实际会话：

```powershell
# 1. 获取真实的收藏夹 key；将输出保留在本地，供人工核对
python .\zotero_web_api.py list-collections

# 2. 预演创建一个顶层收藏夹——不会写入任何数据
python .\zotero_web_api.py create-collection --name '项目-待整理'

# 3. 人工确认名称后才提交；返回值中包含服务端生成的收藏夹 key
python .\zotero_web_api.py create-collection --name '项目-待整理' --apply

# 4. 若要建立子收藏夹，使用上一步返回的 key；先预演，再带 --apply
python .\zotero_web_api.py create-collection --name '2026-待读' --parent-key COLLECTIONKEY
python .\zotero_web_api.py create-collection --name '2026-待读' --parent-key COLLECTIONKEY --apply

# 5. 将已有条目加入收藏夹；先预演，确认现有归属不会被移除
python .\zotero_web_api.py add-to-collection --item-key ITEMKEY --collection-key COLLECTIONKEY
python .\zotero_web_api.py add-to-collection --item-key ITEMKEY --collection-key COLLECTIONKEY --apply
```

`ITEMKEY` 和 `COLLECTIONKEY` 都是 Zotero 的八位内部标识，不是论文标题、DOI 或收藏夹显示名称。它们应来自 Zotero 界面、已审核的导出结果或 `list-collections` 的只读输出；不得自行编造。

## 本工具实际能做什么

| 目标 | 命令 | 默认行为 | 写入后的验证 |
|---|---|---|---|
| 验证权限 | `verify` | 只读 | 返回资料库、写入、文件权限 |
| 建立顶层/子收藏夹 | `create-collection` | 输出计划 | Zotero 服务端生成 key；再次列出收藏夹可确认层级 |
| 查找云端收藏夹层级 | `list-collections` | 只读 | 直接返回 key、名称和父级 key |
| 为条目增加一个归属 | `add-to-collection` | 输出原归属与新归属计划 | 工具会回读条目并确认归属存在 |
| 从审核后的 JSON 创建题录 | `create-items` | 输出数量与条目类型计划 | 服务端返回每条记录的创建结果 |

这里的“增加归属”与“移动”不同：同一条文献可属于多个收藏夹。该工具不会默认移除任何既有归属，也不会删除条目、附件或收藏夹。

## 使用边界与常见误解

- **Web API 写的是云端资料库**。写入成功后，保持 Zotero 桌面端的普通同步，变化会回到本机。
- **Key 不是密码，也不应成为资料库内容的一部分**。工具只在进程环境变量中读取它；建议从 Windows Credential Manager 临时读入，而不是在 `.env`、脚本或 README 里保存。
- **PDF 不是普通元数据**。本项目不下载受限内容，也不通过复制文件到 `storage` 目录制造附件；合法取得的附件上传必须另行实现官方的多阶段文件上传协议。
- **批量操作先拆小**。建议先对 1–3 个条目完成“预演 → 确认 → 写入 → 回读”，再把同样规则推广到下一批。
- **冲突不覆盖**。HTTP 412 表示远端已经变化；重新读取、比较差异，再决定是否重试。

## 给智能体的完整执行顺序

不熟悉 Zotero 的自动化智能体应严格按以下顺序工作：

1. **确认目标**：区分“创建收藏夹”“把条目额外加入收藏夹”“移动条目”“删除条目”。本工具只实现前两类低风险操作。
2. **验证凭据**：运行 `verify`，确认 `library_access=true`；需要修改时还必须确认 `write_access=true`。
3. **只读发现**：运行 `list-collections`，找到父收藏夹与目标收藏夹的 `key`。不要根据显示名称猜 key。
4. **预演**：每个写入命令先不带 `--apply` 执行，保存其 JSON 预览。若目标、名称或现有归属不对，在此停止。
5. **单次提交**：得到用户明确确认后，用相同参数追加 `--apply`。不要把多项不相关变更拼进一个请求。
6. **回读与同步**：对于条目归类，工具会回读确认；创建后再次运行 `list-collections`。随后让 Zotero 桌面端进行正常同步。
7. **异常停止**：遇到 HTTP 412、权限不足、Key 不存在或项目找不到时，停止并报告；不要直接改 SQLite，也不要伪造对象 key。

更完整的可复现手册见 [docs/agent-runbook.md](docs/agent-runbook.md)，可直接套用的无版权示例见 [examples/collection-plan.json](examples/collection-plan.json) 和 [examples/items-plan.json](examples/items-plan.json)。

## 限制

- PDF 附件上传需要遵循 Zotero 的多阶段文件上传协议，不能通过手改本地 `storage` 目录实现。
- API 写入后，桌面端仍应通过 Zotero 的正常同步完成本地刷新。
- 删除、批量移动和批量元数据覆盖应单独设计预览与确认流程；本项目有意不把这些高风险操作做成默认命令。

## 官方资料

- [Web API 写入请求](https://www.zotero.org/support/dev/web_api/v3/write_requests)
- [Web API 同步](https://www.zotero.org/support/dev/web_api/v3/syncing)
- [Web API 文件上传](https://www.zotero.org/support/dev/web_api/v3/file_upload)

