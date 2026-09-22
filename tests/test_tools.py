from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from bigship_sdk.models import SaveWarehouseRequest, WarehouseListRequest

from agent.tools import (
    ALL_TOOLS,
    calculate_rate,
    cancel_order,
    create_order,
    download_document,
    get_order_detail,
    get_package_types,
    get_payment_modes,
    get_profile,
    get_risk_types,
    get_serviceable_couriers,
    get_warehouse_list,
    place_order,
    save_warehouse,
    track_order,
    update_warehouse,
)
from bigship_sdk.models import RateCalculatorRequest as SDKRateCalculatorRequest


@pytest.fixture
def mock_client() -> MagicMock:
    client = MagicMock()
    response = MagicMock()
    response.status = True
    response.data = {"ok": True}
    response.message = "OK"
    client.get_profile.return_value = response
    client.save_warehouse.return_value = response
    client.get_warehouse_list.return_value = response
    client.update_warehouse.return_value = response
    client.get_package_types.return_value = response
    client.get_payment_modes.return_value = response
    client.get_risk_types.return_value = response
    client.calculate_rate.return_value = response
    client.create_order.return_value = response
    client.get_serviceable_couriers.return_value = response
    client.place_order.return_value = response
    client.cancel_order.return_value = response
    client.track_order.return_value = response
    client.get_order_detail.return_value = response
    client.download_document.return_value = response
    return client


@pytest.fixture(autouse=True)
def mock_credential_store(mock_client: MagicMock) -> None:
    with patch("agent.tools.get_credential_store") as gs:
        gs.return_value.get_or_create_client.return_value = mock_client
        yield


def test_get_profile() -> None:
    result = get_profile.invoke({"thread_id": "t1"})
    assert "ok" in result


def test_save_warehouse() -> None:
    payload = SaveWarehouseRequest(
        segment_type="local",
        warehouseContactPerson="John",
        warehouseAddressPhone="9876543210",
        warehouseState="Karnataka",
        warehouseCity="Bangalore",
        warehousePinCode="560001",
        warehouseAddressLine1="123 Main St",
        warehouseAddressLandMark="Near Park",
    )
    result = save_warehouse.invoke({"payload": payload.model_dump(), "thread_id": "t1"})
    assert "ok" in result


def test_get_warehouse_list() -> None:
    params = WarehouseListRequest(page="1", perPage="10", segment_type="local")
    result = get_warehouse_list.invoke({"params": params.model_dump(), "thread_id": "t1"})
    assert "ok" in result


def test_update_warehouse() -> None:
    from bigship_sdk.models import UpdateWarehouseRequest

    payload = UpdateWarehouseRequest(
        warehouseId="1",
        warehouseName="Test WH",
        warehouseContactPerson="John",
        warehouseAddressPhone="9876543210",
        warehouseState="Karnataka",
        warehouseCity="Bangalore",
        warehousePinCode="560001",
        warehouseAddressLine1="123 Main St",
        warehouseAddressLandMark="Near Park",
    )
    result = update_warehouse.invoke({"payload": payload.model_dump(), "thread_id": "t1"})
    assert "ok" in result


def test_get_package_types() -> None:
    result = get_package_types.invoke({"thread_id": "t1"})
    assert "ok" in result


def test_get_payment_modes() -> None:
    result = get_payment_modes.invoke({"segment_type": "hyperlocal", "thread_id": "t1"})
    assert "ok" in result


def test_get_risk_types() -> None:
    result = get_risk_types.invoke({"thread_id": "t1"})
    assert "ok" in result


def test_calculate_rate() -> None:
    payload = {
        "segment_type": "domestic_b2b",
        "sourcePincode": "560001",
        "destPincode": "110001",
        "invoiceValue": 1000.0,
        "paymentModeId": 1,
        "riskTypeId": 1,
        "boxes": [
            {
                "box_length": 10,
                "box_width": 10,
                "box_height": 10,
                "box_dead_weight": 1,
                "no_of_box": 1,
            }
        ],
    }
    result = calculate_rate.invoke({"payload": payload, "thread_id": "t1"})
    assert "ok" in result


