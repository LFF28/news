#!/usr/bin/env python3
"""AI News Digest 命令行入口。

直接运行即跑一遍完整流水线后退出（systemd timer 调用的就是它）。
  python run.py        跑一遍
  python run.py -v     跑一遍并打印每个中间单元的输出
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from newspaper.main import run  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="AI News Digest 服务")
    parser.add_argument("-v", "--verbose", action="store_true", help="打印每个中间单元的输出")
    parser.add_argument("-c", "--config", default=None, help="指定配置文件路径")
    args = parser.parse_args()
    sys.exit(run(verbose=args.verbose, config_path=args.config))


if __name__ == "__main__":
    main()
