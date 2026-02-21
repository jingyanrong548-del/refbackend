#!/bin/bash
# 将本地 REFPROP AddIns 中的 FLUIDS、MIXTURES、FORTRAN 同步到阿里云服务器
# 使用前：1. 修改下方变量  2. 确保 SSH 免密登录已配置

# ============ 配置（请按实际修改）============
SSH_HOST="${ALIYUN_HOST:-ref.jingyanrong.com}"   # 或填 IP，如 123.45.67.89
SSH_USER="${ALIYUN_USER:-root}"
SSH_PORT="${SSH_PORT:-22}"
LOCAL_ADDINS="/Users/jingyanrong/Downloads/NIST Refprop10.0/NIST Refprop10.0/AddIns"
SERVER_RPPREFIX="/www/refprop/Refprop10.0"
# =============================================

set -e

echo ">>> 本地源目录: $LOCAL_ADDINS"
echo ">>> 服务器目标: $SSH_USER@$SSH_HOST:$SERVER_RPPREFIX"
echo ""

# 1. 删除服务器上的旧文件（FLUIDS、MIXTURES、FORTRAN）
echo ">>> 步骤 1/2：删除服务器上的旧 FLUIDS、MIXTURES、FORTRAN..."
ssh -p "$SSH_PORT" "$SSH_USER@$SSH_HOST" "rm -rf $SERVER_RPPREFIX/FLUIDS $SERVER_RPPREFIX/MIXTURES $SERVER_RPPREFIX/FORTRAN"
echo "    已删除"
echo ""

# 2. 上传新的 3 个文件夹
echo ">>> 步骤 2/2：上传新的 FLUIDS、MIXTURES、FORTRAN..."
for dir in FLUIDS MIXTURES FORTRAN; do
  if [ -d "$LOCAL_ADDINS/$dir" ]; then
    echo "    上传 $dir ..."
    scp -P "$SSH_PORT" -r "$LOCAL_ADDINS/$dir" "$SSH_USER@$SSH_HOST:$SERVER_RPPREFIX/"
  else
    echo "    跳过 $dir（本地不存在: $LOCAL_ADDINS/$dir）"
  fi
done

echo ""
echo ">>> 完成。如需重启 refbackend 服务："
echo "    ssh $SSH_USER@$SSH_HOST 'sudo systemctl restart refbackend'"
