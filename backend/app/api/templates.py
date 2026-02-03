from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.sys_user import SysUser
from app.models.chart_template import ChartTemplate
from app.schemas.chart_spec import ChartSpec
from app.services.template_service import load_templates, init_templates_to_db, resolve_template_params, resolve_block_query
from app.services.template_executor import execute_template
from app.models.metric_code_map import resolve_metric_id

router = APIRouter(prefix=f"{settings.API_V1_STR}/templates", tags=["templates"])


class TemplateCreate(BaseModel):
    name: str
    chart_type: str  # seasonality | timeseries
    spec_json: dict  # ChartSpec JSON
    is_public: bool = False


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    spec_json: Optional[dict] = None
    is_public: Optional[bool] = None


class TemplateInfo(BaseModel):
    id: int
    name: str
    chart_type: Optional[str]
    is_public: bool
    owner_id: Optional[int]
    created_at: str
    
    class Config:
        from_attributes = True


class TemplateDetail(TemplateInfo):
    spec_json: dict


class PresetTemplateExecuteRequest(BaseModel):
    params: Dict  # 用户参数（template_id从路径参数获取，不需要在请求体中）


@router.get("", response_model=List[TemplateInfo])
async def get_templates(
    scope: str = Query("mine", description="mine|public|all"),
    chart_type: Optional[str] = Query(None, description="seasonality|timeseries"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """获取模板列表"""
    query = db.query(ChartTemplate)
    
    # 根据scope过滤
    if scope == "mine":
        query = query.filter(ChartTemplate.owner_id == current_user.id)
    elif scope == "public":
        query = query.filter(ChartTemplate.is_public == True)
    # all: 不额外过滤
    
    # 根据chart_type过滤
    if chart_type:
        query = query.filter(ChartTemplate.chart_type == chart_type)
    
    templates = query.order_by(ChartTemplate.created_at.desc()).all()
    
    return [
        {
            "id": t.id,
            "name": t.name,
            "chart_type": t.chart_type,
            "is_public": t.is_public,
            "owner_id": t.owner_id,
            "created_at": t.created_at.isoformat()
        }
        for t in templates
    ]


@router.get("/preset", response_model=List[dict])
async def get_preset_templates():
    """获取8套预设模板配置（不存库，直接返回JSON）"""
    return load_templates()


@router.get("/preset/{template_id}", response_model=dict)
async def get_preset_template(template_id: str):
    """获取单个预设模板配置"""
    templates = load_templates()
    template = next((t for t in templates if t["template_id"] == template_id), None)
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Preset template {template_id} not found"
        )
    
    return template


@router.post("/preset/{template_id}/execute")
async def execute_preset_template(
    template_id: str,
    request_body: PresetTemplateExecuteRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """执行预设模板并返回数据"""
    templates = load_templates()
    template = next((t for t in templates if t["template_id"] == template_id), None)
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Preset template {template_id} not found"
        )
    
    # 使用路径参数中的template_id，忽略请求体中的（如果存在）
    try:
        result = execute_template(db, template, request_body.params)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Template execution failed: {str(e)}"
        )


