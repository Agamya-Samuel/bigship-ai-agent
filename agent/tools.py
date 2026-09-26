from __future__ import annotations

from typing import Annotated, Any, Literal

from bigship_sdk import BigshipClient
from bigship_sdk.models import (
    DomesticB2BOrderRequest,
    DomesticB2COrderRequest,
    HyperlocalOrderRequest,
    PlaceOrderRequest,
    RateCalculatorRequest as _SDKRateCalculatorRequest,
    SaveWarehouseRequest,
    UpdateWarehouseRequest,
    WarehouseListRequest,
)
from langchain_core.tools import tool
from langgraph.prebuilt.tool_node import ToolRuntime
from pydantic import BaseModel, BeforeValidator, Field

from agent.credentials import get_credential_store


def _format_result(response: Any) -> str:
    data: Any = getattr(response, "data", None)
    message: Any = getattr(response, "message", None)
    if data is not None and hasattr(data, "model_dump"):
        data = data.model_dump(mode="json", exclude_none=True)
    if not getattr(response, "status", True):
        return f"Error: {message}"
    if isinstance(data, list):
        return _format_list(data)
    return str(data)


def _format_list(items: list[dict]) -> str:
    if not items:
        return "No results."
    keys = list(items[0].keys())
    header = "| " + " | ".join(keys) + " |"
    separator = "|" + "|".join(["---"] * len(keys)) + "|"
    rows = []
    for item in items:
        row = "| " + " | ".join(str(item.get(k, "")) for k in keys) + " |"
        rows.append(row)
    return "\n".join([header, separator] + rows)


def _get_client(runtime: ToolRuntime) -> BigshipClient:
    thread_id = runtime.config.get("configurable", {}).get("thread_id", "")
    return get_credential_store().get_or_create_client(thread_id)


# ==================== CUSTOM INPUT MODELS ====================


class CreateOrderHyperlocalInput(BaseModel):
    segment_type: Literal["hyperlocal"] = "hyperlocal"
    MasterOrderPickUpLocation: int
    MasterOrderPaymentMode: int
    MasterOrderShippingName: str = Field(..., min_length=1)
    MasterOrderShippingEmail: str | None = None
    MasterOrderShippingMobileNo: float | str | int
    MasterOrderShippingZipCode: str = Field(..., pattern="^[0-9]{6}$")
    MasterOrderShippingCity: str = Field(..., min_length=1)
    MasterOrderShippingState: str = Field(..., min_length=1)
    MasterOrderShippingCountry: str = Field(default="India")
    MasterOrderShippingAddress: str = Field(..., min_length=1)
    MasterOrderShippingAddress2: str | None = None
    MasterOrderShippingLandmark: str | None = None
    MasterOrderShippingLatitude: str
    MasterOrderShippingLongitude: str
    OrderInvoiceNo: str | None = None
    MasterOrderInvoiceAmount: float = Field(..., gt=0)
    PackageTypeId: int = Field(..., gt=0)
    pickup_instructions: str | None = None
    additional_comments: str | None = None
    boxes: dict[str, Any]


class CreateOrderDomesticB2BInput(BaseModel):
    segment_type: Literal["domestic_b2b"] = "domestic_b2b"
    MasterOrderPickUpLocation: int
    MasterOrderPaymentMode: int
    MasterOrderShippingName: str = Field(..., min_length=1)
    MasterOrderShippingEmail: str | None = None
    MasterOrderShippingMobileNo: float | str | int
    MasterOrderShippingZipCode: str = Field(..., pattern="^[0-9]{6}$")
    MasterOrderShippingCity: str = Field(..., min_length=1)
    MasterOrderShippingState: str = Field(..., min_length=1)
    MasterOrderShippingCountry: str = Field(default="India")
    MasterOrderShippingAddress: str = Field(..., min_length=1)
    MasterOrderShippingAddress2: str | None = None
    MasterOrderShippingLandmark: str | None = None
    MasterOrderReturnLocation: int
    MasterOrderDate: str
    OrderInvoiceNo: str = Field(..., min_length=1)
    MasterOrderInvoiceAmount: float = Field(..., gt=0)
    MasterOrderCollectableAmount: str | None = None
    ProductName: str = Field(..., min_length=1)
    totalNumOfBoxes: int
    boxes: list[dict[str, Any]]


