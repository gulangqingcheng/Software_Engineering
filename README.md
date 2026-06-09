# 智能面试助手

智能面试助手是一个面向求职面试准备场景的 Web 应用。项目由 Vue 3 前端、FastAPI 后端、MySQL、Redis、ChromaDB 向量库以及外部大模型/语音识别服务组成，主要提供账号登录、智能对话、简历分析、面试录音分析、面试题生成、我的题库和个人资料维护等功能。


## 功能概览

| 功能模块 | 实现内容 |
| --- | --- |
| 用户认证 | 注册、登录、刷新令牌、获取当前用户信息，使用 JWT 进行接口鉴权。 |
| 智能对话 | 基于 SSE 返回流式回答，支持会话列表、历史消息、文件上传和报告产物查看/下载。 |
| Agent 编排 | 后端 `orchestrator` 根据用户输入和附件类型选择简历、录音、面试题或普通对话处理路径。 |
| 简历分析 | 支持上传 PDF、DOC、DOCX 简历，进行文本提取、视觉模型辅助解析、简历评价、查重和违规内容检查。 |
| 录音分析 | 支持上传面试录音，结合 DashScope/阿里云语音识别进行转写，并生成面试表现分析与问题提取结果。 |
| 面试题生成 | 根据岗位、技能、数量、难度等条件生成面试题，结合 RAG 知识库和 Tavily 搜索增强上下文。 |
| 我的题库 | 查看、创建、编辑、删除个人面试题，并提供重复题检查和处理接口。 |
| 个人中心 | 维护头像、用户名、密码、教育背景、目标岗位、技能证书、实习经历等信息。 |


## 技术栈

| 层次 | 技术 |
| --- | --- |
| 前端 | Vue 3、TypeScript、Vite、Pinia、Vue Router、Element Plus、Axios、Marked、DOMPurify |
| 后端 | Python 3.11、FastAPI、SQLAlchemy、PyMySQL、Pydantic Settings、SSE |
| 数据存储 | MySQL 8.0、Redis 7、ChromaDB |
| AI 能力 | OpenAI 兼容接口、DeepSeek 配置项、DashScope/Qwen VL、Paraformer、Sentence Transformers、Tavily |
| 文档与文件处理 | pdfplumber、python-docx、pdf2image、Poppler、Pillow |
| 部署 | Docker、Docker Compose、Nginx |

## 目录结构

```text
.
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── agents/          # Agent 实现与编排
│   │   ├── api/             # REST/SSE 接口
│   │   ├── models/          # SQLAlchemy ORM 模型
│   │   ├── schemas/         # Pydantic 数据结构
│   │   └── services/        # LLM、RAG、音频、解析、查重等服务
│   ├── tests/               # 后端接口测试
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                # Vue 3 前端
│   ├── src/
│   │   ├── api/             # 前端接口封装
│   │   ├── components/      # 通用组件
│   │   ├── stores/          # Pinia 状态
│   │   └── views/           # 页面视图
│   ├── Dockerfile
│   └── package.json
├── knowledge_base/          # RAG 知识库源文件目录
├── docker-compose.yml       # 容器编排
├── nginx.conf               # 前端容器 Nginx 配置
├── .env.example             # 环境变量示例
└── *.docx                   # 项目说明、部署说明、使用手册等文档
```

## 环境准备

本地开发建议准备以下环境：

- Python 3.11
- Node.js 22 或兼容版本
- MySQL 8.0
- Redis 7
- Docker Desktop 与 Docker Compose（使用容器部署时需要）
- 可访问外部模型服务的网络环境

后端启动时会执行 `Base.metadata.create_all(bind=engine)` 创建缺失的 ORM 表，并通过 `ensure_schema_compatibility` 对已有演示数据库补充少量兼容字段。

## 配置说明

复制环境变量模板：

```powershell
Copy-Item .env.example .env
```

至少需要关注以下配置：

