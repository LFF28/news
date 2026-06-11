# AI News Digest

本地运行的 AI 新闻摘要服务。每天定时从预设 RSS 源抓取新闻，经时间过滤后交给 Claude Agent 按兴趣关键词整理成 HTML，最后通过 SMTP 发送到指定邮箱。

## 工作流

```
systemd timer (每天 08:00)
        │  唤起
        ▼
  RSSReader  ──►  Filter  ──►  AIAgent  ──►  EmailSender
  (按组抓取)     (近24h+精简)   (claude整理HTML)   (SMTP发送)
```

- **RSSReader**（头单元）：按分组抓取所有 RSS 源，归一化输出分组 JSON。
- **Filter**：只保留最近 N 小时内的新闻，且每条仅留 `title` 与 `contentSnippet`。
- **AIAgent**：调用 `claude --dangerously-skip-permissions -p`，按关键词每组选前 N 条整理成 HTML 并存到本地。
- **EmailSender**（尾单元）：将 HTML 通过 SMTP 发送到配置的收件箱。

每个单元为独立的类，配置参数全部来自 `config/config.yaml`。除头尾单元外都实现 `output()` 方法，配合 `-v` 可查看中间结果。

## 环境要求

- Python 3.12+
- 已安装并登录的 `claude` CLI（`which claude` 确认路径）
- 一个可用的 SMTP 账号（推荐使用应用专用密码）
- Linux + systemd（用于定时；手动运行无需 systemd）

## 安装

```bash
cd newspaper
cp config/config.example.yaml config/config.yaml
# 编辑 config/config.yaml 填写 RSS、关键词、SMTP 等
./install.sh
```

`install.sh` 会：
1. 创建 `.venv` 并安装依赖；
2. 读取 `schedule.time` 写入 systemd timer 的 `OnCalendar`；
3. 安装 `newspaper.service`（oneshot）与 `newspaper.timer` 到 `~/.config/systemd/user/`；
4. 启用 linger（允许未登录时触发）并启动 timer。

> 采用 systemd **user** 服务，无需 sudo，SMTP 密码留在用户目录更安全。
> timer + oneshot 模式：休眠期进程不驻留，零内存占用；到点唤起跑完即退。

## 配置说明（config/config.yaml）

| 字段 | 说明 |
|------|------|
| `schedule.time` | 每日触发时间 `HH:MM`（本地时区）。修改后需重新运行 `./install.sh`。 |
| `sources` | RSS 源分组。键是组名，值是该组 URL 列表，可自由增删分组。 |
| `filter.window_hours` | 保留最近多少小时的新闻（默认 24）。 |
| `ai_agent.claude_bin` | claude 可执行文件绝对路径。 |
| `ai_agent.top_n` | 每组保留新闻条数（默认 10）。 |
| `ai_agent.timeout` | claude 调用超时秒数。 |
| `ai_agent.keywords` | 兴趣关键词列表，用于让 Agent 筛选最相关的内容。 |
| `output.dir` | 生成的 HTML 保存目录。 |
| `email.smtp_host/port` | SMTP 服务器与端口。587→STARTTLS（`use_tls: true`）；465→SSL（`use_tls: false`）。 |
| `email.username/password` | SMTP 登录凭据。建议用应用专用密码。 |
| `email.from_addr / to_addrs` | 发件人与收件人列表。 |
| `email.subject` | 邮件主题，`{date}` 替换为当天日期。 |
| `log.level` | 日志级别 DEBUG/INFO/WARNING/ERROR。 |

## 使用

```bash
# 手动跑一遍完整流水线（systemd timer 调用的也是它）
.venv/bin/python run.py

# 调试：打印每个中间单元的输出（RSS 抓取结果、过滤结果、HTML 路径）
.venv/bin/python run.py -v

# 指定其他配置文件
.venv/bin/python run.py -c /path/to/other.yaml
```

服务管理：

```bash
systemctl --user list-timers newspaper.timer   # 下次触发时间
systemctl --user start newspaper.service        # 立即手动触发一次
journalctl --user -u newspaper.service -f       # 实时日志
./uninstall.sh                                  # 卸载 timer/service
```

## 输出

生成的 HTML 摘要保存在 `output/digest_YYYY-MM-DD.html`，同时作为邮件正文发送。

## 故障排查

- **RSS 抓取失败**：单个源失败只告警、不中断（见日志 WARNING）。某些源可能需要代理或对 UA 敏感。
- **claude 调用失败/超时**：确认 `ai_agent.claude_bin` 路径正确、CLI 已登录；必要时调大 `ai_agent.timeout`。
- **SMTP 认证失败**：检查端口与 `use_tls` 是否匹配（587/STARTTLS、465/SSL），优先使用应用专用密码。
- **timer 不触发**：`systemctl --user list-timers` 确认已激活；若注销后不运行，确认 `loginctl enable-linger $USER` 已生效。
- **修改了触发时间不生效**：`schedule.time` 改完需重新运行 `./install.sh`（会重写 timer）。
