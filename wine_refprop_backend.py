"""
REFPROP 8002 后端服务（供 refbackend 的 wine_refprop_client 调用）

使用 ctREFPROP 直接计算，需 RPPREFIX 指向含 librefprop.so 的 REFPROP 目录。
部署在 8002 端口，实现 wine_refprop_client 预期的单属性接口。
"""
import os
import sys

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

# wine_refprop_client 使用的属性名 -> REFPROP 输出代码
PROPERTY_TO_OUTPUT = {
    "temperature": "T",
    "pressure": "P",
    "density": "D",
    "enthalpy": "H",
    "entropy": "S",
    "quality": "Qmole",
    "cp": "CP",
    "cv": "CV",
    "speed_of_sound": "W",
}


class CalcRequest(BaseModel):
    """单属性请求（wine_refprop_client 格式）"""
    fluid: str
    temperature: float  # °C
    pressure: float     # Pa
    prop: str = Field(alias="property")  # temperature, pressure, density, ...

    model_config = ConfigDict(populate_by_name=True)


def _get_refprop_value(fluid: str, t_k: float, p_kpa: float, out_code: str) -> float:
    """调用 ctREFPROP 获取单个物性"""
    rpprefix = os.environ.get("RPPREFIX", "").strip()
    if not rpprefix or not os.path.isdir(rpprefix):
        raise RuntimeError(
            f"RPPREFIX 未配置或无效: {rpprefix}。"
            "请设置环境变量指向 REFPROP 目录（含 librefprop.so 和 FLUIDS）。"
        )

    from ctREFPROP.ctREFPROP import REFPROPFunctionLibrary
    from refprop_service import parse_fluid_string

    RP = REFPROPFunctionLibrary(rpprefix)
    RP.SETPATHdll(rpprefix)
    MOLAR_BASE_SI = RP.GETENUMdll(0, "MOLAR BASE SI").iEnum

    refprop_fluid, z = parse_fluid_string(fluid)
    r = RP.REFPROPdll(
        refprop_fluid, "TP", out_code, MOLAR_BASE_SI, 0, 0, p_kpa, t_k, z
    )
    if r.ierr > 100:
        raise RuntimeError(f"REFPROP 计算错误 (ierr={r.ierr}): {r.herr.strip()}")

    val = r.Output[0]
    if val <= -9999970:  # 未定义标记
        return None
    return float(val)


app = FastAPI(title="REFPROP 8002 后端", version="1.0.0")


@app.get("/")
def root():
    return {"service": "REFPROP 8002 backend", "status": "ok"}


@app.post("/calculate")
def calculate(req: CalcRequest):
    """
    单属性计算接口（wine_refprop_client 预期格式）
    temperature: °C, pressure: Pa
    """
    out_code = PROPERTY_TO_OUTPUT.get(req.prop.lower())
    if not out_code:
        raise HTTPException(400, f"不支持的属性: {req.prop}")

    t_k = req.temperature + 273.15
    p_kpa = req.pressure / 1000.0

    try:
        val = _get_refprop_value(req.fluid, t_k, p_kpa, out_code)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(500, str(e))

    # 单位转换以匹配 SI
    unit = "K" if out_code == "T" else "kPa" if out_code == "P" else "SI"
    return {"result": {"value": val, "unit": unit}}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8002)
