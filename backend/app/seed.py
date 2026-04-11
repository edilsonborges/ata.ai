import asyncio
from sqlmodel import select
from app.config import get_settings
from app.db import get_session
from app.models import User, ProviderCredential
from app.security import hash_password


DEFAULT_PROVIDERS = [
    ("anthropic", "claude-opus-4-6"),
    ("openai", "gpt-4o"),
    ("openrouter", "anthropic/claude-3.5-sonnet"),
    ("claude_cli", "claude-opus-4-6"),
]


async def run() -> None:
    settings = get_settings()
    async with get_session() as s:
        result = await s.exec(select(User).where(User.email == settings.admin_email))
        if result.first():
            print(f"admin {settings.admin_email} already exists")
            return

        admin = User(
            email=settings.admin_email,
            password_hash=hash_password(settings.admin_password),
            role="admin",
        )
        s.add(admin)
        await s.flush()

        for provider, default_model in DEFAULT_PROVIDERS:
            s.add(ProviderCredential(
                user_id=admin.id,
                provider=provider,
                default_model=default_model,
                enabled=False,
            ))

        await s.commit()
        print(f"seeded admin {settings.admin_email}")


if __name__ == "__main__":
    asyncio.run(run())
