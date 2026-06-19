# 本地启动命令

## 后端（FastAPI，端口 8000）

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

健康检查：http://localhost:8000/health  
API 文档：http://localhost:8000/docs

## 前端（Next.js，端口 3000）

```bash
cd frontend
npm run dev
```

访问地址：http://localhost:3000

---

**注意**：后端依赖 `backend/.env` 中的环境变量，首次启动前确认该文件已配置。
