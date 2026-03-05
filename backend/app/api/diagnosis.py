from __future__ import annotations
from typing import Optional
"""
诊断 API - /api/v1/diagnosis
支持：文字问诊 + 图片上传
返回：Server-Sent Events (SSE) 流式响应
"""
import base64
from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from fastapi.responses import StreamingResponse

from app.services.llm_service import llm_service
from app.services.rag_service import rag_service

router = APIRouter(prefix="/diagnosis", tags=["diagnosis"])

MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB


async def _stream_generator(user_text: str, image_base64: Optional[str]):
    """SSE 格式生成器"""
    rag_context = rag_service.retrieve(user_text, top_k=3)
    async for chunk in llm_service.analyze_stream(user_text, image_base64, rag_context):
        # SSE 格式：data: {内容}\n\n
        yield f"data: {chunk}\n\n"
    yield "data: [DONE]\n\n"


@router.post("/text")
async def diagnose_text(symptom: str = Form(..., description="症状文字描述")):
    """纯文字问诊（流式）"""
    if not symptom.strip():
        raise HTTPException(status_code=400, detail="症状描述不能为空")

    return StreamingResponse(
        _stream_generator(symptom, None),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/image")
async def diagnose_with_image(
    symptom: str = Form(..., description="症状描述文字"),
    image: UploadFile = File(..., description="宠物患部照片（≤5MB）"),
):
    """图文联合问诊（流式）"""
    if not symptom.strip():
        raise HTTPException(status_code=400, detail="症状描述不能为空")

    # 文件大小检查
    content = await image.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="图片不能超过 5MB，请压缩后重试")

    # 检查文件类型
    if image.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=415, detail="仅支持 JPEG / PNG / WebP 格式")

    image_b64 = base64.b64encode(content).decode()

    return StreamingResponse(
        _stream_generator(symptom, image_b64),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/rebuild-index")
async def rebuild_rag_index():
    """重建 RAG 向量索引（管理员用）"""
    count = rag_service.build_index()
    return {"message": f"RAG 索引重建完成，新增 {count} 个知识分块"}
