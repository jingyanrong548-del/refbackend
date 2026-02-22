"""
饱和包络线 (Saturation Dome) 计算引擎
为 P-h 压焓图提供饱和液线 (q=0) 和饱和气线 (q=1) 的坐标点数组

单位：API 遵循 NIST REFPROP DEFAULT 单位制，P [kPa]，H [J/mol]，T [K]。
内部用 MOLAR BASE SI 调用 REFPROP，输出 P 从 Pa 转为 kPa。
"""
import os
from typing import List, Optional, Tuple

from config import FLUIDS_PATH, RPPREFIX
from refprop_engine import KPA_TO_PA, parse_fluid_string


# 扫描参数
T_MIN_FALLBACK = 223.15  # 最低温度 [K]，约 -50°C（若获取三相点失败时使用）
T_CRIT_OFFSET = 0.5      # 临界点前停止的偏移 [K]，避免临界区发散
TARGET_POINTS = 65       # 目标总点数（液线+气线各约一半，保证绘图性能）
LOW_FRAC = 0.75          # 低温区占比（前 75% 用大步长，后 25% 用小步长）


def _get_rp_instance(rpprefix: Optional[str] = None):
    """创建并配置 REFPROP 实例"""
    prefix = rpprefix or RPPREFIX
    fluids = FLUIDS_PATH or prefix
    if not prefix or not os.path.isdir(prefix):
        raise RuntimeError(f"REFPROP 路径未配置或无效: {prefix}。请设置 RPPREFIX 环境变量。")
    from ctREFPROP.ctREFPROP import REFPROPFunctionLibrary
    RP = REFPROPFunctionLibrary(prefix)
    RP.SETPATHdll(fluids)
    return RP


def _get_critical_point(
    RP,
    refprop_fluid: str,
    z: List[float],
    is_mixture: bool,
) -> Tuple[float, float, float]:
    """
    获取临界点 (Tc, Pc, Hc)
    混合物需 iFlag=1 调用 SATSPLN 后临界点才准确
    """
    MOLAR_BASE_SI = RP.GETENUMdll(0, "MOLAR BASE SI").iEnum
    iFlag = 1 if is_mixture else 0  # 混合物必须调 SATSPLN
    r = RP.REFPROPdll(
        refprop_fluid,
        "CRIT",           # hIn: 临界点
        "T;P;H",          # hOut: 温度、压力、焓
        MOLAR_BASE_SI,
        0,                # iMass: 摩尔基
        iFlag,
        0.0,              # a, b: CRIT 时无需输入
        0.0,
        list(z),          # 副本，避免 REFPROP 原地修改 z
    )
    if r.ierr > 100:
        raise RuntimeError(f"获取临界点失败 (ierr={r.ierr}): {r.herr.strip()}")
    Tc, Pc_Pa, Hc = float(r.Output[0]), float(r.Output[1]), float(r.Output[2])
    return Tc, Pc_Pa / KPA_TO_PA, Hc  # P: Pa -> kPa


def _get_eos_min_temperature(RP, refprop_fluid: str, z: List[float]) -> float:
    """获取状态方程最低温度（通常为三相点液相温度）"""
    MOLAR_BASE_SI = RP.GETENUMdll(0, "MOLAR BASE SI").iEnum
    r = RP.REFPROPdll(
        refprop_fluid,
        "EOSMIN",
        "T",
        MOLAR_BASE_SI,
        0,
        0,
        0.0,
        0.0,
        list(z),          # 副本，避免 REFPROP 原地修改 z
    )
    if r.ierr > 100:
        return T_MIN_FALLBACK  # 失败则使用默认最低温度
    return max(float(r.Output[0]), T_MIN_FALLBACK)


def _adaptive_temperatures(t_min: float, t_crit: float, n: int) -> List[float]:
    """
    自适应温度序列：低温区步长大，靠近临界点步长缩小
    前 LOW_FRAC 比例用较疏的点，后 (1-LOW_FRAC) 用较密的点
    """
    t_end = t_crit - T_CRIT_OFFSET
    if t_min >= t_end:
        return [t_min, t_end]
    # 分段：低温区 n_low 点，高温区 n_high 点
    n_high = max(15, int(n * (1 - LOW_FRAC)))
    n_low = n - n_high
    t_mid = t_min + LOW_FRAC * (t_end - t_min)
    temps = []
    for i in range(n_low):
        t = t_min + (t_mid - t_min) * (i / max(n_low - 1, 1))
        temps.append(t)
    for i in range(n_high):
        t = t_mid + (t_end - t_mid) * (i / max(n_high - 1, 1))
        temps.append(t)
    temps.append(t_end)
    return sorted(set(temps))


