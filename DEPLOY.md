# REFPROP API 部署指南

## 零、GitHub 同步（首次）

1. 在 GitHub 新建仓库 `refbackend`：<https://github.com/new>
2. 本地推送：

```bash
cd /path/to/refbackend
git remote add origin https://github.com/你的用户名/refbackend.git
git push -u origin main
```

---

## 〇一、自动部署（GitHub Actions）

推送 `main` 分支后，GitHub Actions 会自动 SSH 到阿里云服务器执行 `git pull` 并重启服务。

### 1. 配置 GitHub Secrets

在仓库页：**Settings → Secrets and variables → Actions**，新增 Secrets：

| 名称 | 说明 | 示例 |
|------|------|------|
| `SSH_HOST` | 服务器 IP 或域名 | `123.45.67.89` 或 `ref.jingyanrong.com` |
| `SSH_USER` | SSH 登录用户名 | `root` |
| `SSH_PRIVATE_KEY` | SSH 私钥完整内容（含 `-----BEGIN...` 和 `-----END...`）。对应公钥需已添加到服务器 `~/.ssh/authorized_keys` | 粘贴私钥 |
| `SSH_PORT` | SSH 端口（可选，默认 22） | `22` |

### 2. 服务器端准备

- 已在服务器上完成首次部署（见下文「阿里云轻量服务器部署」）
- SSH 用户具备 `sudo systemctl restart refbackend` 权限（建议配置免密 sudo）
- 部署路径为 `/www/refprop/refbackend`。部署时会自动安装/更新 `refbackend.service`，无需手动配置

### 3. 免密 sudo 配置（可选）

若 SSH 用户执行 `sudo systemctl restart` 时被要求输入密码，可配置免密：

```bash
sudo visudo
# 在文件末尾添加（将 root 换成你的 SSH_USER）：
root ALL=(ALL) NOPASSWD: /bin/cp /www/refprop/refbackend/deploy/refbackend.service /etc/systemd/system/
root ALL=(ALL) NOPASSWD: /bin/systemctl daemon-reload
root ALL=(ALL) NOPASSWD: /bin/systemctl enable refbackend
root ALL=(ALL) NOPASSWD: /bin/systemctl restart refbackend
root ALL=(ALL) NOPASSWD: /bin/systemctl status refbackend
```

### 4. 查看部署结果

推送后到 **Actions** 标签页查看运行日志。

---

## 一、阿里云轻量服务器部署

### 1. 前置条件

- 阿里云轻量应用服务器（Linux）
- **REFPROP 10.0**：Linux 需 `librefprop.so` + `FLUIDS` 文件夹（见下方「REFPROP Linux 库」）
- Python 3.10+

#### REFPROP Linux 库（必须）

ctREFPROP 在 Linux 上需要 `librefprop.so`，不能使用 Windows 的 REFPRP64.DLL。