@router.post("/init-preset")
async def init_preset_templates(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """初始化8套预设模板到数据库（仅admin可执行）"""
    from app.core.security import check_user_role
    
    if not check_user_role(current_user, ["admin"], db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can initialize preset templates"
        )
    
    try:
        init_templates_to_db(db)
        return {"message": "Preset templates initialized successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize templates: {str(e)}"
        )


@router.post("", response_model=TemplateDetail)
async def create_template(
    template: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """创建模板"""
    # 验证ChartSpec结构（可选，但建议）
    try:
        ChartSpec(**template.spec_json)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid ChartSpec: {str(e)}"
        )
    
    # 检查is_public权限（仅admin可发布公共模板）
    is_public = template.is_public
    if is_public:
        # 通过角色表检查权限
        from app.core.security import check_user_role
        if not check_user_role(current_user, ["admin"], db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admin can create public templates"
            )
    
    new_template = ChartTemplate(
        name=template.name,
        chart_type=template.chart_type,
        spec_json=template.spec_json,
        is_public=is_public,
        owner_id=current_user.id
    )
    
    db.add(new_template)
    db.commit()
    db.refresh(new_template)
    
    return {
        "id": new_template.id,
        "name": new_template.name,
        "chart_type": new_template.chart_type,
        "is_public": new_template.is_public,
        "owner_id": new_template.owner_id,
        "created_at": new_template.created_at.isoformat(),
        "spec_json": new_template.spec_json
    }


@router.get("/{template_id}", response_model=TemplateDetail)
async def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """获取模板详情"""
    import json
    import os
    log_path = r"d:\Workspace\hogprice-insight\.cursor\debug.log"
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps({"location":"templates.py:220","message":"get_template called","data":{"template_id":template_id,"current_user_id":current_user.id,"current_username":current_user.username},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"H1,H4"})+'\n')
    except: pass
    
    template = db.query(ChartTemplate).filter(ChartTemplate.id == template_id).first()
    
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps({"location":"templates.py:223","message":"Template query result","data":{"found":template is not None,"template_id":template.id if template else None,"is_public":template.is_public if template else None,"owner_id":template.owner_id if template else None},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"H1,H4"})+'\n')
    except: pass
    
    if not template:
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"location":"templates.py:226","message":"Template not found","data":{"template_id":template_id},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"H1"})+'\n')
        except: pass
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    # 权限检查：只能查看自己的或公共模板
    if not template.is_public and template.owner_id != current_user.id:
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"location":"templates.py:231","message":"Access denied","data":{"template_id":template_id,"template_owner_id":template.owner_id,"current_user_id":current_user.id,"is_public":template.is_public},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"H4"})+'\n')
        except: pass
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps({"location":"templates.py:242","message":"Returning template","data":{"template_id":template.id,"chart_type":template.chart_type,"has_spec_json":bool(template.spec_json)},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"H1,H2"})+'\n')
    except: pass
    
    return {
        "id": template.id,
        "name": template.name,
        "chart_type": template.chart_type,
        "is_public": template.is_public,
        "owner_id": template.owner_id,
        "created_at": template.created_at.isoformat(),
        "spec_json": template.spec_json
    }


@router.put("/{template_id}", response_model=TemplateDetail)
async def update_template(
    template_id: int,
    template: TemplateUpdate,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """更新模板"""
    existing = db.query(ChartTemplate).filter(ChartTemplate.id == template_id).first()
    
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    # 权限检查：只能更新自己的模板，或admin可更新公共模板
    from app.core.security import check_user_role
    is_admin = check_user_role(current_user, ["admin"], db)
    
    if existing.owner_id != current_user.id and not (is_admin and existing.is_public):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owner or admin can update this template"
        )
    
    # 更新字段
    if template.name is not None:
        existing.name = template.name
    if template.spec_json is not None:
        # 验证ChartSpec
        try:
            ChartSpec(**template.spec_json)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid ChartSpec: {str(e)}"
            )
        existing.spec_json = template.spec_json
    if template.is_public is not None:
        # 只有admin可以修改is_public
        if not check_user_role(current_user, ["admin"], db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admin can change is_public"
            )
        existing.is_public = template.is_public
    
    db.commit()
    db.refresh(existing)
    
    return {
        "id": existing.id,
        "name": existing.name,
        "chart_type": existing.chart_type,
        "is_public": existing.is_public,
        "owner_id": existing.owner_id,
        "created_at": existing.created_at.isoformat(),
        "spec_json": existing.spec_json
    }


@router.delete("/{template_id}")
async def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """删除模板"""
    template = db.query(ChartTemplate).filter(ChartTemplate.id == template_id).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    # 权限检查：只能删除自己的模板，或admin可删除公共模板
    from app.core.security import check_user_role
    is_admin = check_user_role(current_user, ["admin"], db)
    
    if template.owner_id != current_user.id and not (is_admin and template.is_public):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owner or admin can delete this template"
        )
    
    db.delete(template)
    db.commit()
    
    return {"message": "Template deleted successfully"}
