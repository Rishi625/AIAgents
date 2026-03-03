from google import genai
from google.genai import errors, types


def check_api_limit_status(api_key: str, model: str) -> tuple[bool, str]:
    """
    Run a small live request to validate key/model access and quota availability.
    """
    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model=model,
            config=types.GenerateContentConfig(max_output_tokens=8, temperature=0),
            contents=[types.Content(role="user", parts=[types.Part(text="ping")])],
        )
        usage = getattr(response, "usage_metadata", None)
        if usage:
            prompt_tokens = getattr(usage, "prompt_token_count", "n/a")
            candidate_tokens = getattr(usage, "candidates_token_count", "n/a")
            return (
                True,
                (
                    "API check passed.\n"
                    f"Model: {model}\n"
                    f"Prompt tokens: {prompt_tokens}\n"
                    f"Candidate tokens: {candidate_tokens}"
                ),
            )
        return True, f"API check passed.\nModel: {model}"
    except errors.ClientError as exc:
        status_code = getattr(exc, "status_code", "unknown")
        message = str(exc)
        if "429" in message or "RESOURCE_EXHAUSTED" in message:
            return (
                False,
                (
                    "API check failed: quota/rate limit issue.\n"
                    f"Status: {status_code}\n"
                    f"Model: {model}\n"
                    f"Details: {message}\n\n"
                    "Action: verify billing/project on the same API key, check rate-limit page, "
                    "or switch GEMINI_MODEL."
                ),
            )
        return (
            False,
            (
                "API check failed.\n"
                f"Status: {status_code}\n"
                f"Model: {model}\n"
                f"Details: {message}"
            ),
        )
