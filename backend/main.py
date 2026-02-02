from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import auth, import_excel, metadata, query, export, templates, reports

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router)
app.include_router(import_excel.router)
app.include_router(metadata.router)
app.include_router(query.router)
app.include_router(export.router)
app.include_router(templates.router)
app.include_router(reports.router)


@app.get("/health")
def health():
    return {"status": "ok"}