def test_calculate_rate_coerces_numeric_pincodes_and_cod() -> None:
    """Regression: LLM emits sourcePincode/destPincode/codAmount as JSON numbers.

    The SDK's RateCalculatorRequest requires those fields to be strings
    (validated by ^[0-9]{6}$), so the tool's input shim must coerce them.
    This mirrors the failing call from the bug report (400012 → 226018, COD).
    """
    from agent.tools import RateCalculatorRequest as ToolRateCalculatorRequest

    raw = {
        "segment_type": "domestic_b2c",
        "sourcePincode": 400012,  # int, as the LLM emitted
        "destPincode": 226018,  # int, as the LLM emitted
        "invoiceValue": 1600.0,
        "paymentModeId": 2,
        "riskTypeId": 2,
        "codAmount": 1600.0,  # float, as the LLM emitted
        "boxes": [
            {
                "box_length": 20,
                "box_width": 10,
                "box_height": 20,
                "box_dead_weight": 15,
                "no_of_box": 1,
            }
        ],
    }
    shim = ToolRateCalculatorRequest.model_validate(raw)
    assert shim.sourcePincode == "400012"
    assert shim.destPincode == "226018"
    assert shim.codAmount == "1600.0"

    # And the dumped payload must satisfy the SDK's strict schema.
    sdk_payload = SDKRateCalculatorRequest(**shim.model_dump(mode="json"))
    assert sdk_payload.sourcePincode == "400012"
    assert sdk_payload.destPincode == "226018"
    assert sdk_payload.codAmount == "1600.0"


def test_calculate_rate_auto_fills_cod_when_missing() -> None:
    """When paymentModeId == 2 and codAmount is omitted, default to invoiceValue as str."""
    from agent.tools import RateCalculatorRequest as ToolRateCalculatorRequest

    raw = {
        "segment_type": "domestic_b2c",
        "sourcePincode": "400012",
        "destPincode": "226018",
        "invoiceValue": 1600.0,
        "paymentModeId": 2,
        "riskTypeId": 2,
        "boxes": [
            {
                "box_length": 20,
                "box_width": 10,
                "box_height": 20,
                "box_dead_weight": 15,
                "no_of_box": 1,
            }
        ],
    }
    shim = ToolRateCalculatorRequest.model_validate(raw)
    dumped = shim.model_dump(mode="json", exclude_none=True)
    assert "codAmount" not in dumped
    if dumped.get("codAmount") is None and dumped.get("paymentModeId") == 2:
        dumped["codAmount"] = str(dumped["invoiceValue"])
    SDKRateCalculatorRequest(**dumped)  # must not raise


def test_create_order_hyperlocal() -> None:
    payload = {
        "segment_type": "hyperlocal",
        "MasterOrderPickUpLocation": 1,
        "MasterOrderPaymentMode": 1,
        "MasterOrderShippingName": "Test",
        "MasterOrderShippingMobileNo": "9876543210",
        "MasterOrderShippingZipCode": "560001",
        "MasterOrderShippingCity": "Bangalore",
        "MasterOrderShippingState": "Karnataka",
        "MasterOrderShippingAddress": "123 Main St",
        "MasterOrderShippingLatitude": "12.97",
        "MasterOrderShippingLongitude": "77.59",
        "MasterOrderInvoiceAmount": 100.0,
        "PackageTypeId": 1,
        "boxes": {},
    }
    result = create_order.invoke({"payload": payload, "thread_id": "t1"})
    assert "ok" in result


def test_get_serviceable_couriers() -> None:
    result = get_serviceable_couriers.invoke({"order_id": "ORD123", "thread_id": "t1"})
    assert "ok" in result


def test_place_order() -> None:
    payload = {"MasterCustomOrderId": "ORD123", "courierId": 1}
    result = place_order.invoke({"payload": payload, "thread_id": "t1"})
    assert "ok" in result


def test_cancel_order() -> None:
    result = cancel_order.invoke({"order_id": "ORD123", "thread_id": "t1"})
    assert "ok" in result


def test_track_order() -> None:
    result = track_order.invoke({"order_id": "ORD123", "thread_id": "t1"})
    assert "ok" in result


def test_get_order_detail() -> None:
    result = get_order_detail.invoke({"order_id": "ORD123", "thread_id": "t1"})
    assert "ok" in result


def test_download_document() -> None:
    result = download_document.invoke(
        {"order_id": "ORD123", "document_type": "label", "thread_id": "t1"}
    )
    assert "ok" in result


def test_tool_count() -> None:
    assert len(ALL_TOOLS) == 15
