"""
API 接口测试
使用 httpx 进行 HTTP 接口测试
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database import Base, engine
from app.main import app


def unique_username(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


@pytest_asyncio.fixture
async def client():
    """创建异步测试客户端"""
    Base.metadata.create_all(bind=engine)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """测试健康检查端点"""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    """测试用户注册"""
    username = unique_username("register")
    payload = {
        "username": username,
        "password": "testpass123",
        "email": f"{username}@example.com",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert data["data"]["username"] == username


@pytest.mark.asyncio
async def test_login(client: AsyncClient):
    """测试用户登录"""
    username = unique_username("login")

    # 先注册
    await client.post("/api/v1/auth/register", json={
        "username": username,
        "password": "testpass123",
    })

    # 登录
    response = await client.post("/api/v1/auth/login", json={
        "username": username,
        "password": "testpass123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data["data"]
    assert "refresh_token" in data["data"]


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """测试错误密码登录"""
    response = await client.post("/api/v1/auth/login", json={
        "username": unique_username("nonexistent"),
        "password": "wrong",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_interview_session_flow_and_user_isolation(client: AsyncClient):
    """测试 AI 面试完整流程及用户数据隔离"""
    first_username = unique_username("interview_owner")
    await client.post("/api/v1/auth/register", json={
        "username": first_username,
        "password": "testpass123",
    })
    login_response = await client.post("/api/v1/auth/login", json={
        "username": first_username,
        "password": "testpass123",
    })
    first_token = login_response.json()["data"]["access_token"]
    first_headers = {"Authorization": f"Bearer {first_token}"}

    create_response = await client.post(
        "/api/v1/interview/sessions",
        headers=first_headers,
        json={
            "title": "后端开发模拟面试",
            "target_position": "后端开发工程师",
            "interview_type": "technical",
            "difficulty": "medium",
            "question_count": 2,
            "answer_mode": "text",
        },
    )
    assert create_response.status_code == 200
    session_id = create_response.json()["data"]["id"]
    assert create_response.json()["data"]["status"] == "pending"

    start_response = await client.post(
        f"/api/v1/interview/sessions/{session_id}/start",
        headers=first_headers,
    )
    assert start_response.status_code == 200
    assert start_response.json()["data"]["status"] == "in_progress"
    assert len(start_response.json()["data"]["turns"]) == 1

    answer_response = await client.post(
        f"/api/v1/interview/sessions/{session_id}/answer",
        headers=first_headers,
        json={
            "answer_text": "首先我会确认问题边界，其次通过日志和监控定位原因，最后补充自动化测试并复盘结果。",
            "answer_duration_seconds": 60,
        },
    )
    assert answer_response.status_code == 200
    assert len(answer_response.json()["data"]["turns"]) == 2
    assert answer_response.json()["data"]["turns"][0]["score"] is not None

    detail_response = await client.get(
        f"/api/v1/interview/sessions/{session_id}",
        headers=first_headers,
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["id"] == session_id
    assert detail_response.json()["data"]["turns"][0]["answered_at"] is not None

    finish_response = await client.post(
        f"/api/v1/interview/sessions/{session_id}/finish",
        headers=first_headers,
    )
    assert finish_response.status_code == 200
    assert finish_response.json()["data"]["status"] == "finished"
    assert finish_response.json()["data"]["total_score"] > 0

    report_response = await client.get(
        f"/api/v1/interview/sessions/{session_id}/report",
        headers=first_headers,
    )
    assert report_response.status_code == 200
    assert report_response.json()["data"]["session_id"] == session_id
    assert report_response.json()["data"]["turn_performance"]
    assert report_response.json()["data"]["suggestions"]

    second_username = unique_username("interview_other")
    await client.post("/api/v1/auth/register", json={
        "username": second_username,
        "password": "testpass123",
    })
    second_login_response = await client.post("/api/v1/auth/login", json={
        "username": second_username,
        "password": "testpass123",
    })
    second_token = second_login_response.json()["data"]["access_token"]
    second_headers = {"Authorization": f"Bearer {second_token}"}

    forbidden_response = await client.get(
        f"/api/v1/interview/sessions/{session_id}",
        headers=second_headers,
    )
    assert forbidden_response.status_code in (403, 404)
