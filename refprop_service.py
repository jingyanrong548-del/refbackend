"""
REFPROP 热力学计算服务
封装 ctREFPROP 调用，支持纯工质和混合工质
"""
import os
from typing import List, Optional, Tuple

# REFPROP 错误码：-9999980, -9999990 等表示两相区未定义的属性
REFPROP_UNDEFINED = -9999970
REFPROP_2PHASE_CP_W = -9999980
REFPROP_2PHASE_CV = -9999990


def parse_fluid_string(fluid_string: str) -> Tuple[str, List[float]]:
    """
    解析工质字符串，支持多种格式：
    
    1. 纯工质: "R32", "R1234ZE", "Water"
    2. 混合工质 REFPROP 格式: "R32*R125" (需配合 SETFLUIDS 后传入 z)
    3. 混合工质自定义格式: "R32&R125|0.5&0.5" (组分用&分隔，比例用|分隔，比例用&分隔)
       - 摩尔分数: "R32&R125|0.5&0.5"
       - 质量分数: "R32&R125|0.5&0.5" (可通过 iMass 区分，默认摩尔)
    
    Returns:
        (fluid_refprop_str, z_array): REFPROP 可用的流体字符串和组分数组
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
        
        # 归一化摩尔/质量分数
        total = sum(fracs)
        if total <= 0:
            raise ValueError("组分比例之和必须大于 0")
        z = [f / total for f in fracs]
        
        # REFPROP 混合物格式: "Fluid1*Fluid2"
        refprop_str = "*".join(fluids)
        
        # 补齐到 20 个组分
        z_extended = z + [0.0] * (20 - len(z))
        
        return refprop_str, z_extended
    
    # 格式: "Fluid1*Fluid2" 无比例（需调用方提供 z，此处默认等摩尔）
    if "*" in fluid_string:
        fluids = [f.strip() for f in fluid_string.split("*") if f.strip()]
        n = len(fluids)
        z = [1.0 / n] * n + [0.0] * (20 - n)
        return fluid_string, z
    
    # 纯工质
    return fluid_string, [1.0] + [0.0] * 19


def _is_sentinel(value: float) -> bool:
    """检查是否为 REFPROP 的未定义/错误标记值"""
    return value <= REFPROP_UNDEFINED or value == REFPROP_2PHASE_CP_W or value == REFPROP_2PHASE_CV


def _clean_value(value: float) -> Optional[float]:
    """将 REFPROP 标记值转换为 None"""
    if _is_sentinel(value):
        return None
    return value


def calculate_properties(
    fluid_string: str,
    input_type: str,
    value1: float,
    value2: float,
    rpprefix: Optional[str] = None,
) -> dict:
    """
    计算热力学性质（ctREFPROP 直连）。
    建议使用 refprop_engine.calculate_properties。
    """
    if rpprefix is None:
        from config import RPPREFIX
        rpprefix = RPPREFIX
    
    if not rpprefix or not os.path.isdir(rpprefix):
        raise RuntimeError(
            f"REFPROP 路径未配置或无效: {rpprefix}。请设置 RPPREFIX 环境变量。"
        )
    
    from ctREFPROP.ctREFPROP import REFPROPFunctionLibrary
    
    RP = REFPROPFunctionLibrary(rpprefix)
    RP.SETPATHdll(rpprefix)
    
    # 摩尔基 SI 单位
    MOLAR_BASE_SI = RP.GETENUMdll(0, "MOLAR BASE SI").iEnum
    
    # 解析工质
    refprop_fluid, z = parse_fluid_string(fluid_string)
    
    # 请求的输出: T, P, D, H, S, Qmole, CP, CV, W
    h_out = "T;P;D;H;S;Qmole;CP;CV;W"
    
    # 输入类型转为大写
    h_in = input_type.upper().strip()
    if len(h_in) != 2:
        raise ValueError(
            f"input_type 必须为两个字符，如 PT, PQ, PH。当前: {input_type}"
        )
    
    # iMass=0 摩尔基, iFlag=0 默认
    r = RP.REFPROPdll(
        refprop_fluid,
        h_in,
        h_out,
        MOLAR_BASE_SI,
        0,  # iMass: 摩尔基
        0,  # iFlag
        value1,
        value2,
        z,
    )
    
    if r.ierr > 100:
        raise RuntimeError(f"REFPROP 计算错误 (ierr={r.ierr}): {r.herr.strip()}")
    
    # 输出顺序: T, P, D, H, S, Qmole, CP, CV, W
    outputs = list(r.Output[:9])
    
    result = {
        "T": _clean_value(outputs[0]),   # K
        "P": _clean_value(outputs[1]),   # kPa
        "D": _clean_value(outputs[2]),   # mol/dm³
        "H": _clean_value(outputs[3]),   # J/mol
        "S": _clean_value(outputs[4]),   # J/(mol·K)
        "Q": _clean_value(outputs[5]),   # 干度 (摩尔基)
        "CP": _clean_value(outputs[6]),  # J/(mol·K)
        "CV": _clean_value(outputs[7]),  # J/(mol·K)
        "W": _clean_value(outputs[8]),   # m/s
    }
    
    return result
