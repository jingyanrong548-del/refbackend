"""
REFPROP 路径与 Wine 后端配置
"""
import os

# REFPROP 安装根目录（仅在使用 ctREFPROP 即 Linux .so 时需要）
RPPREFIX = os.environ.get("RPPREFIX", os.path.join(os.path.dirname(__file__), "REFPROP"))

# Wine REFPROP 后端 URL（方案 B：本机通过 Wine 调 DLL 的后端）
# 默认 http://127.0.0.1:8002；设为空字符串可禁用，改用 ctREFPROP
WINE_REFPROP_URL = os.environ.get(
    "WINE_REFPROP_URL", "http://127.0.0.1:8002"
).strip()
