"""Run the single-concurrency background worker for Dashboard LLM tasks."""
from modules.blueprint.dashboard.llm_tasks import run_worker


if __name__ == "__main__":
    run_worker()