| 配置项 | 说明 |
| --- | --- |
| `DATABASE_URL` | 后端连接 MySQL 的 SQLAlchemy 地址。Docker Compose 中会覆盖为 `db:3306`。 |
| `REDIS_URL` | Redis 连接地址。Docker Compose 中会覆盖为 `redis:6379`。 |
| `SECRET_KEY` | JWT 签名密钥，生产环境必须替换为随机强密钥。 |
| `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL_NAME` | 普通对话、编排和文本分析使用的大模型配置。 |
| `DASHSCOPE_API_KEY` | Qwen VL 与 Paraformer 等 DashScope 能力所需密钥。 |
| `TAVILY_API_KEY` | 面试题生成中的网络搜索增强能力所需密钥。 |
| `CHROMA_PERSIST_DIR` | ChromaDB 持久化目录。 |
| `UPLOAD_DIR` | 上传文件保存目录。 |
| `BACKEND_PORT`、`FRONTEND_PORT`、`REDIS_PORT` | Docker 暴露端口。 |

`.env.example` 中的密钥和密码仅为示例，不能直接用于生产环境。

## 本地开发运行

可以先用 Docker 启动依赖服务：

```powershell
docker compose up -d db redis
```

启动后端：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动前端：

```powershell
cd frontend
npm install
npm run dev
```

默认前端开发地址通常为 `http://localhost:5173`，后端接口地址为 `http://localhost:8000`，健康检查接口为 `http://localhost:8000/health`。

## Docker 部署

当前仓库已经包含可用的容器化部署文件：

- `backend/Dockerfile`
- `frontend/Dockerfile`
- `nginx.conf`
- `docker-compose.yml`

启动完整服务：

```powershell
docker compose up -d --build
```

查看容器状态：

```powershell
docker compose ps
```

当前 Compose 配置中：

- `db` 使用 `mysql:8.0`，仅在 Compose 网络内供后端访问，避免占用宿主机 `3306` 端口。
- `redis` 使用 `redis:7-alpine`，默认暴露到宿主机 `${REDIS_PORT:-6379}`。
- `backend` 构建自 `backend/Dockerfile`，默认暴露 `${BACKEND_PORT:-8000}`。
- `frontend` 构建自 `frontend/Dockerfile`，通过 Nginx 暴露 `${FRONTEND_PORT:-80}`。
- Nginx 将 `/api/` 和 `/uploads/` 反向代理到 `backend:8000`，并对 SSE 长连接关闭代理缓冲。
- `backend/uploads`、`artifacts`、`chroma_db`、`knowledge_base` 会挂载到后端容器中，便于文件、报告和向量库数据持久化。

如果宿主机 `80`、`6379` 或 `8000` 端口已被占用，可以在 `.env` 中调整 `FRONTEND_PORT`、`REDIS_PORT`、`BACKEND_PORT` 后重新启动。

## 主要接口

| 模块 | 路径前缀 |
| --- | --- |
| 健康检查 | `/health` |
| 认证 | `/api/v1/auth` |
| 对话与 SSE | `/api/v1/chat` |
| 简历 | `/api/v1/resume` |
| 录音 | `/api/v1/recording` |
| 面试题 | `/api/v1/question` |
| 个人中心 | `/api/v1/profile` |
| 后台管理预留 | `/api/v1/admin` |

开发环境下可访问 `http://localhost:8000/docs` 查看 FastAPI 自动生成的接口文档。

## 测试与校验

前端提供类型检查和构建命令：

```powershell
cd frontend
npm run type-check
npm run build
```

后端包含 `backend/tests/test_api.py`，主要覆盖健康检查、注册和登录等基础接口。需要注意，测试文件中的部分认证路径仍使用早期 `/api/auth/...` 写法，而当前实际接口前缀是 `/api/v1/auth/...`，运行完整测试前应先同步测试路径和测试数据库配置。

Docker 配置可用以下命令检查：

```powershell
docker compose config --quiet
```

## 文档

仓库中包含以下项目文档，可作为部署、使用和说明材料：

- `Agent架构说明.docx`
- `部署说明.docx`
- `使用手册.docx`
