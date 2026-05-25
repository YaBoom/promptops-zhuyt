"""PromptOps CLI - DSPy-style Evaluator"""

import json
import statistics
from typing import Any, Dict, List, Optional

from pydantic import BaseModel
from rich.console import Console

console = Console()


class EvaluationResult(BaseModel):
    """评估结果"""
    prompt_name: str
    version: str
    metrics: Dict[str, float]
    samples: int
    passed: bool
    details: Optional[Dict[str, Any]] = None


class Evaluator:
    """DSPy风格评估器"""
    
    def __init__(
        self,
        llm_judge_model: Optional[str] = None,
        custom_metrics: Optional[Dict[str, Any]] = None
    ):
        self.llm_judge_model = llm_judge_model
        self.custom_metrics = custom_metrics or {}
    
    def evaluate(
        self,
        prompt_name: str,
        version: str,
        test_outputs: List[Dict[str, Any]],
        metrics: List[str] = None
    ) -> EvaluationResult:
        """评估测试输出"""
        if metrics is None:
            metrics = ["accuracy", "consistency", "relevance"]
        
        results = {}
        
        for metric in metrics:
            if metric == "accuracy":
                results["accuracy"] = self._evaluate_accuracy(test_outputs)
            elif metric == "consistency":
                results["consistency"] = self._evaluate_consistency(test_outputs)
            elif metric == "relevance":
                results["relevance"] = self._evaluate_relevance(test_outputs)
            elif metric in self.custom_metrics:
                results[metric] = self.custom_metrics[metric](test_outputs)
        
        # 判断是否通过
        passed = all(v >= 0.8 for v in results.values() if isinstance(v, float))
        
        return EvaluationResult(
            prompt_name=prompt_name,
            version=version,
            metrics=results,
            samples=len(test_outputs),
            passed=passed,
            details={"raw_outputs": test_outputs[:5]}  # 保留前5个样本
        )
    
    def _evaluate_accuracy(self, outputs: List[Dict[str, Any]]) -> float:
        """评估准确率"""
        correct = 0
        total = len(outputs)
        
        for output in outputs:
            if "expected" in output and "actual" in output:
                if self._fuzzy_match(output["expected"], output["actual"]):
                    correct += 1
            elif "passed" in output and output["passed"]:
                correct += 1
        
        return correct / total if total > 0 else 0.0
    
    def _evaluate_consistency(self, outputs: List[Dict[str, Any]]) -> float:
        """评估一致性（输出格式是否一致）"""
        if not outputs:
            return 0.0
        
        # 检查是否所有输出都有相同结构
        structures = [self._get_structure(o) for o in outputs]
        
        if not structures:
            return 0.0
        
        # 统计相同结构的比例
        most_common = max(set(structures), key=structures.count)
        consistency = structures.count(most_common) / len(structures)
        
        return consistency
    
    def _evaluate_relevance(self, outputs: List[Dict[str, Any]]) -> float:
        """评估相关性（输出是否与输入相关）"""
        # 简化版：假设所有输出都有relevance字段
        relevances = [o.get("relevance", 0.5) for o in outputs]
        
        if relevances:
            return statistics.mean(relevances)
        return 0.5
    
    def _fuzzy_match(self, expected: Any, actual: Any) -> bool:
        """模糊匹配"""
        if isinstance(expected, str) and isinstance(actual, str):
            return expected.lower() in actual.lower()
        
        if isinstance(expected, dict) and isinstance(actual, dict):
            for key, value in expected.items():
                if key in actual:
                    if not self._fuzzy_match(value, actual[key]):
                        return False
            return True
        
        return str(expected).lower() in str(actual).lower()
    
    def _get_structure(self, obj: Any) -> str:
        """获取对象结构签名"""
        if isinstance(obj, dict):
            keys = sorted(obj.keys())
            return f"dict:{','.join(keys)}"
        elif isinstance(obj, list):
            if obj:
                return f"list[{self._get_structure(obj[0])}]"
            return "list[]"
        elif isinstance(obj, str):
            return "str"
        elif isinstance(obj, (int, float)):
            return "num"
        else:
            return "other"
    
    def generate_report(self, result: EvaluationResult) -> str:
        """生成评估报告"""
        status = "✅ PASSED" if result.passed else "❌ FAILED"
        
        report = f"""
╔══════════════════════════════════════════════════════════╗
║           PromptOps Evaluation Report                    ║
╠══════════════════════════════════════════════════════════╣
║ Prompt: {result.prompt_name} (v{result.version})
║ Samples: {result.samples}
╠══════════════════════════════════════════════════════════╣
║ {status}
╠══════════════════════════════════════════════════════════╣
║ 📊 Metrics:
"""
        
        for metric, value in result.metrics.items():
            if isinstance(value, float):
                report += f"║   {metric:15s}: {value * 100:.2f}%\n"
            else:
                report += f"║   {metric:15s}: {value}\n"
        
        report += "╚══════════════════════════════════════════════════════════╝\n"
        
        return report
    
    def compare_versions(
        self,
        baseline: EvaluationResult,
        variant: EvaluationResult
    ) -> Dict[str, Any]:
        """对比两个版本的评估结果"""
        comparison = {
            "baseline_version": baseline.version,
            "variant_version": variant.version,
            "improvements": {},
            "degradations": {},
            "summary": ""
        }
        
        for metric in baseline.metrics:
            if metric in variant.metrics:
                delta = variant.metrics[metric] - baseline.metrics[metric]
                
                if delta > 0.05:
                    comparison["improvements"][metric] = {
                        "baseline": baseline.metrics[metric],
                        "variant": variant.metrics[metric],
                        "delta": delta
                    }
                elif delta < -0.05:
                    comparison["degradations"][metric] = {
                        "baseline": baseline.metrics[metric],
                        "variant": variant.metrics[metric],
                        "delta": delta
                    }
        
        # 总结
        if comparison["improvements"] and not comparison["degradations"]:
            comparison["summary"] = "✅ Variant is better overall"
        elif comparison["degradations"] and not comparison["improvements"]:
            comparison["summary"] = "❌ Baseline is better overall"
        else:
            comparison["summary"] = "⚠️ Mixed results - review metrics"
        
        return comparison