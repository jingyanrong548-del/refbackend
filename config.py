"""
REFPROP 路径配置
请根据你的 REFPROP 10.0 安装路径修改 RPPREFIX
"""
import os

# REFPROP 安装根目录，需包含 REFPRP64.DLL 和 FLUIDS 文件夹
# Windows 默认: C:\\Program Files (x86)\\REFPROP
# macOS/Linux: 通过 REFPROP-cmake 构建后的路径
RPPREFIX = os.environ.get("RPPREFIX", os.path.join(os.path.dirname(__file__), "REFPROP"))
