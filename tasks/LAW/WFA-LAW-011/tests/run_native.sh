#!/bin/bash
# verifier: 原包 verify.py（仅标准库）在独立镜像中读取 /workspace/submission。
# verify.py 失败（如金标缺失）时 set -e 使脚本非零退出，不写 reward。
set -euo pipefail
mkdir -p /logs/verifier
rm -f /logs/verifier/reward.txt /logs/verifier/reward.json
python3 -I /tests/verify.py /workspace/submission --json /logs/verifier/details.json
python3 -I /tests/reward.py /logs/verifier/details.json

