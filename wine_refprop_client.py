"""
Wine REFPROP 后端客户端（方案 B）
请求现有「通过 Wine 调 REFPROP DLL」的后端，按单属性返回的接口聚合为统一响应。
"""
import json
import urllib.error
import urllib.request
from typing import Any, Optional

# Wine 后端常见属性名（按需与对方接口对齐）
PROPERTY_MAP = {
    "T": "temperature",      # K，若后端返回 C 则需 +273.15
    "P": "pressure",         # kPa 或 Pa，需统一
    "D": "density",
    "H": "enthalpy",
    "S": "entropy",
    "Q": "quality",
    "CP": "cp",
    "CV": "cv",
    "W": "speed_of_sound",
}


def _wine_request(
    base_url: str,
    fluid: str,
    temperature_c: float,
    pressure_pa: float,
    property_name: str,
    timeout: float = 10.0,
) -> Optional[float]:
    """
    向 Wine 后端请求单个物性。
    假设后端：POST JSON { fluid, temperature, pressure, property }，返回 { result: { value, unit } }。
    """
    url = base_url.rstrip("/") + "/calculate"
    body = {
        "fluid": fluid,
        "temperature": temperature_c,
        "pressure": pressure_pa,
        "property": property_name,
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            out = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Wine REFPROP 后端请求失败: {e}") from e

    # 兼容多种返回结构
    result = out.get("result") or out
    if isinstance(result, dict) and "value" in result:
        return float(result["value"])
    if "value" in out:
        return float(out["value"])
    raise RuntimeError(f"Wine 后端返回格式无法解析: {out}")


def calculate_via_wine(
    wine_url: str,
    fluid_string: str,
    input_type: str,
    value1: float,
    value2: float,
) -> dict:
    """
    通过 Wine 后端计算物性。当前仅支持 PT（压力-温度）输入。
    value1 = P [kPa], value2 = T [K] -> 转为 Pa 和 °C 请求后端。
    """
    input_type = input_type.upper().strip()
    if input_type != "PT":
        raise ValueError(
            f"Wine 后端当前仅支持 input_type=PT，收到: {input_type}"
        )

    # 纯工质名：取第一段，混合暂用第一个组分名（可按实际后端扩展）
    fluid = fluid_string.strip().split("&")[0].split("|")[0].strip() or "R32"
    pressure_pa = value1 * 1000.0   # kPa -> Pa
    temperature_c = value2 - 273.15  # K -> °C

    result = {}
    for our_key, wine_prop in PROPERTY_MAP.items():
        try:
            val = _wine_request(
                wine_url, fluid, temperature_c, pressure_pa, wine_prop
            )
            result[our_key] = val
        except Exception:
            result[our_key] = None

    # 若后端返回温度为 °C，转 K
    if result.get("T") is not None and result["T"] < 200:
        result["T"] = result["T"] + 273.15
    # 若后端返回压力为 Pa，转 kPa
    if result.get("P") is not None and result["P"] > 1000:
        result["P"] = result["P"] / 1000.0

    return result
