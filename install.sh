#!/usr/bin/env bash
# AI News Digest 安装脚本：建立 venv、安装依赖、注册 systemd user timer。
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$APP_DIR/.venv"
VENV_PY="$VENV_DIR/bin/python"
CONFIG="$APP_DIR/config/config.yaml"
SYSTEMD_DIR="$HOME/.config/systemd/user"

echo "==> 项目目录：$APP_DIR"

# 1. 配置检查
if [[ ! -f "$CONFIG" ]]; then
  echo "未找到 config/config.yaml，正在从示例复制……"
  cp "$APP_DIR/config/config.example.yaml" "$CONFIG"
  echo "已创建 $CONFIG，请编辑后重新运行 install.sh。"
  exit 1
fi

# 2. 创建 venv 并安装依赖
echo "==> 创建虚拟环境并安装依赖"
python3 -m venv "$VENV_DIR"
"$VENV_PY" -m pip install --upgrade pip >/dev/null
"$VENV_PY" -m pip install -r "$APP_DIR/requirements.txt"

# 3. 读取 schedule.time（HH:MM），转为 OnCalendar 用的 HH:MM:00
RUN_TIME="$("$VENV_PY" - "$CONFIG" <<'PY'
import sys, yaml
with open(sys.argv[1], encoding="utf-8") as f:
    cfg = yaml.safe_load(f) or {}
t = (cfg.get("schedule", {}) or {}).get("time", "08:00")
parts = t.split(":")
hh, mm = parts[0], parts[1] if len(parts) > 1 else "00"
print(f"{int(hh):02d}:{int(mm):02d}:00")
PY
)"
echo "==> 每日触发时间：$RUN_TIME"

# 4. 生成 systemd unit 文件
echo "==> 写入 systemd user unit 到 $SYSTEMD_DIR"
mkdir -p "$SYSTEMD_DIR"
sed -e "s|__APP_DIR__|$APP_DIR|g" -e "s|__VENV_PY__|$VENV_PY|g" \
  "$APP_DIR/newspaper.service.template" > "$SYSTEMD_DIR/newspaper.service"
sed -e "s|__RUN_TIME__|$RUN_TIME|g" \
  "$APP_DIR/newspaper.timer.template" > "$SYSTEMD_DIR/newspaper.timer"

# 5. 允许未登录时触发
if command -v loginctl >/dev/null 2>&1; then
  echo "==> 启用 linger（允许未登录时运行）"
  loginctl enable-linger "$USER" || echo "（linger 启用失败，可手动 sudo loginctl enable-linger $USER）"
fi

# 6. 启用 timer
echo "==> 启用并启动 timer"
systemctl --user daemon-reload
systemctl --user enable --now newspaper.timer

echo
echo "安装完成。常用命令："
echo "  systemctl --user list-timers newspaper.timer   # 查看下次触发时间"
echo "  systemctl --user start newspaper.service        # 立即手动跑一次"
echo "  journalctl --user -u newspaper.service -f       # 查看运行日志"
echo "  $VENV_PY $APP_DIR/run.py -v                     # 前台调试运行"