def _saturation_ph_at_t(
    RP,
    refprop_fluid: str,
    z: List[float],
    t: float,
    quality: float,
) -> Tuple[float, float]:
    """
    在给定温度 T 和干度 q 下计算饱和压力 P 和焓 H
    quality=0 饱和液，quality=1 饱和气
    """
    MOLAR_BASE_SI = RP.GETENUMdll(0, "MOLAR BASE SI").iEnum
    r = RP.REFPROPdll(
        refprop_fluid,
        "TQ",             # hIn: 温度 + 干度
        "P;H",            # hOut: 压力、焓
        MOLAR_BASE_SI,
        0,                # iMass: 摩尔基
        0,
        t,                # a = T
        quality,          # b = Q (0 液线, 1 气线)
        list(z),          # 副本，避免 REFPROP 原地修改 z
    )
    if r.ierr > 100:
        raise RuntimeError(f"REFPROP 饱和计算失败 T={t} q={quality} (ierr={r.ierr}): {r.herr.strip()}")
    P_Pa, H = float(r.Output[0]), float(r.Output[1])
    return P_Pa / KPA_TO_PA, H  # P: Pa -> kPa


def compute_saturation_dome(
    fluid_string: str,
    rpprefix: Optional[str] = None,
) -> dict:
    """
    计算饱和包络线 (P-h Dome) 数据
    
    从最低温度（三相点或 223.15 K）步进到略低于临界温度，
    对每个温度计算饱和液 (q=0) 和饱和气 (q=1) 的 (P, H)，
    供前端绘制 P-h 图。
    
    Args:
        fluid_string: 工质字符串，如 "R32", "CO2", "R32&R125|0.5&0.5"
        rpprefix: REFPROP 路径，默认从配置读取
    
    Returns:
        {
            "liquid": [{"P": kPa, "H": J/mol}, ...],   # 饱和液线
            "vapor":  [{"P": kPa, "H": J/mol}, ...],   # 饱和气线
            "critical": {"T": K, "P": kPa, "H": J/mol}
        }
    """
    refprop_fluid, z = parse_fluid_string(fluid_string)
    is_mixture = "*" in refprop_fluid or "|" in fluid_string

    RP = _get_rp_instance(rpprefix)

    # 1. 获取临界点 (Tc, Pc, Hc)
    Tc, Pc, Hc = _get_critical_point(RP, refprop_fluid, z, is_mixture)

    # 2. 确定扫描范围：最低温度 与 最高温度（略低于 Tc）
    try:
        T_min = _get_eos_min_temperature(RP, refprop_fluid, z)
    except Exception:
        T_min = T_MIN_FALLBACK
    T_max = Tc - T_CRIT_OFFSET
    if T_min >= T_max:
        T_min = max(T_min - 10.0, 200.0)  # 避免范围过窄

    # 3. 自适应温度序列
    temps = _adaptive_temperatures(T_min, Tc, TARGET_POINTS)

    liquid_points: List[dict] = []
    vapor_points: List[dict] = []

    # 4. 双线计算：对每个温度计算饱和液和饱和气
    for Ti in temps:
        try:
            Pl, Hl = _saturation_ph_at_t(RP, refprop_fluid, z, Ti, 0.0)
            liquid_points.append({"P": round(Pl, 6), "H": round(Hl, 2)})
        except (RuntimeError, ValueError) as e:
            # 某点失败则终止液线，以上一成功点作为顶点
            break
        try:
            Pv, Hv = _saturation_ph_at_t(RP, refprop_fluid, z, Ti, 1.0)
            vapor_points.append({"P": round(Pv, 6), "H": round(Hv, 2)})
        except (RuntimeError, ValueError) as e:
            break

    # 5. 液线按 H 升序排列（低温→高温），气线按 H 升序
    liquid_points.sort(key=lambda p: p["H"])
    vapor_points.sort(key=lambda p: p["H"])

    # 6. 可选：在临界点追加顶点（若未因错误提前终止）
    # 临界点液气相合一，P、H 相同，前端可用来闭合 dome
    return {
        "liquid": liquid_points,
        "vapor": vapor_points,
        "critical": {
            "T": round(Tc, 4),
            "P": round(Pc, 6),
            "H": round(Hc, 2),
        },
    }
