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

### 2. 方案 B：Wine REFPROP 后端（做法一）

Wine 后端占 **8002**，refbackend 占 **8003**，域名指向 refbackend：

```bash
export WINE_REFPROP_URL="http://127.0.0.1:8002"
```

在 systemd 的 `refbackend.service` 中可加：`Environment="WINE_REFPROP_URL=http://127.0.0.1:8002"`。  
宝塔中 ref.jingyanrong.com 反向代理目标为：`http://127.0.0.1:8003`。

### 3. 服务器端准备

- 已在服务器上完成首次部署（见下文「阿里云轻量服务器部署」）
- SSH 用户具备 `sudo systemctl restart refbackend` 权限（建议配置免密 sudo）
- 部署路径为 `/www/refprop/refbackend`。部署时会自动安装/更新 `refbackend.service`，无需手动配置

### 4. 免密 sudo 配置（可选）

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

### 5. 查看部署结果

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
4. **环境**：`deploy/refbackend.env` 中 `RPPREFIX=/www/refprop/Refprop10.0`，`WINE_REFPROP_URL=` 留空

若尚未编译好 librefprop.so，可运行 `wine_refprop_backend` 作为 8002 后端（同样需要 librefprop.so，与直接使用 ctREFPROP 条件相同）：

```bash
# 编辑 deploy/refbackend.env，设置 WINE_REFPROP_URL=http://127.0.0.1:8002
# 安装并启动 8002 后端
sudo cp deploy/refprop8002.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable refprop8002
sudo systemctl start refprop8002
```

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

## 二、接口说明

部署完成后，API 统一为：

- **POST** `https://ref.jingyanrong.com/calculate`
- **GET** `https://ref.jingyanrong.com/` 健康检查
- **GET** `https://ref.jingyanrong.com/docs` OpenAPI 文档

详见 [API.md](./API.md)。