class CreateOrderDomesticB2CInput(BaseModel):
    segment_type: Literal["domestic_b2c"] = "domestic_b2c"
    MasterOrderPickUpLocation: int
    MasterOrderPaymentMode: int
    MasterOrderShippingName: str = Field(..., min_length=1)
    MasterOrderShippingEmail: str | None = None
    MasterOrderShippingMobileNo: float | str | int
    MasterOrderShippingZipCode: str = Field(..., pattern="^[0-9]{6}$")
    MasterOrderShippingCity: str = Field(..., min_length=1)
    MasterOrderShippingState: str = Field(..., min_length=1)
    MasterOrderShippingCountry: str = Field(default="India")
    MasterOrderShippingAddress: str = Field(..., min_length=1)
    MasterOrderShippingAddress2: str | None = None
    MasterOrderShippingLandmark: str | None = None
    MasterOrderReturnLocation: int
    MasterOrderDate: str
    OrderInvoiceNo: str = Field(..., min_length=1)
    MasterOrderInvoiceAmount: float = Field(..., gt=0)
    totalNumOfBoxes: int
    boxes: list[dict[str, Any]]


CreateOrderInput = Annotated[
    CreateOrderHyperlocalInput | CreateOrderDomesticB2BInput | CreateOrderDomesticB2CInput,
    Field(discriminator="segment_type"),
]


# ==================== PROFILE ====================


@tool
def get_profile(
    runtime: ToolRuntime,
) -> str:
    """Get the merchant's profile information including wallet balance."""
    client = _get_client(runtime)
    response = client.get_profile()
    return _format_result(response)


# ==================== WAREHOUSE ====================


@tool
def save_warehouse(
    payload: SaveWarehouseRequest,
    runtime: ToolRuntime,
) -> str:
    """Save a new warehouse.

    Required fields:
    - segment_type: "hyperlocal" or "local"
    - warehouseContactPerson: contact person name
    - warehouseAddressPhone: 10-digit phone number
    - warehouseState: state name
    - warehouseCity: city name
    - warehousePinCode: 6-digit pincode
    - warehouseAddressLine1: address line 1 (3-75 chars)
    - warehouseAddressLandMark: landmark (3-50 chars)
    - warehouseCountry: default "India"
    """
    client = _get_client(runtime)
    response = client.save_warehouse(payload)
    return _format_result(response)


@tool
def get_warehouse_list(
    params: WarehouseListRequest,
    runtime: ToolRuntime,
) -> str:
    """Get the list of warehouses.

    Required fields:
    - page: page number
    - perPage: items per page
    - segment_type: "hyperlocal" or "local"
    - status: optional filter (e.g., "active")
    """
    client = _get_client(runtime)
    response = client.get_warehouse_list(params)
    return _format_result(response)


@tool
def update_warehouse(
    payload: UpdateWarehouseRequest,
    runtime: ToolRuntime,
) -> str:
    """Update an existing warehouse.

    Required fields:
    - warehouseId: ID of the warehouse to update
    - warehouseName: warehouse name
    - warehouseContactPerson: contact person name
    - warehouseAddressPhone: 10-digit phone number
    - warehouseState: state name
    - warehouseCity: city name
    - warehousePinCode: 6-digit pincode
    - warehouseAddressLine1: address line 1 (3-75 chars)
    - warehouseAddressLandMark: landmark (3-50 chars)
    - warehouseCountry: default "India"
    """
    client = _get_client(runtime)
    response = client.update_warehouse(payload)
    return _format_result(response)


# ==================== REFERENCE DATA ====================


