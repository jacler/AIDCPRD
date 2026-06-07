from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_settings import AppSetting


class AppSettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_value(self, key: str) -> dict | None:
        row = await self.session.get(AppSetting, key)
        return row.value if row else None

    async def upsert(self, key: str, value: dict) -> dict:
        row = await self.session.get(AppSetting, key)
        if row is None:
            row = AppSetting(key=key, value=value)
            self.session.add(row)
        else:
            row.value = value
        await self.session.flush()
        return row.value
