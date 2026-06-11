#!/usr/bin/env bash
# 卸载 AI News Digest 的 systemd user timer 与 service。
set -euo pipefail

SYSTEMD_DIR="$HOME/.config/systemd/user"

echo "==> 停止并禁用 timer"
systemctl --user disable --now newspaper.timer 2>/dev/null || true
systemctl --user stop newspaper.service 2>/dev/null || true

echo "==> 删除 unit 文件"
rm -f "$SYSTEMD_DIR/newspaper.timer" "$SYSTEMD_DIR/newspaper.service"

systemctl --user daemon-reload
echo "卸载完成。（.venv 与 config 保留，可手动删除）"