@tool
def get_package_types(
    runtime: ToolRuntime,
) -> str:
    """Get the list of available package types for hyperlocal shipments."""
    client = _get_client(runtime)
    response = client.get_package_types()
    return _format_result(response)


@tool
def get_payment_modes(
    segment_type: str,
    runtime: ToolRuntime,
) -> str:
    """Get available payment modes for a given segment type.

    segment_type examples: "hyperlocal", "domestic_b2b", "domestic_b2c"
    """
    client = _get_client(runtime)
    response = client.get_payment_modes(segment_type)
    return _format_result(response)


@tool
def get_risk_types(
    runtime: ToolRuntime,
) -> str:
    """Get the list of available risk types for domestic shipments."""
    client = _get_client(runtime)
    response = client.get_risk_types()
    return _format_result(response)


# ==================== RATE CALCULATOR ====================


def _coerce_to_str(v: Any) -> Any:
    if v is None or isinstance(v, str):
        return v
    return str(v)


_StrLike = Annotated[Any, BeforeValidator(_coerce_to_str)]


class RateCalculatorRequest(BaseModel):
    """Input shim for the rate calculator tool.

    Mirrors the SDK's ``RateCalculatorRequest`` but coerces the three fields
    the LLM commonly emits as JSON numbers (``sourcePincode``, ``destPincode``,
    ``codAmount``) to strings before the SDK's strict regex validation runs.
    """

    segment_type: str
    sourcePincode: _StrLike
    destPincode: _StrLike
    invoiceValue: float = Field(..., gt=0)
    paymentModeId: int
    codAmount: _StrLike | None = None
    riskTypeId: int
    boxes: list[dict[str, Any]]


@tool
def calculate_rate(
    payload: RateCalculatorRequest,
    runtime: ToolRuntime,
) -> str:
    """Calculate shipping rates for a shipment.

    Required fields:
    - segment_type: "domestic_b2b" or "domestic_b2c"
    - sourcePincode: 6-digit source pincode (string or int)
    - destPincode: 6-digit destination pincode (string or int)
    - invoiceValue: invoice value (>0)
    - paymentModeId: payment mode ID
    - riskTypeId: risk type ID
    - codAmount: optional COD amount (string or number; auto-set to invoiceValue when COD + None)
    - boxes: list of boxes with box_length, box_width, box_height, box_dead_weight, no_of_box
    """
    raw = payload.model_dump(mode="json", exclude_none=True)
    if raw.get("codAmount") is None and raw.get("paymentModeId") == 2:
        raw["codAmount"] = str(raw["invoiceValue"])
    sdk_payload = _SDKRateCalculatorRequest(**raw)
    client = _get_client(runtime)
    response = client.calculate_rate(sdk_payload)
    return _format_result(response)


# ==================== ORDER LIFECYCLE ====================


