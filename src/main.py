"""Главный модуль приложения корпоративного микроблога FastAPI.

Инициализирует сервер, подключает маршрутизаторы пользователей и твитов,
монтирует директории со статическими файлами фронтенда и загружаемых медиа,
а также настраивает глобальные кастомные обработчики системных ошибок.
"""

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from router_tweets import router as router_tweets
from router_users import router as router_users
from schemas import ErrorResponse

app = FastAPI(title="Corporate Twitter")

app.include_router(router_users)
app.include_router(router_tweets)

BASE_DIR: Path = Path(__file__).resolve().parent.parent
static_path: Path = BASE_DIR / "static"
frontend_path: Path = BASE_DIR / "frontend_dist"

(static_path / "medias").mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Глобальный перехватчик и обработчик стандартных ошибок HTTPException.

    Args:
        request: Объект входящего HTTP-запроса, вызвавшего исключение.
        exc: Экземпляр возникшего исключения с метаданными ошибки.

    Returns:
        JSONResponse: Структурированный JSON-ответ с описанием ошибки.
    """
    error_data = ErrorResponse(
        result=False,
        error_type="BackendError",
        error_message=str(exc.detail),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_data.model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Глобальный обработчик ошибок автоматической валидации входных данных Pydantic.

    Args:
        request: Объект входящего HTTP-запроса, вызвавшего исключение.
        exc: Экземпляр возникшего исключения с детальным списком несоответствий типов.

    Returns:
        JSONResponse: Ответ с кодом 400 и кастомной структурой ошибок по ТЗ.
    """
    error_data = ErrorResponse(
        result=False,
        error_type="ValidationError",
        error_message=json.dumps(exc.errors(), default=str),
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=error_data.model_dump(),
    )


@app.exception_handler(Exception)
async def universal_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Универсальный глобальный перехватчик любых непредвиденных системных исключений.

    Args:
        request: Объект входящего HTTP-запроса, вызвавшего исключение.
        exc: Экземпляр базового непредвиденного исключения Python.

    Returns:
        JSONResponse: Ответ с кодом 500 для предотвращения утечки системных логов.
    """
    error_data = ErrorResponse(
        result=False,
        error_type="CriticalError",
        error_message=str(exc),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_data.model_dump(),
    )
