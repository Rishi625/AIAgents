from dataclasses import dataclass
import os


@dataclass
class AgentConfig:
    api_key: str
    model: str = "gemini-3.0-flash"
    max_iterations: int = 5
    max_files_in_context: int = 20
    max_chars_per_file: int = 4000
    enable_reviewer: bool = True

    @classmethod
    def from_env(cls) -> "AgentConfig":
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required in your environment or .env file.")
        return cls(
            api_key=api_key,
            model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            max_iterations=int(os.getenv("MAX_AGENT_ITERATIONS", "5")),
            max_files_in_context=int(os.getenv("MAX_FILES_IN_CONTEXT", "20")),
            max_chars_per_file=int(os.getenv("MAX_CHARS_PER_FILE", "4000")),
            enable_reviewer=os.getenv("ENABLE_REVIEWER", "true").strip().lower() in {"1", "true", "yes"},
        )