@tool
def create_order(
    payload: CreateOrderInput,
    runtime: ToolRuntime,
) -> str:
    """Create a new shipment order.

    The payload must match one of these segment types:

    hyperlocal:
    - segment_type: "hyperlocal"
    - MasterOrderPickUpLocation: pickup warehouse ID
    - MasterOrderPaymentMode: payment mode ID
    - MasterOrderShippingName: recipient name
    - MasterOrderShippingEmail: recipient email
    - MasterOrderShippingMobileNo: recipient mobile
    - MasterOrderShippingZipCode: 6-digit destination pincode
    - MasterOrderShippingCity: destination city
    - MasterOrderShippingState: destination state
    - MasterOrderShippingCountry: default "India"
    - MasterOrderShippingAddress: address
    - MasterOrderShippingLatitude: latitude
    - MasterOrderShippingLongitude: longitude
    - OrderInvoiceNo: optional invoice number
    - MasterOrderInvoiceAmount: invoice amount (>0)
    - PackageTypeId: package type ID
    - pickup_instructions: optional
    - additional_comments: optional
    - boxes: dict with box details

    domestic_b2b:
    - segment_type: "domestic_b2b"
    - MasterOrderPickUpLocation: pickup warehouse ID
    - MasterOrderPaymentMode: payment mode ID
    - MasterOrderShippingName: recipient name
    - MasterOrderShippingEmail: recipient email
    - MasterOrderShippingMobileNo: recipient mobile
    - MasterOrderShippingZipCode: 6-digit destination pincode
    - MasterOrderShippingCity: destination city
    - MasterOrderShippingState: destination state
    - MasterOrderShippingCountry: default "India"
    - MasterOrderShippingAddress: address
    - MasterOrderReturnLocation: return warehouse ID
    - MasterOrderDate: order date
    - OrderInvoiceNo: invoice number
    - MasterOrderInvoiceAmount: invoice amount (>0)
    - MasterOrderCollectableAmount: optional collectable amount
    - ProductName: product name
    - totalNumOfBoxes: total boxes
    - boxes: list of box dicts

    domestic_b2c: same as domestic_b2b without MasterOrderCollectableAmount and ProductName
    """
    client = _get_client(runtime)
    raw = payload.model_dump(mode="json", exclude_none=True)
    segment_type = raw.get("segment_type")
    model: Any
    if segment_type == "hyperlocal":
        model = HyperlocalOrderRequest(**raw)
    elif segment_type == "domestic_b2b":
        model = DomesticB2BOrderRequest(**raw)
    elif segment_type == "domestic_b2c":
        model = DomesticB2COrderRequest(**raw)
    else:
        raise ValueError(f"Unknown segment_type: {segment_type}")
    response = client.create_order(model)
    return _format_result(response)


@tool
def get_serviceable_couriers(
    order_id: str,
    runtime: ToolRuntime,
) -> str:
    """Get the list of serviceable couriers for a given order.

    order_id: the CustomGlobalOrderId or MasterCustomOrderId of the order
    """
    client = _get_client(runtime)
    response = client.get_serviceable_couriers(order_id)
    return _format_result(response)


@tool
def place_order(
    payload: PlaceOrderRequest,
    runtime: ToolRuntime,
) -> str:
    """Place/confirm an order with a selected courier.

    Required fields:
    - MasterCustomOrderId: the order ID
    - courierId: ID of the selected courier
    - invoiceType: optional invoice type
    - riskTypeId: optional risk type ID
    """
    client = _get_client(runtime)
    response = client.place_order(payload)
    return _format_result(response)


@tool
def cancel_order(
    order_id: str,
    runtime: ToolRuntime,
) -> str:
    """Cancel an order by its ID.

    order_id: the CustomGlobalOrderId of the order to cancel
    """
    client = _get_client(runtime)
    response = client.cancel_order(order_id)
    return _format_result(response)


# ==================== TRACKING & DETAILS ====================


@tool
def track_order(
    order_id: str,
    runtime: ToolRuntime,
) -> str:
    """Track the current status and history of an order.

    order_id: the CustomGlobalOrderId of the order to track
    """
    client = _get_client(runtime)
    response = client.track_order(order_id)
    return _format_result(response)


@tool
def get_order_detail(
    order_id: str,
    runtime: ToolRuntime,
) -> str:
    """Get detailed information about an order.

    order_id: the MasterCustomOrderId of the order
    """
    client = _get_client(runtime)
    response = client.get_order_detail(order_id)
    return _format_result(response)


@tool
def download_document(
    order_id: str,
    document_type: str,
    runtime: ToolRuntime,
) -> str:
    """Download a shipment document (invoice, label, ewaybill, manifest).

    order_id: the CustomGlobalOrderId of the order
    document_type: one of "invoice", "label", "ewaybill", "manifest"
    """
    client = _get_client(runtime)
    response = client.download_document(order_id, document_type)
    return _format_result(response)


ALL_TOOLS = [
    get_profile,
    save_warehouse,
    get_warehouse_list,
    update_warehouse,
    get_package_types,
    get_payment_modes,
    get_risk_types,
    calculate_rate,
    create_order,
    get_serviceable_couriers,
    place_order,
    cancel_order,
    track_order,
    get_order_detail,
    download_document,
]
