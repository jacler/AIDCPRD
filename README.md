# AIDC-CostPro

智算数据中心基础设施设计与成本拆解引擎。

## 项目结构

```
aidc-costpro/
├── frontend/               # Next.js 14+ (App Router, TypeScript)
│   ├── src/
│   │   ├── app/            # 页面路由
│   │   ├── components/     # UI & 业务组件
│   │   ├── lib/            # API 客户端, 工具函数
│   │   └── types/          # TypeScript 类型 (与后端 Pydantic 同步)
├── backend/                # FastAPI (Clean Architecture)
│   ├── app/
│   │   ├── api/            # 路由层 (Step 3)
│   │   ├── core/           # 配置, 数据库, 异常
│   │   ├── models/         # SQLAlchemy ORM
│   │   ├── schemas/        # Pydantic V2
│   │   ├── services/       # 核心算法 (Step 2)
│   │   └── repositories/   # CRUD (Step 3)
│   └── tests/
└── docker-compose.yml      # PostgreSQL 15 + Redis
```

## 快速启动

### 1. 启动基础设施

```bash
docker compose up -d
```

### 2. 后端

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

API 文档: http://localhost:8000/docs

### 3. 前端

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

访问: http://localhost:3000

## 开发进度

- [x] **Step 1** — 项目初始化、数据模型、核心配置
- [x] **Step 2** — 拓扑推导 & 5 维成本算法引擎 + 单元测试
- [x] **Step 3** — RESTful API 路由与 CRUD
- [x] **Step 4** — 前端 Designer 页面 & Zustand 状态管理
- [x] **Step 5** — CostWaterfall & RadarCompare 可视化组件
