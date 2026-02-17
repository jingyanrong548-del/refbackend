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

## 一、阿里云轻量服务器部署

### 1. 前置条件

- 阿里云轻量应用服务器（Linux）
- 已安装 REFPROP 10.0（含 REFPRP64.DLL 或 librefprop.so + FLUIDS 文件夹）
- Python 3.10+

### 2. 首次部署

```bash
# SSH 登录服务器后
cd /opt  # 或你选定的目录
sudo git clone https://github.com/jingyanrong/refbackend.git
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
        proxy_pass http://127.0.0.1:8000;
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

### 5. 更新部署（从 GitHub 拉取后重启）

```bash
cd /opt/refbackend
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
