"""
工质参考属性引擎
获取制冷剂的安全类别、GWP、ODP、临界温度、标准沸点、CAS、三相点、分子量、k值
基于 REFPROP 10.0 REFPROPdll / ALLPROPSdll
"""
import os
from typing import Any, Dict, List, Optional

from config import FLUIDS_PATH, RPPREFIX
from refprop_engine import KPA_TO_PA, parse_fluid_string

# REFPROP 未定义标记
REFPROP_UNDEFINED = -9999970


def _get_rp_instance(rpprefix: Optional[str] = None):
    """创建并配置 REFPROP 实例"""
    prefix = rpprefix or RPPREFIX
    fluids = FLUIDS_PATH or prefix
    if not prefix or not os.path.isdir(prefix):
        raise RuntimeError(
            f"REFPROP 路径未配置或无效: {prefix}。请设置 RPPREFIX 环境变量。"
        )
    from ctREFPROP.ctREFPROP import REFPROPFunctionLibrary

    RP = REFPROPFunctionLibrary(prefix)
    RP.SETPATHdll(fluids)
    return RP


def _clean_num(value: float) -> Optional[float]:
    """将 REFPROP 哨兵值转为 None"""
    if value is None or (isinstance(value, (int, float)) and value <= REFPROP_UNDEFINED):
        return None
    return float(value)


def _get_info_string(RP, refprop_fluid: str, z: List[float], h_out: str) -> Optional[str]:
    """
    通过 REFPROPdll 获取字符串类 INFO（SAFETY, CAS# 等）
    REFPROP 2dll/1dll 文档：ierr=0 时，hUnits 字符串通过 herr 返回
    """
    MOLAR_BASE_SI = RP.GETENUMdll(0, "MOLAR BASE SI").iEnum
    r = RP.REFPROPdll(
        refprop_fluid,
        "CRIT",  # hIn: 临界点（作为有效输入以获取流体信息）
        h_out,
        MOLAR_BASE_SI,
        0,
        0,
        0.0,
        0.0,
        list(z),
    )
    if r.ierr > 100:
        return None
    # ierr=0 时，字符串输出在 hUnits 或 herr 中（REFPROP 文档：hUnits sent back in herr）
    s = getattr(r, "hUnits", None) or getattr(r, "herr", None) or ""
    if s and isinstance(s, str) and s.strip():
        return s.strip()
    return None


def _get_info_number(RP, refprop_fluid: str, z: List[float], h_out: str, i_flag: int = 0) -> Optional[float]:
    """通过 REFPROPdll 获取数值类 INFO（GWP, ODP 等）"""
    MOLAR_BASE_SI = RP.GETENUMdll(0, "MOLAR BASE SI").iEnum
    r = RP.REFPROPdll(
        refprop_fluid,
        "CRIT",
        h_out,
        MOLAR_BASE_SI,
        0,
        i_flag,
        0.0,
        0.0,
        list(z),
    )
    if r.ierr > 100:
        return None
    if not r.Output:
        return None
    return _clean_num(float(r.Output[0]))


def _get_crit_and_mix_setup(
    RP, refprop_fluid: str, z: List[float], is_mixture: bool
) -> tuple:
    """获取临界点并（混合物）调用 SATSPLN"""
    MOLAR_BASE_SI = RP.GETENUMdll(0, "MOLAR BASE SI").iEnum
    i_flag = 1 if is_mixture else 0
    r = RP.REFPROPdll(
        refprop_fluid,
        "CRIT",
        "T;P;H;M",
        MOLAR_BASE_SI,
        0,
        i_flag,
        0.0,
        0.0,
        list(z),
    )
    if r.ierr > 100:
        raise RuntimeError(f"REFPROP 获取临界点失败 (ierr={r.ierr}): {r.herr.strip()}")
    tc = float(r.Output[0])
    pc_pa = float(r.Output[1])
    hc = float(r.Output[2])
    mol_mass = _clean_num(float(r.Output[3])) if len(r.Output) > 3 else None
    return tc, pc_pa / KPA_TO_PA, hc, mol_mass


def _get_nbp(RP, refprop_fluid: str, z: List[float]) -> Optional[float]:
    """标准沸点：P=101.325 kPa 下的饱和气相温度"""
    MOLAR_BASE_SI = RP.GETENUMdll(0, "MOLAR BASE SI").iEnum
    p_kpa = 101.325
    r = RP.REFPROPdll(
        refprop_fluid,
        "PQ",
        "T",
        MOLAR_BASE_SI,
        0,
        0,
        p_kpa * KPA_TO_PA,
        1.0,  # 饱和气
        list(z),
    )
    if r.ierr > 100:
        return None
    return _clean_num(float(r.Output[0]))


