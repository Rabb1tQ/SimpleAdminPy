"""
认证相关 Schema
"""
from typing import Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """登录请求"""

    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=50, description="密码")
    captcha_key: Optional[str] = Field(None, description="验证码key")
    captcha_code: Optional[str] = Field(None, description="验证码")


class LoginResponse(BaseModel):
    """登录响应"""

    accessToken: str = Field(description="访问令牌")


class RefreshTokenRequest(BaseModel):
    """刷新Token请求"""

    refreshToken: str = Field(..., description="刷新令牌")


class RefreshTokenResponse(BaseModel):
    """刷新Token响应"""

    accessToken: str = Field(description="新的访问令牌")


class CaptchaResponse(BaseModel):
    """验证码响应"""

    key: str = Field(description="验证码key")
    image: str = Field(description="验证码图片(Base64)")


class RegisterRequest(BaseModel):
    """注册请求"""

    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=50, description="密码")
    real_name: str = Field(..., min_length=2, max_length=50, description="真实姓名")
    email: Optional[str] = Field(None, max_length=100, description="邮箱")
    captcha_key: Optional[str] = Field(None, description="验证码key")
    captcha_code: Optional[str] = Field(None, description="验证码")


class ForgotPasswordRequest(BaseModel):
    """忘记密码请求"""

    email: str = Field(..., max_length=100, description="邮箱")
