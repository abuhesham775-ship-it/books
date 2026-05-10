"""
AI API - واجهة الذكاء الاصطناعي
"""
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.ai_service import AIService

router = APIRouter(prefix="/ai", tags=["الذكاء الاصطناعي"])


class SummaryRequest(BaseModel):
    text: str = Field(..., min_length=1)
    max_length: int = Field(default=200, ge=20, le=2000)


class ClassifyBookRequest(BaseModel):
    title: str = Field(..., min_length=1)
    description: Optional[str] = ""
    category: Optional[str] = ""


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)
    context: Optional[str] = ""


class SimilarityRequest(BaseModel):
    text1: str = Field(..., min_length=1)
    text2: str = Field(..., min_length=1)


class ImproveRequest(BaseModel):
    text: str = Field(..., min_length=1)


@router.get("/health")
def health():
    """فحص توفر خدمة AI"""
    service = AIService()
    return {
        "available": service.client is not None,
        "model": service.model,
    }


@router.post("/summary")
async def generate_summary(payload: SummaryRequest):
    """توليد ملخص للنص"""
    service = AIService()
    return {
        "summary": await service.generate_summary(payload.text, max_length=payload.max_length)
    }


@router.post("/quick-summary")
async def generate_quick_summary(payload: SummaryRequest):
    """توليد ملخص سريع"""
    service = AIService()
    return {
        "summary": await service.generate_summary(payload.text, max_length=min(payload.max_length, 50))
    }


@router.post("/classify-book")
async def classify_book(payload: ClassifyBookRequest):
    """تصنيف كتاب إلى قسم مناسب"""
    service = AIService()
    try:
        category = await service.classify_book(
            title=payload.title,
            description=payload.description or "",
            category=payload.category or ""
        )
        return {"category": category}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"فشل التصنيف: {exc}")


@router.post("/ask")
async def ask_ai(payload: AskRequest):
    """الإجابة على سؤال"""
    service = AIService()
    return {
        "answer": await service.answer_question(payload.question, context=payload.context or "")
    }


@router.post("/similarity")
async def similarity(payload: SimilarityRequest):
    """حساب درجة التشابه بين نصين"""
    service = AIService()
    return {
        "similarity": await service.similarity_score(payload.text1, payload.text2)
    }


@router.post("/improve")
async def improve_text(payload: ImproveRequest):
    """اقتراح تحسينات للنص"""
    service = AIService()
    return {
        "improvements": await service.suggest_improvements(payload.text)
    }


@router.post("/chapter-summary")
async def chapter_summary(text: str, chapter_name: Optional[str] = None):
    """تلخيص فصل"""
    service = AIService()
    return {
        "summary": await service.generate_chapter_summary(text=text, chapter_name=chapter_name or "")
    }


@router.post("/story-analysis")
async def story_analysis(book_content: str):
    """تحليل عام للمحتوى"""
    service = AIService()
    return {
        "analysis": await service.analyze_themes(book_content)
    }
