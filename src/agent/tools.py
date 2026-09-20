from __future__ import annotations

from typing import Annotated, Any, Literal

from bigship_sdk import BigshipClient
from bigship_sdk.models import (
    DomesticB2BOrderRequest,
    DomesticB2COrderRequest,
    HyperlocalOrderRequest,
    PlaceOrderRequest,
    RateCalculatorRequest,
    SaveWarehouseRequest,
    UpdateWarehouseRequest,
    WarehouseListRequest,
)
from langchain_core.tools import InjectedToolArg, tool
from pydantic import BaseModel, Field

from agent.credentials import get_credential_store


def _format_result(response: Any) -> str:
    if response.status is True and response.data is not None:
        if hasattr(response.data, "model_dump"):
            return str(response.data.model_dump(mode="json", exclude_none=True))
        return str(response.data)
    return f"Error: {response.message}"


def _get_client(thread_id: str) -> BigshipClient:
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
    thread_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Get the merchant's profile information including wallet balance."""
    client = _get_client(thread_id)
    response = client.get_profile()
    return _format_result(response)


# ==================== WAREHOUSE ====================


@tool
def save_warehouse(
    payload: SaveWarehouseRequest,
    thread_id: Annotated[str, InjectedToolArg] = "",
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
    client = _get_client(thread_id)
    response = client.save_warehouse(payload)
    return _format_result(response)


@tool
def get_warehouse_list(
    params: WarehouseListRequest,
    thread_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Get the list of warehouses.

    Required fields:
    - page: page number
    - perPage: items per page
    - segment_type: "hyperlocal" or "local"
    - status: optional filter (e.g., "active")
    """
    client = _get_client(thread_id)
    response = client.get_warehouse_list(params)
    return _format_result(response)


@tool
def update_warehouse(
    payload: UpdateWarehouseRequest,
    thread_id: Annotated[str, InjectedToolArg] = "",
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
    client = _get_client(thread_id)
    response = client.update_warehouse(payload)
    return _format_result(response)


# ==================== REFERENCE DATA ====================


@tool
def get_package_types(
    thread_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Get the list of available package types for hyperlocal shipments."""
    client = _get_client(thread_id)
    response = client.get_package_types()
    return _format_result(response)


@tool
def get_payment_modes(
    segment_type: str,
    thread_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Get available payment modes for a given segment type.

    segment_type examples: "hyperlocal", "domestic_b2b", "domestic_b2c"
    """
    client = _get_client(thread_id)
    response = client.get_payment_modes(segment_type)
    return _format_result(response)


@tool
def get_risk_types(
    thread_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Get the list of available risk types for domestic shipments."""
    client = _get_client(thread_id)
    response = client.get_risk_types()
    return _format_result(response)


# ==================== RATE CALCULATOR ====================


@tool
def calculate_rate(
    payload: RateCalculatorRequest,
    thread_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Calculate shipping rates for a shipment.

    Required fields:
    - segment_type: "domestic_b2b" or "domestic_b2c"
    - sourcePincode: 6-digit source pincode
    - destPincode: 6-digit destination pincode
    - invoiceValue: invoice value (>0)
    - paymentModeId: payment mode ID
    - riskTypeId: risk type ID
    - codAmount: optional COD amount
    - boxes: list of boxes with box_length, box_width, box_height, box_dead_weight, no_of_box
    """
    client = _get_client(thread_id)
    response = client.calculate_rate(payload)
    return _format_result(response)


# ==================== ORDER LIFECYCLE ====================


@tool
def create_order(
    payload: CreateOrderInput,
    thread_id: Annotated[str, InjectedToolArg] = "",
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
    client = _get_client(thread_id)
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
    thread_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Get the list of serviceable couriers for a given order.

    order_id: the CustomGlobalOrderId or MasterCustomOrderId of the order
    """
    client = _get_client(thread_id)
    response = client.get_serviceable_couriers(order_id)
    return _format_result(response)


@tool
def place_order(
    payload: PlaceOrderRequest,
    thread_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Place/confirm an order with a selected courier.

    Required fields:
    - MasterCustomOrderId: the order ID
    - courierId: ID of the selected courier
    - invoiceType: optional invoice type
    - riskTypeId: optional risk type ID
    """
    client = _get_client(thread_id)
    response = client.place_order(payload)
    return _format_result(response)


@tool
def cancel_order(
    order_id: str,
    thread_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Cancel an order by its ID.

    order_id: the CustomGlobalOrderId of the order to cancel
    """
    client = _get_client(thread_id)
    response = client.cancel_order(order_id)
    return _format_result(response)


# ==================== TRACKING & DETAILS ====================


@tool
def track_order(
    order_id: str,
    thread_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Track the current status and history of an order.

    order_id: the CustomGlobalOrderId of the order to track
    """
    client = _get_client(thread_id)
    response = client.track_order(order_id)
    return _format_result(response)


@tool
def get_order_detail(
    order_id: str,
    thread_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Get detailed information about an order.

    order_id: the MasterCustomOrderId of the order
    """
    client = _get_client(thread_id)
    response = client.get_order_detail(order_id)
    return _format_result(response)


@tool
def download_document(
    order_id: str,
    document_type: str,
    thread_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Download a shipment document (invoice, label, ewaybill, manifest).

    order_id: the CustomGlobalOrderId of the order
    document_type: one of "invoice", "label", "ewaybill", "manifest"
    """
    client = _get_client(thread_id)
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
