"""
REFPROP 热力学计算 API 配置
使用 python-dotenv 读取 .env，支持多域 CORS、API Key、REFPROP 路径等
"""
import os
from typing import List

from dotenv import load_dotenv

# 优先加载项目根目录下的 .env 文件
load_dotenv()

# ============== CORS 多域支持 ==============
# 允许的跨域来源，逗号分隔。例如：https://reffrontend.jingyanrong.com,https://jingyanrong.com,http://localhost:5173
_allowed = os.environ.get("ALLOWED_ORIGINS", "").strip()
ALLOWED_ORIGINS: List[str] = (
    [o.strip() for o in _allowed.split(",") if o.strip()]
    if _allowed
    else ["*"]  # 未配置时默认允许所有来源（生产环境务必显式配置）
)

# ============== API Key 鉴权（安全护城河）==============
# 公网防护：所有 /calculate 请求必须携带正确的 X-API-Key
SECRET_API_KEY: str = os.environ.get("SECRET_API_KEY", "").strip()

# ============== REFPROP 路径配置 ==============
# REFPROP 安装根目录，需含 librefprop.so 和 FLUIDS 文件夹
# 阿里云服务器安装位置：/www/refprop/Refprop10.0
_default = os.path.join(os.path.dirname(__file__), "REFPROP")
_server = "/www/refprop/Refprop10.0"
RPPREFIX: str = (
    os.environ.get("RPPREFIX") or (_server if os.path.isdir(_server) else _default)
)

# FLUIDS 路径（可选，若与 RPPREFIX 同目录可留空）
# 某些部署下 FLUIDS 可能单独放置
FLUIDS_PATH: str = os.environ.get("FLUIDS_PATH", "").strip() or RPPREFIX
