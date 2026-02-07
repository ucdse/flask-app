#!/usr/bin/env bash
# 在服务器上测试 SMTP 连通性（TCP + TLS/SSL 握手）。
# 用法：bash scripts/test_smtp.sh

set -e

# ---------- 写死配置，按需修改 ----------
MAIL_SERVER="pixel.mxrouting.com"
MAIL_PORT="587"
# ---------------------------------------

echo "=== SMTP 连通性测试 ==="
echo "服务器: $MAIL_SERVER"
echo "端口:   $MAIL_PORT"
echo ""

# 1. TCP 连接
echo -n "[1] TCP 连接 $MAIL_SERVER:$MAIL_PORT ... "
if (echo >/dev/tcp/"$MAIL_SERVER"/"$MAIL_PORT") 2>/dev/null; then
  echo "成功"
else
  # 无 /dev/tcp 时尝试 nc
  if command -v nc &>/dev/null; then
    if nc -z -w5 "$MAIL_SERVER" "$MAIL_PORT" 2>/dev/null; then
      echo "成功"
    else
      echo "失败（端口不可达或超时）"
      exit 1
    fi
  else
    echo "失败（bash 无 /dev/tcp 且未找到 nc）"
    exit 1
  fi
fi

# 2. TLS/SSL 握手
if [[ "$MAIL_PORT" == "465" ]]; then
  echo -n "[2] SSL 握手 (端口 465) ... "
  if echo | timeout 15 openssl s_client -connect "$MAIL_SERVER:$MAIL_PORT" -brief 2>/dev/null | grep -q "Connection established"; then
    echo "成功"
  else
    echo "失败"
    exit 1
  fi
else
  echo -n "[2] STARTTLS 握手 (端口 $MAIL_PORT) ... "
  if echo | timeout 15 openssl s_client -connect "$MAIL_SERVER:$MAIL_PORT" -starttls smtp -brief 2>/dev/null | grep -q "Connection established"; then
    echo "成功"
  else
    echo "失败"
    exit 1
  fi
fi

echo ""
echo "SMTP 连通性测试通过。"
