"""PromptOps CLI - Type definitions"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PromptMetadata(BaseModel):
    """提示词元数据"""
    name: str = Field(..., description="提示词名称")
    version: str = Field(default="1.0.0", description="语义版本号")
    model: str = Field(default="deepseek-chat", description="LLM模型")
    author: str = Field(default="unknown", description="作者")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    tags: List[str] = Field(default_factory=list, description="标签")
    description: Optional[str] = Field(None, description="描述")


class TestCase(BaseModel):
    """测试用例"""
    input: str = Field(..., description="输入文本")
    expected: Dict[str, Any] = Field(default_factory=dict, description="期望输出")
    description: Optional[str] = Field(None, description="用例描述")


class PromptThreshold(BaseModel):
    """质量阈值"""
    accuracy: Optional[float] = Field(None, ge=0, le=1, description="准确率阈值")
    latency_ms: Optional[float] = Field(None, ge=0, description="延迟阈值(ms)")
    cost_per_request: Optional[float] = Field(None, ge=0, description="单次成本阈值")
    custom_metrics: Optional[Dict[str, float]] = Field(None, description="自定义指标")


class PromptDefinition(PromptMetadata):
    """完整提示词定义"""
    content: str = Field(default="", description="提示词内容")
    tests: List[TestCase] = Field(default_factory=list, description="测试用例列表")
    thresholds: Optional[PromptThreshold] = Field(None, description="质量阈值")
    config: Optional[Dict[str, Any]] = Field(None, description="配置参数")


class VersionHistory(BaseModel):
    """版本历史记录"""
    version: str = Field(..., description="版本号")
    author: str = Field(..., description="作者")
    timestamp: datetime = Field(..., description="时间")
    changes: str = Field(..., description="变更说明")
    hash: Optional[str] = Field(None, description="内容哈希")


class TestResult(BaseModel):
    """测试结果"""
    prompt_name: str = Field(..., description="提示词名称")
    version: str = Field(..., description="版本号")
    total_tests: int = Field(..., ge=0, description="总测试数")
    passed_tests: int = Field(..., ge=0, description="通过数")
    failed_tests: int = Field(..., ge=0, description="失败数")
    accuracy: float = Field(..., ge=0, le=1, description="准确率")
    latency_avg_ms: float = Field(..., ge=0, description="平均延迟(ms)")
    latency_p95_ms: Optional[float] = Field(None, description="P95延迟(ms)")
    total_cost: Optional[float] = Field(None, ge=0, description="总成本($)")
    errors: List[str] = Field(default_factory=list, description="错误列表")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")


class MetricsSnapshot(BaseModel):
    """监控指标快照"""
    prompt_name: str = Field(..., description="提示词名称")
    version: str = Field(..., description="版本号")
    timestamp: datetime = Field(..., description="时间戳")
    requests: int = Field(..., ge=0, description="请求总数")
    accuracy: float = Field(..., ge=0, le=1, description="准确率")
    latency_avg_ms: float = Field(..., ge=0, description="平均延迟")
    cost_total: float = Field(..., ge=0, description="总成本")
    errors: int = Field(..., ge=0, description="错误数")
    user_satisfaction: Optional[float] = Field(None, ge=0, le=5, description="用户满意度")


class LLMResponse(BaseModel):
    """LLM API 响应"""
    content: str = Field(..., description="响应内容")
    model: str = Field(..., description="使用的模型")
    latency_ms: float = Field(..., description="延迟(ms)")
    tokens_used: int = Field(..., ge=0, description="token使用量")
    cost: float = Field(..., ge=0, description="成本($)")
    finish_reason: str = Field(default="complete", description="结束原因")


class PromptOpsError(Exception):
    """PromptOps 错误基类"""
    
    def __init__(self, error_type: str, message: str, details: Optional[Dict] = None):
        self.error_type = error_type
        self.message = message
        self.details = details or {}
        super().__init__(f"[{error_type}] {message}")


class PromptNotFoundError(PromptOpsError):
    """提示词未找到"""
    def __init__(self, name: str):
        super().__init__("PROMPT_NOT_FOUND", f"Prompt '{name}' not found")


class VersionConflictError(PromptOpsError):
    """版本冲突"""
    def __init__(self, version: str):
        super().__init__("VERSION_CONFLICT", f"Version '{version}' already exists")


class TestFailureError(PromptOpsError):
    """测试失败"""
    def __init__(self, failed_count: int, details: Dict):
        super().__init__(
            "TEST_FAILURE",
            f"{failed_count} tests failed",
            details
        )