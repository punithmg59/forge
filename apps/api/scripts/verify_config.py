"""Verify production configuration guards (Task 8.8 smoke helper)."""

from pydantic import ValidationError

from app.core.config import Settings


def main() -> None:
    try:
        Settings(app_env="production", secret_key="change-me")
        print("FAIL: production accepted weak SECRET_KEY")
    except ValidationError:
        print("OK: production rejects weak SECRET_KEY")

    dev = Settings(app_env="development", secret_key="change-me")
    print("OK: development allows default SECRET_KEY")
    print(f"OK: default CORS origins: {dev.cors_origin_list()}")

    prod = Settings(
        app_env="production",
        secret_key="secure-random-key-for-test-only",
        cors_origins="https://app.example.com",
    )
    print(f"OK: production CORS: {prod.cors_origin_list()}")


if __name__ == "__main__":
    main()
