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

## 6. 扩展边界

批量导入题录、批量打标签、删除和附件上传都应另设“输入校验 → 预演 → 显式确认 → 回读验证”的流程。附件上传必须采用官方多阶段上传 API；禁止向桌面数据目录的 `storage` 手动复制文件来模拟上传。

