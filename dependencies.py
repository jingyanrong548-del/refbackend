"""
FastAPI 依赖函数
提供 API Key 鉴权等通用依赖，供路由注入使用
"""
from typing import Optional

from fastapi import Header, HTTPException

from config import SECRET_API_KEY


def verify_api_key(x_api_key: Optional[str] = Header(None, description="API 密钥，用于鉴权")) -> str:
    """
    验证 X-API-Key 请求头，保护 /calculate 等核心接口
    
    若 SECRET_API_KEY 未配置，则不进行鉴权（便于本地开发）。
    生产环境务必在 .env 中设置 SECRET_API_KEY。
    
    Returns:
        验证通过的 API Key 字符串
        
    Raises:
        HTTPException 401: 未提供或密钥不匹配
    """
    # 未配置密钥时跳过鉴权（开发环境友好）
    if not SECRET_API_KEY:
        return x_api_key or "dev-skip"
    
    # 未提供密钥
    if not x_api_key or not x_api_key.strip():
        raise HTTPException(
            status_code=401,
            detail="Missing X-API-Key header. 请在请求头中提供 X-API-Key。",
        )
    
    # 密钥不匹配
    if x_api_key.strip() != SECRET_API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API Key. X-API-Key 无效。",
        )
    
    return x_api_key
