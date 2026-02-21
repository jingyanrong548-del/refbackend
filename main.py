"""
基于 REFPROP 10.0 的热力学计算 API（进阶版）
用于高温热泵、新工质开发等高精度工业应用，支持多 App 接入
"""
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import ALLOWED_ORIGINS
from dome_engine import compute_saturation_dome
from refprop_engine import calculate_properties


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


class DomeRequest(BaseModel):
    """POST /dome 请求体"""
    fluid_string: str = Field(
        ...,
        description="工质字符串。纯工质如 'R32'；混合工质如 'R32&R125|0.5&0.5'"
    )


class DomeResponse(BaseModel):
    """POST /dome 响应体"""
    liquid: list = Field(..., description="饱和液线 (q=0) 的 [P, H] 点列表")
    vapor: list = Field(..., description="饱和气线 (q=1) 的 [P, H] 点列表")
    critical: dict = Field(..., description="临界点 {T, P, H}")


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
    VIS: Optional[float] = Field(None, description="动力粘度 [µPa·s]")
    TCX: Optional[float] = Field(None, description="导热系数 [W/(m·K)]")
    PRANDTL: Optional[float] = Field(None, description="普朗特数 [-]")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时记录配置"""
    yield


app = FastAPI(
    title="REFPROP 热力学计算 API",
    description="基于 NIST REFPROP 10.0 的热力学性质计算接口，支持纯工质和混合工质",
    version="1.0.0",
    lifespan=lifespan,
)

# ============== 多域 CORS 支持 ==============
# 从 .env 的 ALLOWED_ORIGINS 读取，支持 reffrontend、个人站点、本地开发等
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
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
        )
        return CalculateResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/dome", response_model=DomeResponse)
def dome(req: DomeRequest) -> DomeResponse:
    """
    生成饱和包络线 (P-h Dome) 数据
    
    返回饱和液线 (q=0) 和饱和气线 (q=1) 的 (P, H) 坐标点数组，
    供前端绘制 P-h 压焓图。单位：P [kPa]，H [J/mol]。
    """
    try:
        result = compute_saturation_dome(fluid_string=req.fluid_string)
        return DomeResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
def root():
    """健康检查（无需鉴权）"""
    return {"status": "ok", "api": "REFPROP 热力学计算 API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
