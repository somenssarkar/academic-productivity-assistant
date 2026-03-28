import yaml
from pathlib import Path
from typing import Optional
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Pydantic validation models (mirrors _schema.yaml)
# ---------------------------------------------------------------------------

class Question(BaseModel):
    question: str
    options: list[str]
    answer: str
    explanation: str = ""
    difficulty: int = 1


class Topic(BaseModel):
    id: str
    title: str
    sequence: int
    estimated_minutes: int = 45
    prerequisites: list[str] = []
    concepts: list[str] = []
    youtube_search_hints: list[str] = []
    questions: list[Question] = []


class Chapter(BaseModel):
    id: str
    title: str
    sequence: int
    topics: list[Topic]


class CurriculumMeta(BaseModel):
    board: str
    subject: str
    grade: int
    language: str = "English"


class CurriculumFile(BaseModel):
    curriculum: CurriculumMeta
    chapters: list[Chapter]


# ---------------------------------------------------------------------------
# Loader functions
# ---------------------------------------------------------------------------

_BASE_PATH = Path(__file__).parent.parent.parent / "data" / "curricula"


def load_curriculum(board: str, subject: str, grade: int) -> CurriculumFile:
    """Load and validate a single curriculum YAML file.

    Args:
        board: e.g. "cbse"
        subject: e.g. "math"
        grade: e.g. 8

    Returns:
        Validated CurriculumFile model.

    Raises:
        FileNotFoundError: if the YAML file does not exist.
        ValidationError: if the YAML does not match the schema.
    """
    path = _BASE_PATH / board.lower() / subject.lower() / f"grade-{grade}.yaml"
    if not path.exists():
        raise FileNotFoundError(
            f"Curriculum not found: {path}\n"
            f"Available: {list(_BASE_PATH.rglob('grade-*.yaml'))}"
        )
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return CurriculumFile.model_validate(raw)


def discover_curricula(base_path: Optional[Path] = None) -> dict[str, CurriculumFile]:
    """Scan the curriculum directory and return all available curricula.

    Returns:
        Dict keyed by "BOARD/subject/grade-N" → CurriculumFile
    """
    search_root = base_path or _BASE_PATH
    curricula: dict[str, CurriculumFile] = {}

    for yaml_file in sorted(search_root.rglob("grade-*.yaml")):
        if yaml_file.name.startswith("_"):
            continue
        try:
            raw = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
            cf = CurriculumFile.model_validate(raw)
            key = (
                f"{cf.curriculum.board.upper()}/"
                f"{cf.curriculum.subject.lower()}/"
                f"grade-{cf.curriculum.grade}"
            )
            curricula[key] = cf
        except Exception as exc:
            # Log but don't crash — bad YAML shouldn't block the whole system
            print(f"[curriculum_loader] Skipping {yaml_file}: {exc}")

    return curricula


def get_chapter(curriculum: CurriculumFile, chapter_id: str) -> Optional[Chapter]:
    """Look up a chapter by ID."""
    for chapter in curriculum.chapters:
        if chapter.id == chapter_id:
            return chapter
    return None


def get_topic(curriculum: CurriculumFile, topic_key: str) -> Optional[Topic]:
    """Look up a topic by dotted key (chapter_id.topic_id)."""
    parts = topic_key.split(".", 1)
    if len(parts) != 2:
        return None
    chapter_id, topic_id = parts
    chapter = get_chapter(curriculum, chapter_id)
    if chapter is None:
        return None
    for topic in chapter.topics:
        if topic.id == topic_id:
            return topic
    return None


def curriculum_to_context_string(curriculum: CurriculumFile, chapter_id: Optional[str] = None) -> str:
    """Serialize curriculum (or one chapter) to a compact string for LLM context injection.

    Keeps token count low: injects only the relevant chapter when chapter_id is given.
    """
    meta = curriculum.curriculum
    lines = [
        f"Board: {meta.board} | Subject: {meta.subject} | Grade: {meta.grade}",
        "",
    ]

    chapters_to_include = curriculum.chapters
    if chapter_id:
        chapter = get_chapter(curriculum, chapter_id)
        chapters_to_include = [chapter] if chapter else []

    for chapter in chapters_to_include:
        lines.append(f"## Chapter: {chapter.title} (id: {chapter.id})")
        for topic in sorted(chapter.topics, key=lambda t: t.sequence):
            prereqs = ", ".join(topic.prerequisites) if topic.prerequisites else "none"
            lines.append(f"  ### Topic {topic.sequence}: {topic.title} (id: {topic.id})")
            lines.append(f"      estimated_minutes: {topic.estimated_minutes}")
            lines.append(f"      prerequisites: {prereqs}")
            lines.append(f"      concepts: {', '.join(topic.concepts)}")
            if topic.youtube_search_hints:
                lines.append(f"      youtube_hints: {topic.youtube_search_hints[0]}")
            if topic.questions:
                lines.append(f"      questions: {len(topic.questions)} available")
        lines.append("")

    return "\n".join(lines)