def _get_triple_point(RP, refprop_fluid: str, z: List[float]) -> Dict[str, Optional[float]]:
    """三相点 T, P（若存在）"""
    MOLAR_BASE_SI = RP.GETENUMdll(0, "MOLAR BASE SI").iEnum
    r = RP.REFPROPdll(
        refprop_fluid,
        "TRIP",
        "T;P",
        MOLAR_BASE_SI,
        0,
        0,
        0.0,
        0.0,
        list(z),
    )
    if r.ierr > 100:
        return {"T": None, "P": None}
    t = _clean_num(float(r.Output[0]))
    p_raw = _clean_num(float(r.Output[1])) if len(r.Output) > 1 else None
    p = round(p_raw / KPA_TO_PA, 8) if p_raw is not None else None
    t_out = round(t, 4) if t is not None else None
    return {"T": t_out, "P": p}


def _get_k_value(RP, refprop_fluid: str, z: List[float]) -> Optional[float]:
    """
    k 值 = CP/CV（绝热指数）
    参考状态：101.325 kPa, 298.15 K（常温常压气相）
    """
    MOLAR_BASE_SI = RP.GETENUMdll(0, "MOLAR BASE SI").iEnum
    r = RP.REFPROPdll(
        refprop_fluid,
        "TP",
        "CP;CV",
        MOLAR_BASE_SI,
        0,
        0,
        101.325 * KPA_TO_PA,
        298.15,
        list(z),
    )
    if r.ierr > 100:
        return None
    cp = _clean_num(float(r.Output[0])) if len(r.Output) > 0 else None
    cv = _clean_num(float(r.Output[1])) if len(r.Output) > 1 else None
    if cp is not None and cv is not None and cv > 0:
        return round(cp / cv, 6)
    return None


def get_fluid_info(
    fluid_string: str,
    rpprefix: Optional[str] = None,
) -> Dict[str, Any]:
    """
    获取工质参考属性
    
    Args:
        fluid_string: 工质字符串，如 "R32", "R32&R125|0.5&0.5"
        rpprefix: REFPROP 路径
    
    Returns:
        {
            "safety_class": str | null,      # ASHRAE 34 安全类别
            "gwp": float | null,             # 全球变暖潜能值
            "odp": float | null,             # 臭氧消耗潜能
            "critical_temperature": float | null,  # 临界温度 [K]
            "normal_boiling_point": float | null,  # 标准沸点 [K]
            "cas_number": str | null,        # CAS 编号
            "triple_point": {"T": K, "P": kPa} | null,  # 三相点
            "molecular_weight": float | null,  # 分子量 [g/mol]
            "k_value": float | null,         # 绝热指数 CP/CV（101.325 kPa, 298.15 K）
        }
    """
    refprop_fluid, z = parse_fluid_string(fluid_string)
    is_mixture = "*" in refprop_fluid

    RP = _get_rp_instance(rpprefix)

    # 1. 临界点 + 分子量
    try:
        tc, pc, hc, mol_mass = _get_crit_and_mix_setup(RP, refprop_fluid, z, is_mixture)
    except RuntimeError:
        raise

    # 2. 标准沸点
    nbp = _get_nbp(RP, refprop_fluid, z)

    # 3. 三相点
    triple = _get_triple_point(RP, refprop_fluid, z)
    triple_point = triple if (triple["T"] is not None or triple["P"] is not None) else None

    # 4. k 值
    k_val = _get_k_value(RP, refprop_fluid, z)

    # 5. 纯工质才从流体文件获取 GWP/ODP/SAFETY/CAS
    safety_class = None
    gwp = None
    odp = None
    cas_number = None
    if not is_mixture:
        safety_class = _get_info_string(RP, refprop_fluid, z, "SAFETY")
        gwp = _get_info_number(RP, refprop_fluid, z, "GWP")
        odp_raw = _get_info_number(RP, refprop_fluid, z, "ODP")
        # REFPROP 流体文件用 ODP=-1 表示“零/不消耗臭氧”，需转为 0
        odp = 0.0 if (odp_raw is not None and odp_raw < 0) else odp_raw
        cas_number = _get_info_string(RP, refprop_fluid, z, "CAS#")
        if mol_mass is None:
            mol_mass = _get_info_number(RP, refprop_fluid, z, "M")

    # 混合物分子量：临界点调用已返回 M，若为空则用 INFO 补充
    if mol_mass is None:
        mol_mass = _get_info_number(RP, refprop_fluid, z, "M", i_flag=1 if is_mixture else 0)

    # REFPROP MOLAR_BASE_SI 返回分子量 [kg/mol]，API 约定为 [g/mol]，需乘以 1000
    if mol_mass is not None and mol_mass < 10:
        mol_mass = mol_mass * 1000.0

    return {
        "safety_class": safety_class,
        "gwp": round(gwp, 4) if gwp is not None else None,
        "odp": round(odp, 6) if odp is not None else None,
        "critical_temperature": round(tc, 4) if tc is not None else None,
        "normal_boiling_point": round(nbp, 4) if nbp is not None else None,
        "cas_number": cas_number,
        "triple_point": triple_point,
        "molecular_weight": round(mol_mass, 4) if mol_mass is not None else None,
        "k_value": k_val,
    }
