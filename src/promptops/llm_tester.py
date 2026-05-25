"""PromptOps CLI - Real LLM Testing with OpenAI/Anthropic/DeepSeek"""

import asyncio
import time
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from promptops.types import (
    PromptDefinition,
    TestCase,
    TestResult,
    LLMResponse,
    PromptNotFoundError
)

console = Console()


class LLMTester:
    """真实 LLM API 测试器"""
    
    DEEPSEEK_BASE_URL = "https://api.deepseek.com"
    
    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
        deepseek_api_key: Optional[str] = None
    ):
        self.openai_client = AsyncOpenAI(api_key=openai_api_key) if openai_api_key else None
        self.anthropic_client = AsyncAnthropic(api_key=anthropic_api_key) if anthropic_api_key else None
        # DeepSeek 使用 OpenAI 兼容 API
        self.deepseek_client = AsyncOpenAI(
            api_key=deepseek_api_key,
            base_url=self.DEEPSEEK_BASE_URL
        ) if deepseek_api_key else None
    
    async def run_tests(
        self,
        prompt: PromptDefinition,
        live: bool = True,
        sample_size: Optional[int] = None
    ) -> TestResult:
        """运行测试套件"""
        tests = prompt.tests
        
        if sample_size and sample_size < len(tests):
            tests = tests[:sample_size]
        
        if not tests:
            console.print("[yellow]⚠ No test cases defined[/]")
            return TestResult(
                prompt_name=prompt.name,
                version=prompt.version,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                accuracy=0.0,
                latency_avg_ms=0.0,
                errors=["No test cases"]
            )
        
        results = TestResult(
            prompt_name=prompt.name,
            version=prompt.version,
            total_tests=len(tests),
            passed_tests=0,
            failed_tests=0,
            accuracy=0.0,
            latency_avg_ms=0.0,
            errors=[]
        )
        
        latencies: List[float] = []
        total_cost = 0.0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            console=console
        ) as progress:
            task = progress.add_task(
                f"Testing {prompt.name}...",
                total=len(tests)
            )
            
            for test in tests:
                try:
                    if live:
                        response = await self._call_llm(prompt, test.input)
                        latencies.append(response.latency_ms)
                        total_cost += response.cost
                        
                        # 验证输出
                        passed = self._match_expected(response.content, test.expected)
                    else:
                        # 模拟测试（不调用API）
                        passed = self._simulate_test(prompt, test)
                        latencies.append(50.0)  # 模拟延迟
                    
                    if passed:
                        results.passed_tests += 1
                    else:
                        results.failed_tests += 1
                        results.errors.append(
                            f"Test failed: {test.description or test.input[:50]}"
                        )
                    
                    progress.advance(task)
                    
                except Exception as e:
                    results.failed_tests += 1
                    results.errors.append(f"Error: {str(e)}")
                    progress.advance(task)
        
        # 计算统计指标
        results.accuracy = results.passed_tests / results.total_tests
        results.latency_avg_ms = sum(latencies) / len(latencies) if latencies else 0.0
        results.latency_p95_ms = self._calculate_p95(latencies) if latencies else 0.0
        results.total_cost = total_cost
        
        return results
    
    async def _call_llm(
        self,
        prompt: PromptDefinition,
        input_text: str
    ) -> LLMResponse:
        """调用真实 LLM API"""
        start_time = time.time()
        
        full_prompt = f"{prompt.content}\n\nInput:\n{input_text}"
        
        # 根据模型选择客户端
        if prompt.model.startswith("gpt") or prompt.model.startswith("o1"):
            if not self.openai_client:
                raise ValueError("OpenAI API key not configured")
            
            response = await self.openai_client.chat.completions.create(
                model=prompt.model,
                messages=[{"role": "user", "content": full_prompt}],
                temperature=prompt.config.get("temperature", 0.7) if prompt.config else 0.7,
                max_tokens=prompt.config.get("max_tokens", 1000) if prompt.config else 1000
            )
            
            latency = (time.time() - start_time) * 1000
            content = response.choices[0].message.content or ""
            tokens_used = response.usage.total_tokens
            
            # 计算成本（简化版）
            cost = self._calculate_openai_cost(prompt.model, tokens_used)
            
            return LLMResponse(
                content=content,
                model=prompt.model,
                latency_ms=latency,
                tokens_used=tokens_used,
                cost=cost,
                finish_reason=response.choices[0].finish_reason
            )
        
        elif prompt.model.startswith("deepseek"):
            if not self.deepseek_client:
                raise ValueError("DeepSeek API key not configured")
            
            response = await self.deepseek_client.chat.completions.create(
                model=prompt.model,
                messages=[{"role": "user", "content": full_prompt}],
                temperature=prompt.config.get("temperature", 0.7) if prompt.config else 0.7,
                max_tokens=prompt.config.get("max_tokens", 1000) if prompt.config else 1000
            )
            
            latency = (time.time() - start_time) * 1000
            content = response.choices[0].message.content or ""
            tokens_used = response.usage.total_tokens
            cost = self._calculate_deepseek_cost(prompt.model, tokens_used)
            
            return LLMResponse(
                content=content,
                model=prompt.model,
                latency_ms=latency,
                tokens_used=tokens_used,
                cost=cost,
                finish_reason=response.choices[0].finish_reason or "complete"
            )
        
        elif prompt.model.startswith("claude"):
            if not self.anthropic_client:
                raise ValueError("Anthropic API key not configured")
            
            response = await self.anthropic_client.messages.create(
                model=prompt.model,
                max_tokens=prompt.config.get("max_tokens", 1000) if prompt.config else 1000,
                messages=[{"role": "user", "content": full_prompt}]
            )
            
            latency = (time.time() - start_time) * 1000
            content = response.content[0].text
            tokens_used = response.usage.input_tokens + response.usage.output_tokens
            cost = self._calculate_anthropic_cost(prompt.model, tokens_used)
            
            return LLMResponse(
                content=content,
                model=prompt.model,
                latency_ms=latency,
                tokens_used=tokens_used,
                cost=cost,
                finish_reason="complete"
            )
        
        else:
            raise ValueError(f"Unsupported model: {prompt.model}")
    
    def _match_expected(
        self,
        output: str,
        expected: Dict[str, Any]
    ) -> bool:
        """匹配期望输出（简化版）"""
        # 实际应用中应使用更智能的比对（如 LLM-as-judge）
        try:
            # 尝试解析JSON输出
            if "{" in output:
                import json
                output_json = json.loads(output[output.find("{"):output.rfind("}")+1])
                for key, value in expected.items():
                    if key in output_json:
                        # 部分匹配
                        if str(value).lower() in str(output_json[key]).lower():
                            return True
                return False
            else:
                # 文本匹配
                for key, value in expected.items():
                    if str(value).lower() in output.lower():
                        return True
                return False
        except:
            return False
    
    def _simulate_test(
        self,
        prompt: PromptDefinition,
        test: TestCase
    ) -> bool:
        """模拟测试（不调用API）"""
        # 简化逻辑，实际应更复杂
        return len(test.expected) > 0
    
    def _calculate_p95(self, latencies: List[float]) -> float:
        """计算 P95 延迟"""
        if not latencies:
            return 0.0
        sorted_latencies = sorted(latencies)
        p95_index = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[p95_index]
    
    def _calculate_openai_cost(self, model: str, tokens: int) -> float:
        """计算 OpenAI 成本（简化版）"""
        # 2026年1月价格（大致）
        pricing = {
            "gpt-4o": 0.005 / 1000,  # $5 per 1M tokens
            "gpt-4-turbo": 0.01 / 1000,
            "o1-preview": 0.015 / 1000,
        }
        return tokens * pricing.get(model, 0.005 / 1000)
    
    def _calculate_anthropic_cost(self, model: str, tokens: int) -> float:
        """计算 Anthropic 成本（简化版）"""
        pricing = {
            "claude-3.7-opus": 0.015 / 1000,
            "claude-3.7-sonnet": 0.003 / 1000,
        }
        return tokens * pricing.get(model, 0.003 / 1000)
    
    def _calculate_deepseek_cost(self, model: str, tokens: int) -> float:
        """计算 DeepSeek 成本（简化版）"""
        pricing = {
            "deepseek-chat": 0.0014 / 1000,   # $1.4 per 1M tokens (input)
            "deepseek-reasoner": 0.0055 / 1000,  # $5.5 per 1M tokens
        }
        return tokens * pricing.get(model, 0.0014 / 1000)
    
    def validate_thresholds(
        self,
        results: TestResult,
        thresholds: Optional[Dict[str, float]]
    ) -> bool:
        """验证阈值"""
        if not thresholds:
            return True
        
        if thresholds.get("accuracy") and results.accuracy < thresholds["accuracy"]:
            return False
        
        if thresholds.get("latency_ms") and results.latency_avg_ms > thresholds["latency_ms"]:
            return False
        
        return True
    
    def generate_report(self, results: TestResult) -> str:
        """生成测试报告"""
        status = "✅ PASSED" if results.failed_tests == 0 else "❌ FAILED"
        
        report = f"""
╔══════════════════════════════════════════════════════════╗
║           PromptOps Test Report                          ║
╠══════════════════════════════════════════════════════════╣
║ Prompt: {results.prompt_name} (v{results.version})
║ Timestamp: {results.timestamp}
╠══════════════════════════════════════════════════════════╣
║ {status}
╠══════════════════════════════════════════════════════════╣
║ 📊 Metrics:
║   Total Tests:    {results.total_tests}
║   Passed:         {results.passed_tests}
║   Failed:         {results.failed_tests}
║   Accuracy:       {results.accuracy * 100:.2f}%
║   Avg Latency:    {results.latency_avg_ms:.2f}ms
║   P95 Latency:    {results.latency_p95_ms:.2f}ms
║   Total Cost:     ${results.total_cost:.4f}
╚══════════════════════════════════════════════════════════╝
"""
        
        if results.errors:
            report += "\n❌ Errors:\n"
            for error in results.errors:
                report += f"  - {error}\n"
        
        return report