"""PromptOps CLI - Command Line Interface"""

import asyncio
import os
from pathlib import Path
from typing import Optional

import click
import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from promptops.version_manager import VersionManager
from promptops.llm_tester import LLMTester
from promptops.evaluator import Evaluator

console = Console()


@click.group()
@click.version_option(version="1.1.0", prog_name="promptops")
def main():
    """PromptOps CLI - 轻量级提示词工程运营工具"""
    pass


@main.command()
@click.argument("project_name")
@click.option("--directory", "-d", default=os.getcwd(), help="项目目录")
def init(project_name: str, directory: str):
    """初始化新项目"""
    project_path = Path(directory) / project_name
    vm = VersionManager(str(project_path))
    
    try:
        vm.init_project()
        console.print(Panel.fit(
            f"[green]✅ 项目 '{project_name}' 初始化成功[/]\n\n"
            f"[dim]📁 项目结构:[/]\n"
            f"  {project_path}/\n"
            f"  ├── prompts/         # 提示词定义\n"
            f"  ├── .promptops/\n"
            f"  │   ├── versions/   # 版本历史\n"
            f"  │   └── config.yaml # 项目配置\n\n"
            f"[dim]🚀 下一步:[/]\n"
            f"  cd {project_name}\n"
            f"  promptops new <prompt-name> --author <your-name>",
            title="PromptOps Init"
        ))
    except Exception as e:
        console.print(f"[red]❌ 初始化失败: {e}[/]")
        raise click.Abort()


@main.command()
@click.argument("name")
@click.option("--model", "-m", default="deepseek-chat", help="LLM 模型")
@click.option("--author", "-a", default="unknown", help="作者")
@click.option("--tags", "-t", help="标签（逗号分隔）")
@click.option("--description", "-d", help="描述")
def new(name: str, model: str, author: str, tags: Optional[str], description: Optional[str]):
    """创建新提示词"""
    vm = VersionManager(os.getcwd())
    
    try:
        tag_list = tags.split(",") if tags else []
        prompt_path = vm.create_prompt(
            name=name,
            model=model,
            author=author,
            tags=tag_list,
            description=description,
            content="# TODO: 添加提示词内容"
        )
        
        console.print(Panel.fit(
            f"[green]✅ 提示词 '{name}' 创建成功 (v1.0.0)[/]\n\n"
            f"[dim]📝 编辑文件: {prompt_path}[/]\n\n"
            f"[dim]🧪 添加测试用例验证行为[/]\n"
            f"[dim]📌 使用 'promptops test' 运行测试[/]",
            title="Prompt Created"
        ))
    except Exception as e:
        console.print(f"[red]❌ 创建失败: {e}[/]")
        raise click.Abort()


@main.command()
@click.argument("name")
def history(name: str):
    """查看版本历史"""
    vm = VersionManager(os.getcwd())
    
    try:
        histories = vm.get_version_history(name)
        
        if not histories:
            console.print(f"[yellow]⚠ 未找到 '{name}' 的版本历史[/]")
            return
        
        table = Table(title=f"📜 版本历史: {name}")
        table.add_column("版本", style="cyan")
        table.add_column("作者", style="magenta")
        table.add_column("时间", style="dim")
        table.add_column("变更", style="white")
        
        for record in histories:
            table.add_row(
                f"v{record.version}",
                record.author,
                record.timestamp.strftime("%Y-%m-%d %H:%M"),
                record.changes
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]❌ 错误: {e}[/]")
        raise click.Abort()


@main.command()
@click.argument("name")
@click.option("--live", is_flag=True, help="真实调用 LLM API")
@click.option("--sample", "-s", type=int, help="采样数量")
def test(name: str, live: bool, sample: Optional[int]):
    """运行测试套件"""
    vm = VersionManager(os.getcwd())
    
    try:
        prompt = vm.load_prompt(name)
        
        # 配置 API keys
        openai_key = os.environ.get("OPENAI_API_KEY")
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
        
        if live and not openai_key and not anthropic_key and not deepseek_key:
            console.print("[yellow]⚠ 未配置 API Key，将使用模拟测试[/]")
            live = False
        
        tester = LLMTester(
            openai_api_key=openai_key,
            anthropic_api_key=anthropic_key,
            deepseek_api_key=deepseek_key
        )
        
        console.print(f"\n[cyan]🧪 测试 '{name}' (v{prompt.version})[/]\n")
        
        # 运行测试
        results = asyncio.run(tester.run_tests(prompt, live=live, sample_size=sample))
        
        # 输出报告
        report = tester.generate_report(results)
        console.print(report)
        
        # 验证阈值
        if prompt.thresholds:
            thresholds_dict = {
                "accuracy": prompt.thresholds.accuracy,
                "latency_ms": prompt.thresholds.latency_ms
            }
            
            passed = tester.validate_thresholds(results, thresholds_dict)
            
            if not passed:
                console.print("[red bold]❌ 阈值验证失败[/]")
                console.print("[yellow]要求:[/]")
                if prompt.thresholds.accuracy:
                    console.print(f"  准确率 >= {prompt.thresholds.accuracy * 100}%")
                if prompt.thresholds.latency_ms:
                    console.print(f"  延迟 <= {prompt.thresholds.latency_ms}ms")
                raise click.Abort()
        
        if results.failed_tests > 0:
            raise click.Abort()
        
    except Exception as e:
        console.print(f"[red]❌ 测试失败: {e}[/]")
        raise click.Abort()


@main.command()
@click.argument("name")
@click.argument("version")
def rollback(name: str, version: str):
    """回滚到指定版本"""
    vm = VersionManager(os.getcwd())
    
    try:
        vm.rollback(name, version)
        console.print(Panel.fit(
            f"[green]✅ '{name}' 已回滚到 v{version}[/]\n\n"
            f"[dim]⚠️ 注意: 这会创建新的版本记录[/]",
            title="Rollback Complete"
        ))
    except Exception as e:
        console.print(f"[red]❌ 回滚失败: {e}[/]")
        raise click.Abort()


@main.command()
def list():
    """列出所有提示词"""
    vm = VersionManager(os.getcwd())
    
    try:
        prompts = vm.list_prompts()
        
        if not prompts:
            console.print("[yellow]⚠ 项目中未找到提示词[/]")
            return
        
        table = Table(title="📚 项目提示词")
        table.add_column("名称", style="cyan")
        table.add_column("版本", style="green")
        table.add_column("模型", style="magenta")
        table.add_column("描述", style="white")
        
        for name in prompts:
            prompt = vm.load_prompt(name)
            table.add_row(
                name,
                f"v{prompt.version}",
                prompt.model,
                prompt.description or "[dim]无描述[/]"
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]❌ 错误: {e}[/]")
        raise click.Abort()


if __name__ == "__main__":
    main()