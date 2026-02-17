"""
基于 REFPROP 10.0 的热力学计算 API
用于高温热泵、新工质开发等高精度工业应用
"""
from contextlib import asynccontextmanager

from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from config import RPPREFIX, WINE_REFPROP_URL
from refprop_service import calculate_properties


# --- 请求/响应模型 ---

class CalculateRequest(BaseModel):
    """POST /calculate 请求体"""
    fluid_string: str = Field(
        ...,
        description="工质字符串。纯工质如 'R32','R1234ZE'；混合工质如 'R32&R125|0.5&0.5'（摩尔分数）"
    )
    input_type: str = Field(
        ...,
        description="输入类型：PT(压力温度)、PQ(压力干度)、PH(压力焓)、TD(温度密度)等"
    )
    value1: float = Field(..., description="第一个输入参数的值")
    value2: float = Field(..., description="第二个输入参数的值")


class CalculateResponse(BaseModel):
    """POST /calculate 响应体"""
    T: Optional[float] = Field(None, description="温度 [K]")
    P: Optional[float] = Field(None, description="压力 [kPa]")
    D: Optional[float] = Field(None, description="密度 [mol/dm³]")
    H: Optional[float] = Field(None, description="焓 [J/mol]")
    S: Optional[float] = Field(None, description="熵 [J/(mol·K)]")
    Q: Optional[float] = Field(None, description="干度 (摩尔基，两相区 0~1)")
    CP: Optional[float] = Field(None, description="定压比热 [J/(mol·K)]")
    CV: Optional[float] = Field(None, description="定容比热 [J/(mol·K)]")
    W: Optional[float] = Field(None, description="声速 [m/s]")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时检查 REFPROP 路径"""
    import os
    if not RPPREFIX or not os.path.isdir(RPPREFIX):
        import logging
        logging.warning(
            f"RPPREFIX 未配置或路径无效: {RPPREFIX}。"
            "请设置环境变量 RPPREFIX 指向 REFPROP 安装目录。"
        )
    yield


app = FastAPI(
    title="REFPROP 热力学计算 API",
    description="基于 NIST REFPROP 10.0 的热力学性质计算接口，支持纯工质和混合工质",
    version="1.0.0",
    lifespan=lifespan,
)


@app.post("/calculate", response_model=CalculateResponse)
def calculate(req: CalculateRequest) -> CalculateResponse:
    """
    热力学性质计算
    
    - **fluid_string**: 工质（纯或混合）。混合格式: `R32&R125|0.5&0.5`
    - **input_type**: PT, PQ, PH, TD 等两字符组合
    - **value1, value2**: 对应输入类型的数值（单位见 REFPROP 文档）
    """
    try:
        result = calculate_properties(
            fluid_string=req.fluid_string,
            input_type=req.input_type,
            value1=req.value1,
            value2=req.value2,
            rpprefix=RPPREFIX,
            wine_refprop_url=WINE_REFPROP_URL or None,
        )
        return CalculateResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
def root():
    """健康检查"""
    return {"status": "ok", "api": "REFPROP 热力学计算 API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
