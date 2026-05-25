"""Tests for PromptOps CLI"""

import pytest
from pathlib import Path
import tempfile

from promptops.version_manager import VersionManager
from promptops.types import PromptDefinition


@pytest.fixture
def temp_project():
    """创建临时项目目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        vm = VersionManager(tmpdir)
        vm.init_project()
        yield tmpdir


def test_init_project(temp_project):
    """测试项目初始化"""
    assert Path(temp_project).exists()
    assert (Path(temp_project) / "prompts").exists()
    assert (Path(temp_project) / ".promptops").exists()


def test_create_prompt(temp_project):
    """测试创建提示词"""
    vm = VersionManager(temp_project)
    
    prompt_path = vm.create_prompt(
        name="test-prompt",
        model="gpt-4o",
        author="test-author",
        description="Test prompt"
    )
    
    assert prompt_path.exists()
    
    # 加载并验证
    prompt = vm.load_prompt("test-prompt")
    assert prompt.name == "test-prompt"
    assert prompt.version == "1.0.0"
    assert prompt.author == "test-author"


def test_version_history(temp_project):
    """测试版本历史"""
    vm = VersionManager(temp_project)
    
    vm.create_prompt(name="version-test")
    
    history = vm.get_version_history("version-test")
    assert len(history) == 1
    assert history[0].version == "1.0.0"
    assert history[0].changes == "Initial version"


def test_list_prompts(temp_project):
    """测试列出提示词"""
    vm = VersionManager(temp_project)
    
    vm.create_prompt(name="prompt-1")
    vm.create_prompt(name="prompt-2")
    
    prompts = vm.list_prompts()
    assert len(prompts) == 2
    assert "prompt-1" in prompts
    assert "prompt-2" in prompts


def test_prompt_not_found(temp_project):
    """测试提示词不存在"""
    vm = VersionManager(temp_project)
    
    with pytest.raises(Exception):
        vm.load_prompt("non-existent")