1. **获取 REFPROP 数据**：从 Windows 安装目录复制 `FLUIDS`、`MIXTURES` 到 `/www/refprop/Refprop10.0/`
2. **编译 librefprop.so**：使用 NIST 官方 [REFPROP-cmake](https://github.com/usnistgov/REFPROP-cmake) 从 Fortran 源码编译
3. **放置**：将生成的 `librefprop.so` 放入 `/www/refprop/Refprop10.0/`，与 FLUIDS 同目录
4. **环境**：`deploy/refbackend.env` 中设置 `RPPREFIX=/www/refprop/Refprop10.0`

### 2. 首次部署

```bash
# SSH 登录服务器后
sudo mkdir -p /www/refprop
cd /www/refprop
sudo git clone https://github.com/jingyanrong548-del/refbackend.git
cd refbackend

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 设置 REFPROP 路径（按实际安装路径修改）
export RPPREFIX="/path/to/REFPROP"
echo 'export RPPREFIX="/path/to/REFPROP"' >> ~/.bashrc
```

### 3. 配置 systemd 服务

将 `deploy/refbackend.service` 复制到 `/etc/systemd/system/` 并修改：

```bash
sudo cp deploy/refbackend.service /etc/systemd/system/
sudo nano /etc/systemd/system/refbackend.service
# 修改 Environment="RPPREFIX=/path/to/REFPROP" 和 WorkingDirectory
sudo systemctl daemon-reload
sudo systemctl enable refbackend
sudo systemctl start refbackend
sudo systemctl status refbackend
```

### 4. 配置 Nginx 反向代理（可选）

若域名 ref.jingyanrong.com 使用 Nginx：

```nginx
server {
    listen 80;
    server_name ref.jingyanrong.com;
    location / {
        proxy_pass http://127.0.0.1:8003;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

启用 HTTPS 可使用 Let's Encrypt：

```bash
sudo certbot --nginx -d ref.jingyanrong.com
```

### 5. 更新部署

- **自动**：推送到 GitHub `main` 分支后，GitHub Actions 会自动部署（需先配置 Secrets）
- **手动**：

```bash
cd /www/refprop/refbackend
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart refbackend
```

或使用脚本：

```bash
./deploy/update.sh
```

---

## 一.5 替换 REFPROP 10 源码与数据（解决 FORTRAN 导致后端不可用）

若后端因旧版 FORTRAN 源码 / `librefprop.so` 无法运行（如 multiple definition 编译错误或运行时崩溃），使用新的 REFPROP 10 源码按以下步骤替换。

### 步骤 1：本地上传新的 FLUIDS、MIXTURES、FORTRAN

在**本地 Mac** 执行，将 AddIns 中新源码上传到服务器（会先删除服务器上的旧文件）：

```bash
cd /path/to/refbackend
./deploy/upload-refprop-data.sh
```

脚本会删除服务器 `/www/refprop/Refprop10.0/` 下的旧 `FLUIDS`、`MIXTURES`、`FORTRAN`，并上传本地 `~/下载/NIST Refprop10.0/.../AddIns/` 中的新文件。首次使用前请修改脚本中的 `LOCAL_ADDINS`、`SSH_HOST`、`SSH_USER`。

### 步骤 2：SSH 登录服务器并准备 REFPROP-cmake

```bash
ssh root@你的服务器

# 若尚未克隆 REFPROP-cmake，则执行：
cd /www/refprop
sudo git clone https://github.com/usnistgov/REFPROP-cmake.git
```

### 步骤 3：应用 REFPROP 10 编译修复（排除 multiple definition）

REFPROP 10 源码与 REFPROP-cmake 存在兼容问题，需排除部分冗余 .FOR 文件。**注意**：`UTILITY` 和 `FLSH_SUB` 必须保留（提供 `xdiv2_`、`dsfl1_` 等运行时必需符号），排除列表为：`CORE_DE`、`CORE_MLT`、`CORE_STN`、`CORE_PH0`、`CORE_CPP`、`CORE_BWR`、`CORE_ECS`、`IDEALGAS`、`MIX_AGA8`、`REALGAS`、`TRNS_ECS`。

```bash
cd /www/refprop/refbackend
sudo bash /www/refprop/refbackend/deploy/refprop-build-fix.sh
```

或手动应用补丁：

```bash
cd /www/refprop/REFPROP-cmake
sudo patch -p1 < /www/refprop/refbackend/deploy/REFPROP-cmake-REFPROP10.patch
```

### 步骤 4：编译生成新的 librefprop.so

```bash
cd /www/refprop/REFPROP-cmake/build
rm -rf *
cmake .. -DREFPROP_FORTRAN_PATH=/www/refprop/Refprop10.0/FORTRAN -DCMAKE_BUILD_TYPE=Release
mkdir -p FORTRAN_temp
cp /www/refprop/Refprop10.0/FORTRAN/*.INC FORTRAN_temp/
cmake --build .
```

### 步骤 5：将 librefprop.so 放入 REFPROP 目录

```bash
# 使用 /bin/cp -f 强制覆盖，避免 cp 别名（如 -i）导致复制失败
/bin/cp -f /www/refprop/REFPROP-cmake/build/librefprop.so /www/refprop/Refprop10.0/
```

### 步骤 6：重启 refbackend 服务

```bash
sudo systemctl restart refbackend
sudo systemctl status refbackend
```

### 步骤 7：验证

访问 `https://ref.jingyanrong.com/` 或调用 `/calculate` 接口，确认后端正常返回。

---

## 二、接口说明

部署完成后，API 统一为：

- **POST** `https://ref.jingyanrong.com/calculate`
- **GET** `https://ref.jingyanrong.com/` 健康检查
- **GET** `https://ref.jingyanrong.com/docs` OpenAPI 文档

详见 [API.md](./API.md)。
