# Web API 整理运行手册

本手册面向需要在 Windows 上复现流程的智能体或自动化脚本。它不包含任何真实密钥、论文正文、PDF 或用户条目。

## 1. 环境模型

桌面 Zotero 保存的是本地缓存；本工具操作的是 Zotero 服务端 Web API。两者的关系如下：

```text
人工确认 / 智能体计划
          ↓
本工具（预演 → --apply）
          ↓
Zotero Web API（验证、版本、对象 key）
          ↓
Zotero 正常同步 → 本机桌面端
```

不要把 API 写入和 WebDAV 混为一谈：前者处理收藏夹和题录元数据，后者只同步附件二进制文件。

## 2. 凭据准备

创建一把**专用于自动化**的 Zotero API Key，并把它保存在操作系统凭据管理器、CI secret 或其他受控密钥服务。运行时再注入 `ZOTERO_API_KEY`。不要将密钥写入 `.env` 后提交，也不要通过命令行参数传入。

PowerShell 会话示例：

```powershell
$env:ZOTERO_API_KEY = '<由安全凭据服务提供>'
python zotero_web_api.py verify
```

期望得到用户 ID 和权限布尔值，但输出中绝不应出现密钥本身。

## 3. 创建两层收藏夹：完整示例

假设要在已有父收藏夹下创建一个用于演示的子收藏夹。先列出收藏夹并找到父收藏夹 key：

```powershell
python zotero_web_api.py list-collections
```

然后预演：

```powershell
python zotero_web_api.py create-collection --name '示例-待归档' --parent-key PARENTKEY
```

核对输出后才提交：

```powershell
python zotero_web_api.py create-collection --name '示例-待归档' --parent-key PARENTKEY --apply
```

服务端会返回新对象的 key。再次执行 `list-collections`，确认新收藏夹的 `parentCollection` 等于 `PARENTKEY`。

## 4. 将条目加入收藏夹：完整示例

先从 Zotero 界面、导出记录或 API 读取获得条目 key 和收藏夹 key。不要使用论文标题做模糊匹配。

```powershell
# 预演会显示条目现有 collections 与提交后的集合
python zotero_web_api.py add-to-collection --item-key ITEMKEY --collection-key COLLECTIONKEY

# 确认后才写入；该操作添加归属，不移除原归属
python zotero_web_api.py add-to-collection --item-key ITEMKEY --collection-key COLLECTIONKEY --apply
```

若用户真正想“移动”，必须先得到明确授权，并单独实现“先读取全部归属、再移除指定旧归属”的受控命令；不要把“加入”误当成“移动”。

## 5. 失败处理

| 现象 | 含义 | 正确处理 |
|---|---|---|
| 没有 `ZOTERO_API_KEY` | 运行时没有取得密钥 | 从受控凭据来源注入，勿写入文件 |
| `write_access=false` | Key 仅可读 | 创建一把权限匹配的专用 Key |
| HTTP 412 | 远端对象在读取后被修改 | 重新读取、比较变化、要求确认 |
| 条目或收藏夹找不到 | key 不属于该资料库或已删除 | 回到只读发现步骤，不猜测 key |
| 桌面端没立即显示 | 本机尚未完成账户同步 | 使用 Zotero 正常同步，不改数据库 |

## 5.1 从审核过的 JSON 创建题录

`examples/items-plan.json` 是无版权、可直接复制的最小样例。先检查 `itemType`、题名、作者、日期与 DOI/URL 是否来自可靠来源；不得把下载到的论文正文放入 JSON 或提交到仓库。

```powershell
python zotero_web_api.py create-items --json-file examples/items-plan.json
python zotero_web_api.py create-items --json-file examples/items-plan.json --apply
```

第一条命令仅显示记录数和条目类型。第二条才真正创建。对于新来源，先用一条记录验证题录质量和同步结果，再处理下一批。

## 5.2 删除收藏夹或收藏夹树

删除前必须由用户确认真实 key 与名称。收藏夹删除只移除分类结构，条目仍保留在资料库。

```powershell
# 叶子收藏夹：预演后再执行
python zotero_web_api.py delete-collection --collection-key COLLECTIONKEY
python zotero_web_api.py delete-collection --collection-key COLLECTIONKEY --apply

# 含子收藏夹的树：先查看完整清单，再显式允许递归删除
python zotero_web_api.py delete-collection --collection-key PARENTKEY --recursive
python zotero_web_api.py delete-collection --collection-key PARENTKEY --recursive --apply
```

预演会列出每一个待删 key 和名称；实际执行按子级到父级的顺序处理，并回读验证其均已不存在。

## 6. 扩展边界

批量导入题录、批量打标签、删除和附件上传都应另设“输入校验 → 预演 → 显式确认 → 回读验证”的流程。附件上传必须采用官方多阶段上传 API；禁止向桌面数据目录的 `storage` 手动复制文件来模拟上传。

## 7. Windows 凭据管理器的本机用法

建议把 API Key 保存为 Windows 的“通用凭据”，而不是保存在项目文件中。一个本机脚本或智能体可以在运行时读取该凭据，把值设置给当前 PowerShell 进程的 `ZOTERO_API_KEY`，运行完毕后关闭窗口即可清除该进程内的变量。

操作原则：

1. 凭据名称使用稳定、易识别的名称，例如 `Codex.Zotero.WebAPI`；不要把密钥放进凭据名称。
2. 使用 `verify` 确认权限后再开始整理；不需要附件上传时，不要授予文件权限。
3. 不要在 `echo`、日志、异常消息、截图或项目文件中输出环境变量。
4. 发现泄露时，立即到 Zotero 的 Key 管理页面撤销该 Key，再创建新的专用 Key。

## 8. 供低自主智能体执行的检查表

```text
[ ] 用户明确说明了要创建/归类的范围
[ ] 已执行 verify，写入权限为 true
[ ] 已通过只读命令取得真实 key，而非猜测 key
[ ] 已运行不带 --apply 的预演，且输出与目标一致
[ ] 每个独立变更均得到确认
[ ] 已带 --apply 执行一次写入
[ ] 已回读验证，并让 Zotero 正常同步
[ ] 未输出、复制、提交或上传 API Key
```

如果任一项无法满足，智能体应停在当前步骤并说明缺失的信息；不得用本地 SQLite 直写来绕过验证或同步问题。

