"""
REFPROP 路径与 Wine 后端配置
"""
import os

# REFPROP 安装根目录（需含 librefprop.so 和 FLUIDS）
_default = os.path.join(os.path.dirname(__file__), "REFPROP")
_server = "/www/refprop/Refprop10.0"
RPPREFIX = os.environ.get("RPPREFIX") or (_server if os.path.isdir(_server) else _default)

# Wine REFPROP 后端 URL（方案 B：本机通过 Wine 调 DLL 的后端）
# 默认 http://127.0.0.1:8002；设为空字符串可禁用，改用 ctREFPROP
WINE_REFPROP_URL = os.environ.get(
    "WINE_REFPROP_URL", "http://127.0.0.1:8002"
).strip()
