"""PromptOps CLI - Version Management"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import yaml
from promptops.types import (
    PromptDefinition,
    VersionHistory,
    PromptNotFoundError,
    VersionConflictError
)


class VersionManager:
    """提示词版本管理器"""
    
    def __init__(self, project_path: str):
        self.base_path = Path(project_path)
        self.prompts_dir = self.base_path / "prompts"
        self.versions_dir = self.base_path / ".promptops" / "versions"
    
    def init_project(self) -> None:
        """初始化项目目录结构"""
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.prompts_dir.mkdir(parents=True, exist_ok=True)
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建配置文件
        config_path = self.base_path / ".promptops" / "config.yaml"
        if not config_path.exists():
            config = {
                "project": self.base_path.name,
                "default_model": "deepseek-chat",
                "thresholds": {
                    "accuracy": 0.95,
                    "latency_ms": 500
                }
            }
            config_path.write_text(yaml.dump(config), encoding="utf-8")
    
    def create_prompt(
        self,
        name: str,
        model: Optional[str] = None,
        author: Optional[str] = None,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
        description: Optional[str] = None
    ) -> Path:
        """创建新提示词"""
        prompt_path = self.prompts_dir / f"{name}.yaml"
        
        if prompt_path.exists():
            raise VersionConflictError(name)
        
        now = datetime.now()
        prompt = PromptDefinition(
            name=name,
            version="1.0.0",
            model=model or "deepseek-chat",
            author=author or "unknown",
            created_at=now,
            updated_at=now,
            content=content or "",
            tags=tags or [],
            description=description,
            tests=[]
        )
        
        prompt_path.write_text(yaml.dump(prompt.model_dump()), encoding="utf-8")
        
        # 保存版本历史
        self._save_version(name, "1.0.0", VersionHistory(
            version="1.0.0",
            author=prompt.author,
            timestamp=now,
            changes="Initial version",
            hash=self._generate_hash(prompt.content)
        ))
        
        return prompt_path
    
    def load_prompt(self, name: str) -> PromptDefinition:
        """加载提示词"""
        prompt_path = self.prompts_dir / f"{name}.yaml"
        
        if not prompt_path.exists():
            raise PromptNotFoundError(name)
        
        content = prompt_path.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        return PromptDefinition(**data)
    
    def update_version(
        self,
        name: str,
        new_version: str,
        changes: str,
        author: str
    ) -> None:
        """更新提示词版本"""
        prompt = self.load_prompt(name)
        
        # 验证版本号递增
        if not self._is_version_higher(prompt.version, new_version):
            raise VersionConflictError(new_version)
        
        now = datetime.now()
        prompt.version = new_version
        prompt.updated_at = now
        prompt.author = author
        
        prompt_path = self.prompts_dir / f"{name}.yaml"
        prompt_path.write_text(yaml.dump(prompt.model_dump()), encoding="utf-8")
        
        self._save_version(name, new_version, VersionHistory(
            version=new_version,
            author=author,
            timestamp=now,
            changes=changes,
            hash=self._generate_hash(prompt.content)
        ))
    
    def get_version_history(self, name: str) -> List[VersionHistory]:
        """获取版本历史"""
        history_path = self.versions_dir / f"{name}_history.yaml"
        
        if not history_path.exists():
            return []
        
        content = history_path.read_text(encoding="utf-8")
        data = yaml.safe_load(content) or []
        return [VersionHistory(**item) for item in data]
    
    def rollback(self, name: str, target_version: str) -> None:
        """回滚到指定版本"""
        history = self.get_version_history(name)
        target_record = next(
            (v for v in history if v.version == target_version),
            None
        )
        
        if not target_record:
            raise PromptNotFoundError(f"{name} v{target_version}")
        
        # 从历史恢复
        version_file = self.versions_dir / f"{name}-{target_version}.yaml"
        if not version_file.exists():
            raise PromptNotFoundError(f"{name} v{target_version} backup")
        
        content = version_file.read_text(encoding="utf-8")
        prompt_data = yaml.safe_load(content)
        prompt = PromptDefinition(**prompt_data)
        
        # 恢复到主文件
        prompt_path = self.prompts_dir / f"{name}.yaml"
        prompt.updated_at = datetime.now()
        prompt_path.write_text(yaml.dump(prompt.model_dump()), encoding="utf-8")
        
        # 记录回滚
        self._save_version(name, prompt.version, VersionHistory(
            version=prompt.version,
            author=prompt.author,
            timestamp=datetime.now(),
            changes=f"Rollback to v{target_version}",
            hash=self._generate_hash(prompt.content)
        ))
    
    def _save_version(self, name: str, version: str, history: VersionHistory) -> None:
        """保存版本历史"""
        history_path = self.versions_dir / f"{name}_history.yaml"
        
        histories = []
        if history_path.exists():
            content = history_path.read_text(encoding="utf-8")
            histories = yaml.safe_load(content) or []
        
        histories.append(history.model_dump())
        history_path.write_text(yaml.dump(histories), encoding="utf-8")
        
        # 备份完整版本
        prompt = self.load_prompt(name)
        backup_path = self.versions_dir / f"{name}-{version}.yaml"
        backup_path.write_text(yaml.dump(prompt.model_dump()), encoding="utf-8")
    
    def _is_version_higher(self, current: str, new_version: str) -> bool:
        """比较版本号"""
        current_parts = [int(x) for x in current.split(".")]
        new_parts = [int(x) for x in new_version.split(".")]
        
        for i in range(3):
            if len(new_parts) > i and len(current_parts) > i:
                if new_parts[i] > current_parts[i]:
                    return True
                if new_parts[i] < current_parts[i]:
                    return False
        
        return False
    
    def _generate_hash(self, content: str) -> str:
        """生成内容哈希"""
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def list_prompts(self) -> List[str]:
        """列出所有提示词"""
        if not self.prompts_dir.exists():
            return []
        
        return [
            f.stem for f in self.prompts_dir.glob("*.yaml")
        ]