from __future__ import annotations
import shutil
from pathlib import Path
import pytest
from evren_agent.skills.manager import SkillManager
from evren_agent.skills.skill import Skill


def test_skill_save_and_load(tmp_path):
    skill = Skill(
        name="test_lawyer",
        description="Legal assistant for contract analysis",
        instructions="Always cite relevant articles and evaluate breach terms.",
        tags=["law", "contracts"],
    )
    skill.save(tmp_path)

    loaded = Skill.load_from_directory(tmp_path / "test_lawyer")
    assert loaded.name == "test_lawyer"
    assert loaded.description == "Legal assistant for contract analysis"
    assert "Always cite relevant articles" in loaded.instructions
    assert "law" in loaded.tags


def test_skill_manager_workflow(tmp_path):
    manager = SkillManager(skills_dir=tmp_path)

    # Add dynamic skill
    manager.add_skill(
        name="turkish_nlp",
        description="Turkish language processing rules",
        instructions="Ensure proper agglutinative suffix vowel harmony.",
        tags=["nlp", "turkish"],
        activate=True,
    )

    assert "turkish_nlp" in manager.skills
    assert manager.skills["turkish_nlp"].is_active is True

    # Check prompt augmentation
    aug = manager.get_prompt_augmentation()
    assert "[Skill: turkish_nlp]" in aug
    assert "vowel harmony" in aug

    # Deactivate
    manager.deactivate_skill("turkish_nlp")
    assert manager.get_prompt_augmentation() == ""

    # Reactivate
    manager.activate_skill("turkish_nlp")
    assert "[Skill: turkish_nlp]" in manager.get_prompt_augmentation()


def test_builtin_computer_use_skill():
    builtin_dir = Path(__file__).parent.parent / "evren_agent" / "builtin_skills"
    manager = SkillManager()
    count = manager.discover_skills(additional_dirs=[builtin_dir])
    assert count > 0

    # Ensure computer-use is discovered
    assert "computer-use" in manager.skills
    skill = manager.get_skill("computer-use")
    assert skill is not None
    assert skill.name == "computer-use"
    assert "terminal" in skill.tags or "cli" in skill.tags
    assert "Execute shell commands" in skill.instructions

    # Test hyphen / underscore normalization
    assert "computer_use" in manager.skills
    assert manager.get_skill("computer_use") is skill
    assert manager.activate_skill("computer_use") is True
    assert skill.is_active is True
    assert manager.deactivate_skill("computer-use") is True
    assert skill.is_active is False


@pytest.mark.asyncio
async def test_agent_default_active_skills():
    from evren_agent.core.agent import Agent

    agent = Agent()
    await agent.initialize()

    active_names = [s.name for s in agent.skills.skills.values() if s.is_active]
    assert "code_assistant" in active_names
    assert "computer-use" in active_names

    aug = agent.skills.get_prompt_augmentation()
    assert "[Skill: computer-use]" in aug
    assert "[Skill: code_assistant]" in aug

    await agent.close()

