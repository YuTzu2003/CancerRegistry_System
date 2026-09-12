"""Run the single-concurrency background worker for dashboard LLM tasks."""
from modules.services.llm_tasks import run_worker


if __name__ == "__main__":
    run_worker()