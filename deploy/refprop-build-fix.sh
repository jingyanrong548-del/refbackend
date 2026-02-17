#!/bin/bash
# REFPROP 10 编译修复：排除导致 multiple definition 的源文件
# 在服务器上执行，需在 cmake 配置之前运行

set -e
CMAKE_FILE="/www/refprop/REFPROP-cmake/CMakeLists.txt"
MARKER="REFPROP_10_EXCLUDE"

if grep -q "$MARKER" "$CMAKE_FILE" 2>/dev/null; then
    echo ">>> 补丁已应用，跳过"
    exit 0
fi

# 在 "# Remove the files COMMONS.FOR" 之前插入排除逻辑
# 定位到 "endif(${REFPROP_SOURCE_AUTOFIX})" 之后
echo ">>> 为 REFPROP 10 修改 CMakeLists.txt..."

# 使用 Python 避免 sed 跨平台差异
python3 << 'PYEOF'
import re

path = "/www/refprop/REFPROP-cmake/CMakeLists.txt"
with open(path) as f:
    content = f.read()

patch = '''
# REFPROP 10: 排除导致 multiple definition 的冗余源文件
set(REFPROP_10_EXCLUDE CORE_DE CORE_MLT CORE_STN CORE_PH0 CORE_CPP CORE_BWR CORE_ECS FLSH_SUB IDEALGAS MIX_AGA8 REALGAS SETUP2 TRNS_ECS TRNS_VIS UTILITY)
foreach(excl ${REFPROP_10_EXCLUDE})
  foreach(src ${APP_SOURCES})
    if("${src}" MATCHES "/${excl}\\\\.FOR$")
      list(REMOVE_ITEM APP_SOURCES "${src}")
    endif()
  endforeach()
endforeach()

'''

# 在 endif(${REFPROP_SOURCE_AUTOFIX}) 和 # Remove the files 之间插入
old = "endif(${REFPROP_SOURCE_AUTOFIX})\n\n# Remove the files COMMONS.FOR"
if old in content:
    content = content.replace(old, "endif(${REFPROP_SOURCE_AUTOFIX})" + patch + "\n# Remove the files COMMONS.FOR")
    with open(path, 'w') as f:
        f.write(content)
    print("补丁应用成功")
else:
    # 备选：在 # Remove the files 行前插入
    content = content.replace("# Remove the files COMMONS.FOR", patch + "# Remove the files COMMONS.FOR")
    with open(path, 'w') as f:
        f.write(content)
    print("补丁应用成功(备选)")
PYEOF

echo ">>> 完成。请重新执行完整构建："
echo "    cd /www/refprop/REFPROP-cmake/build"
echo "    rm -rf *"
echo "    cmake .. -DREFPROP_FORTRAN_PATH=/www/refprop/Refprop10.0/FORTRAN -DCMAKE_BUILD_TYPE=Release"
echo "    cp /www/refprop/Refprop10.0/FORTRAN/*.INC FORTRAN_temp/"
echo "    cmake --build ."
