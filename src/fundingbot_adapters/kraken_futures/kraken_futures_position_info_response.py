from typing import Any, cast

from pydantic import model_validator
from pydantic.dataclasses import dataclass as pdc_dataclass

from fundingbot_sdk.schemas.position_info import CCXTPositionInfoResponse


@pdc_dataclass(slots=True, frozen=True)
class KrakenFuturesPositionInfoResponse(CCXTPositionInfoResponse):
    """Снимок позиции ccxt с нормализацией полей источника.

    Контракт совпадает с ``CCXTPositionInfoResponse``. Дополнительно нормализуются:
    - поле symbol - конвертируется из символа с фиатной quote-частью в соответствующий символ со стейблкоином.
    """

    @model_validator(mode="before")
    @classmethod
    def _normalize_source_2(cls, data: object) -> object:
        """Привести входные данные к ожидаемой форме.

        Принимает словарь от ccxt: добавляет недостающие ``timestamp``/``datetime`` и
        приводит ``id`` к строке. Остальные поля валидируются базовым классом.
        """
        if not isinstance(data, dict):
            return data

        item: dict[str, Any] = dict(cast("dict[str, Any]", data))

        entry_price = item.get("entryPrice")
        contracts = item.get("contracts")
        contract_size = item.get("contractSize")
        if entry_price is not None and contracts is not None and contract_size is not None:
            item["notional"] = entry_price * contracts * contract_size

        item["hedged"] = False
        item["margin_mode"] = item["marginMode"]

        return item
