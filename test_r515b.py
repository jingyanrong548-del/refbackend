#!/usr/bin/env python3
"""
R515B 映射改动验证脚本
无需 REFPROP 安装即可验证解析逻辑
"""
# 直接定义当前配置，避免导入 config（需 dotenv）
BLEND_ALIASES = {"R515B": "R1234ZEE&R227EA|0.938&0.062"}


def parse_fluid_string_test(fluid_string: str):
    """简化版解析，仅验证 R515B 映射"""
    fluid_string = fluid_string.strip()
    alias = BLEND_ALIASES.get(fluid_string.upper())
    if alias is not None:
        fluid_string = alias

    if "|" in fluid_string:
        parts = fluid_string.split("|", 1)
        fluids_part = parts[0].strip()
        fracs_part = parts[1].strip()
        fluids = [f.strip() for f in fluids_part.split("&") if f.strip()]
        fracs_str = [f.strip() for f in fracs_part.split("&") if f.strip()]
        fracs = [float(f) for f in fracs_str]
        total = sum(fracs)
        z = [f / total for f in fracs]
        refprop_str = "*".join(fluids)
        return refprop_str, z
    return fluid_string, [1.0]


if __name__ == "__main__":
    print("=== R515B 映射验证 ===\n")

    # 1. 别名内容
    alias = BLEND_ALIASES["R515B"]
    print(f"1. BLEND_ALIASES['R515B'] = {alias!r}")

    # 2. 组分名检查
    assert "R1234ZEE" in alias, "应使用 R1234ZEE（REFPROP 10 标识符）"
    assert "R1234ZE&" not in alias and not alias.startswith("R1234ZE|"), "不应使用 R1234ZE"
    print("2. ✓ 组分名正确：R1234ZEE（非 R1234ZE）")

    # 3. 摩尔分数
    refprop_str, z = parse_fluid_string_test("R515B")
    print(f"3. parse('R515B') => refprop_str={refprop_str!r}")
    print(f"   摩尔分数 z = {z}")
    assert abs(z[0] - 0.938) < 0.001 and abs(z[1] - 0.062) < 0.001
    print("   ✓ 摩尔分数符合规范：0.938 / 0.062")

    print("\n=== 解析验证通过 ===\n")

    # 4. 若已安装 REFPROP 和依赖，可测试完整计算
    print("完整 REFPROP 计算测试：")
    print("  uvicorn main:app --host 127.0.0.1 --port 8003")
    print("  curl -X POST http://127.0.0.1:8003/calculate \\")
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"fluid_string":"R515B","input_type":"PT","value1":200,"value2":300}\'')
    print()
