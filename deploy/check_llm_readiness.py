from modules.services.llm_service import check_llm_readiness, get_llm_settings


def main() -> None:
    settings = get_llm_settings()
    check_llm_readiness()
    print(f"LLM readiness passed for {settings.provider} model {settings.model}.")


if __name__ == "__main__":
    main()
