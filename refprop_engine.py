"""
REFPROP 核心计算引擎
封装 ctREFPROP 调用，支持纯工质与混合工质，环境变量配置 .so 与 FLUIDS 路径

单位制：API 接口遵循 NIST REFPROP 官方 DEFAULT 单位制（iUnits=0）：
  - T [K], P [kPa], D [mol/dm³], H [J/mol], S [J/(mol·K)], Q [-], CP/CV [J/(mol·K)], W [m/s]
内部使用 MOLAR BASE SI（Pa, mol/m³）调用 REFPROP，在边界做单位转换。
"""
import os
from typing import List, Optional, Tuple

from config import FLUIDS_PATH, RPPREFIX

# REFPROP 错误码：特定哨兵值表示两相区未定义的属性
REFPROP_UNDEFINED = -9999970
REFPROP_2PHASE_CP_W = -9999980
REFPROP_2PHASE_CV = -9999990

# REFPROP DEFAULT 与 MOLAR BASE SI 单位换算
# DEFAULT: P [kPa], D [mol/dm³]  |  MOLAR BASE SI: P [Pa], D [mol/m³]
KPA_TO_PA = 1000.0
MOL_DM3_TO_MOL_M3 = 1000.0  # 1 mol/dm³ = 1000 mol/m³


def parse_fluid_string(fluid_string: str) -> Tuple[str, List[float]]:
    """
    解析工质字符串，支持纯工质与混合工质
    
    1. 纯工质: "R32", "R1234ZE", "Water"
    2. 混合工质 REFPROP 格式: "R32*R125"（无比例时默认等摩尔）
    3. 混合工质自定义格式: "R32&R125|0.5&0.5"（组分用 & 分隔，比例用 | 分隔）
       - 摩尔分数示例: "R32&R125|0.5&0.5"
    
    Returns:
        (fluid_refprop_str, z_array): REFPROP 可用的流体字符串和组分摩尔分数数组（20 维）
    """
    fluid_string = fluid_string.strip()
    
    # 格式: "Fluid1&Fluid2|frac1&frac2"
    if "|" in fluid_string:
        parts = fluid_string.split("|", 1)
        fluids_part = parts[0].strip()
        fracs_part = parts[1].strip()
        
        fluids = [f.strip() for f in fluids_part.split("&") if f.strip()]
        fracs_str = [f.strip() for f in fracs_part.split("&") if f.strip()]
        fracs = [float(f) for f in fracs_str]
        
        if len(fluids) != len(fracs):
            raise ValueError(
                f"组分数量与比例数量不匹配: {len(fluids)} 个组分 vs {len(fracs)} 个比例"
            )
        
        total = sum(fracs)
        if total <= 0:
            raise ValueError("组分比例之和必须大于 0")
        z = [f / total for f in fracs]
        z_extended = z + [0.0] * (20 - len(z))
        refprop_str = "*".join(fluids)
        return refprop_str, z_extended
    
    # 格式: "Fluid1*Fluid2" 无比例，默认等摩尔
    if "*" in fluid_string:
        fluids = [f.strip() for f in fluid_string.split("*") if f.strip()]
        n = len(fluids)
        z = [1.0 / n] * n + [0.0] * (20 - n)
        return fluid_string, z
    
    # 纯工质
    return fluid_string, [1.0] + [0.0] * 19


def _is_sentinel(value: float) -> bool:
    """检查是否为 REFPROP 的未定义/错误标记值"""
    return (
        value <= REFPROP_UNDEFINED
        or value == REFPROP_2PHASE_CP_W
        or value == REFPROP_2PHASE_CV
    )


def _clean_value(value: float) -> Optional[float]:
    """将 REFPROP 标记值转换为 None，便于 JSON 序列化"""
    if _is_sentinel(value):
        return None
    return value


def calculate_properties(
    fluid_string: str,
    input_type: str,
    value1: float,
    value2: float,
    rpprefix: Optional[str] = None,
    fluids_path: Optional[str] = None,
) -> dict:
    """
    通用热力学性质计算函数（ctREFPROP 直连）
    
    Args:
        fluid_string: 工质字符串，如 "R32" 或 "R32&R125|0.5&0.5"
        input_type: 输入类型，如 PT/PQ/PH/TD/TQ/PS 等
        value1: 第一个输入参数
        value2: 第二个输入参数
        rpprefix: REFPROP 安装路径（含 librefprop.so）
        fluids_path: FLUIDS 文件夹路径，默认与 rpprefix 相同
    
    Returns:
        包含 T, P, D, H, S, Q, CP, CV, W 的字典
    """
    # 使用环境变量配置的路径
    prefix = rpprefix or RPPREFIX
    fluids = fluids_path or FLUIDS_PATH or prefix

    if not prefix or not os.path.isdir(prefix):
        raise RuntimeError(
            f"REFPROP 路径未配置或无效: {prefix}。请设置 RPPREFIX 环境变量。"
        )

    from ctREFPROP.ctREFPROP import REFPROPFunctionLibrary

    # 实例化 REFPROP 库，传入包含 librefprop.so 的目录
    RP = REFPROPFunctionLibrary(prefix)
    RP.SETPATHdll(fluids)

    # 摩尔基 SI 单位
    MOLAR_BASE_SI = RP.GETENUMdll(0, "MOLAR BASE SI").iEnum

    refprop_fluid, z = parse_fluid_string(fluid_string)
    h_out = "T;P;D;H;S;Qmole;CP;CV;W"
    h_in = input_type.upper().strip()

    if len(h_in) != 2:
        raise ValueError(
            f"input_type 必须为两个字符，如 PT/PQ/PH。当前: {input_type}"
        )

    # API 使用 DEFAULT 单位 (kPa, mol/dm³)，REFPROP 内部用 MOLAR BASE SI (Pa, mol/m³)
    # 输入压力：kPa -> Pa
    v1, v2 = float(value1), float(value2)
    if h_in[0] == "P":
        v1 *= KPA_TO_PA
    if h_in[1] == "P":
        v2 *= KPA_TO_PA
    # 输入密度：mol/dm³ -> mol/m³（若输入类型含 D）
    if h_in[0] == "D":
        v1 *= MOL_DM3_TO_MOL_M3
    if h_in[1] == "D":
        v2 *= MOL_DM3_TO_MOL_M3

    # REFPROPdll: 输入类型、输出字符串、单位、iMass、iFlag、value1、value2、z
    r = RP.REFPROPdll(
        refprop_fluid,
        h_in,
        h_out,
        MOLAR_BASE_SI,
        0,  # iMass: 0 摩尔基
        0,  # iFlag
        v1,
        v2,
        z,
    )

    # 严谨的 herr 错误捕获
    if r.ierr > 100:
        raise RuntimeError(
            f"REFPROP 计算错误 (ierr={r.ierr}): {r.herr.strip()}"
        )

    outputs = list(r.Output[:9])
    # 输出单位转换：P Pa->kPa, D mol/m³->mol/dm³（与 REFPROP DEFAULT 一致）
    p_val = _clean_value(outputs[1])
    d_val = _clean_value(outputs[2])
    return {
        "T": _clean_value(outputs[0]),
        "P": (p_val / KPA_TO_PA) if p_val is not None else None,
        "D": (d_val / MOL_DM3_TO_MOL_M3) if d_val is not None else None,
        "H": _clean_value(outputs[3]),
        "S": _clean_value(outputs[4]),
        "Q": _clean_value(outputs[5]),
        "CP": _clean_value(outputs[6]),
        "CV": _clean_value(outputs[7]),
        "W": _clean_value(outputs[8]),
    }
