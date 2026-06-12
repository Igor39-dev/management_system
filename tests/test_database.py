from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.src.database import check_db_connection


@pytest.mark.asyncio
async def test_check_db_connection_success() -> None:
    mock_engine = MagicMock()
    mock_connection = AsyncMock()
    mock_engine.connect.return_value.__aenter__ = AsyncMock(return_value=mock_connection)
    mock_engine.connect.return_value.__aexit__ = AsyncMock(return_value=None)
    mock_connection.execute = AsyncMock()

    with patch("backend.src.database.engine", mock_engine):
        assert await check_db_connection() is True


@pytest.mark.asyncio
async def test_check_db_connection_failure() -> None:
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = OSError("connection refused")

    with patch("backend.src.database.engine", mock_engine):
        assert await check_db_connection() is False
