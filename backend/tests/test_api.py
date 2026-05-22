import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_site_crud(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/sites/",
        json={
            "code": "S001",
            "name": "Main Site",
            "address": "123 Main St",
            "timezone": "UTC",
            "region": "Region A"
        }
    )

    assert response.status_code in [200, 201]

    data = response.json()

    assert data["code"] == "S001"

    site_id = data["id"]

    response = await async_client.get(f"/api/v1/sites/{site_id}")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_device_crud_and_soft_delete(async_client: AsyncClient):
    site_response = await async_client.post(
        "/api/v1/sites/",
        json={
            "code": "S002",
            "name": "Device Site",
            "address": "456 Device St",
            "timezone": "UTC",
            "region": "Region B"
        }
    )

    site_id = site_response.json()["id"]

    response = await async_client.post(
        "/api/v1/devices/",
        json={
            "site_id": site_id,
            "device_type": "NVR",
            "vendor": "Hikvision",
            "model": "DS-7608",
            "serial_number": "SN123456",
            "ip_address": "192.168.1.10",
            "status": "ONLINE"
        }
    )

    assert response.status_code in [200, 201]

    device = response.json()

    device_id = device["id"]

    response = await async_client.delete(
        f"/api/v1/devices/{device_id}"
    )

    assert response.status_code in [200, 204]

    response = await async_client.get(
        "/api/v1/devices/"
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_camera_crud_and_soft_delete(async_client: AsyncClient):
    site_response = await async_client.post(
        "/api/v1/sites/",
        json={
            "code": "S003",
            "name": "Camera Site",
            "address": "789 Camera St",
            "timezone": "UTC",
            "region": "Camera Region"
        }
    )

    site_id = site_response.json()["id"]

    device_response = await async_client.post(
        "/api/v1/devices/",
        json={
            "site_id": site_id,
            "device_type": "NVR",
            "vendor": "Hikvision",
            "model": "DS-7608",
            "serial_number": "SN999999",
            "ip_address": "192.168.1.20",
            "status": "ONLINE"
        }
    )

    device_id = device_response.json()["id"]

    response = await async_client.post(
        "/api/v1/cameras/",
        json={
            "device_id": device_id,
            "channel_number": 1,
            "name": "Front Door Camera",
            "rtsp_path": "/Streaming/Channels/101",
        }
    )

    assert response.status_code in [200, 201]

    camera = response.json()

    camera_id = camera["id"]

    response = await async_client.delete(
        f"/api/v1/cameras/{camera_id}"
    )

    assert response.status_code in [200, 204]


@pytest.mark.asyncio
async def test_telemetry_endpoints(async_client: AsyncClient):
    device_id = "00000000-0000-0000-0000-000000000000"

    response = await async_client.get(
        f"/api/v1/telemetry/current/{device_id}"
    )

    assert response.status_code in [200, 404]

    response = await async_client.get(
        "/api/v1/telemetry/history"
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_alerts_endpoints(async_client: AsyncClient):
    response = await async_client.get(
        "/api/v1/alerts/"
    )

    assert response.status_code == 200