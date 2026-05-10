"""
AI Service - خدمة الذكاء الاصطناعي المتقدمة
جميع ميزات AI المطلوبة
"""
import os
from typing import Optional, List, Dict, Tuple
from openai import AsyncOpenAI
from config.settings import get_settings

settings = get_settings()


class AIService:
    """خدمة الذكاء الاصطناعي باستخدام OpenRouter"""

    def __init__(self):
        self.api_key = settings.openrouter_api_key
        self.model = settings.ai_model
        self.max_tokens = settings.max_tokens
        self.client = None
        if self.api_key:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url="https://openrouter.ai/api/v1"
            )

    # ==========================================
    # الميزات الأساسية
    # ==========================================

    async def generate_summary(self, text: str, max_length: int = 200) -> str:
        """توليد ملخص للنص"""
        if not self.client:
            return "خدمة AI غير متاحة"

        prompt = f"""قم بتلخيص النص التالي في ملخص مختصر من {max_length} حرف أو أقل:

{text}

الملخص:"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.max_tokens
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"حدث خطأ: {str(e)}"

    async def generate_embeddings(self, text: str) -> List[float]:
        """توليد embeddings للنص"""
        if not self.client:
            return []

        try:
            response = await self.client.embeddings.create(
                model=settings.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception:
            return []

    async def classify_book(self, title: str, description: str, category: str) -> str:
        """تصنيف الكتاب باستخدام AI"""
        if not self.client:
            return category

        prompt = f"""صنف الكتاب التالي في قسم مناسب من مكتبة عربية:
العنوان: {title}
الوصف: {description}
القسم الحالي: {category}

أجب بأقصر قسم مناسب فقط."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50
            )
            return response.choices[0].message.content.content.strip()
        except Exception:
            return category

    async def answer_question(self, question: str, context: str = "") -> str:
        """الإجابة على سؤال باستخدام AI"""
        if not self.client:
            return "خدمة AI غير متاحة"

        prompt = f"""{context}

السؤال: {question}

أجب بشكل مختصر ومفيد."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.max_tokens
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"حدث خطأ: {str(e)}"

    async def similarity_score(self, text1: str, text2: str) -> float:
        """حساب درجة التشابه بين نصين"""
        if not self.client:
            return 0.0

        try:
            emb1 = await self.generate_embeddings(text1)
            emb2 = await self.generate_embeddings(text2)

            if not emb1 or not emb2:
                return 0.0

            dot_product = sum(a * b for a, b in zip(emb1, emb2))
            norm1 = sum(a * a for a in emb1) ** 0.5
            norm2 = sum(b * b for b in emb2) ** 0.5

            if norm1 * norm2 == 0:
                return 0.0

            return dot_product / (norm1 * norm2)
        except Exception:
            return 0.0

    async def suggest_improvements(self, text: str) -> str:
        """اقتراح تحسينات للنص"""
        if not self.client:
            return "خدمة AI غير متاحة"

        prompt = f"""اقترح تحسينات على النص التالي مع الحفاظ على المعنى:
{text}

التعديلات:"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.max_tokens
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"حدث خطأ: {str(e)}"

    # ==========================================
    # 📝 توليد ملخصات كتب متقدمة
    # ==========================================

    async def generate_quick_summary(self, text: str) -> str:
        """ملخص سريع (50 كلمة)"""
        return await self.generate_summary(text, max_length=50)

    async def generate_detailed_summary(self, text: str) -> str:
        """ملخص مفصل (500 كلمة)"""
        return await self.generate_summary(text, max_length=500)

    async def generate_chapter_summary(self, text: str, chapter_name: str = "") -> str:
        """ملخص حسب الفصل"""
        if not self.client:
            return "خدمة AI غير متاحة"

        prompt = f"""قم بتلخيص الفصل "{chapter_name}" من النص التالي في ملخص شامل:

{text}

يجب أن يشمل الملخص:
- أهم النقاط الرئيسية
- الشخصيات المذكورة
- الأحداث الرئيسية
- العلاقات بين الأحداث

الملخص:"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"حدث خطأ: {str(e)}"

    # ==========================================
    # 💬 محادثة حول الكتاب
    # ==========================================

    async def ask_about_book(
        self,
        book_title: str,
        book_content: str,
        question: str
    ) -> str:
        """أسئلة وأجوبة عن محتوى الكتاب"""
        if not self.client:
            return "خدمة AI غير متاحة"

        prompt = f"""أنت مساعد متخصص في تحليل الكتب. بناءً على المعلومات التالية:

عنوان الكتاب: {book_title}

محتوى الكتاب:
{book_content[:2000]}

السؤال: {question}

أجب بشكل دقيق ومفصل."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.max_tokens
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"حدث خطأ: {str(e)}"

    async def explain_characters(
        self,
        book_content: str,
        character_name: str = None
    ) -> str:
        """شرح الشخصيات"""
        if not self.client:
            return "خدمة AI غير متاحة"

        prompt = f"""قم بتحليل شخصيات الكتاب التالي:

{book_content[:3000]}

{'يركز على الشخصية: ' + character_name if character_name else ''}

يجب أن يشمل التحليل:
- اسم الشخصية ووصفها
- صفاتها ومميزاتها
- دورها في القصة
- علاقتها بالشخصيات الأخرى"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"حدث خطأ: {str(e)}"

    async def analyze_themes(self, book_content: str) -> str:
        """تحليل الثيمات والرسائل"""
        if not self.client:
            return "خدمة AI غير متاحة"

        prompt = f"""قم بتحليل الثيمات والرسائل الرئيسية في الكتاب التالي:

{book_content[:3000]}

يجب أن يشمل التحليل:
- الثيمات الرئيسية
- الرسائل الخفية
- التأثير الاجتماعي أو الثقافي
- الدروس المستفادة"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"حدث خطأ: {str(e)}"

    # ==========================================
    # 📖 استخراج المعلومات
    # ==========================================

    async def extract_quotes(self, text: str, max_quotes: int = 5) -> List[str]:
        """استخراج الاقتباسات المميزة"""
        if not self.client:
            return []

        prompt = f"""استخرج {max_quotes} اقتباسات مميزة ومهمة من النص التالي:

{text}

أجب في شكل قائمة مرقمة."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300
            )
            content = response.choices[0].message.content.strip()
            quotes = [line.strip() for line in content.split('\n') if line.strip()]
            return quotes[:max_quotes]
        except Exception:
            return []

    async def get_author_facts(self, author_name: str, book_title: str = "") -> str:
        """حقائق عن المؤلف"""
        if not self.client:
            return "خدمة AI غير متاحة"

        prompt = f"""قدم معلومات عن المؤلف {author_name}:

{'كتابه: ' + book_title if book_title else ''}

يجب أن يشمل:
- نبذة شخصية
- أهم أعماله
- جوائزه وإنجازاته
- أسلوبه الأدبي"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"حدث خطأ: {str(e)}"

    async def compare_books(
        self,
        book1_title: str,
        book1_desc: str,
        book2_title: str,
        book2_desc: str
    ) -> str:
        """مقارنة بين كتب"""
        if not self.client:
            return "خدمة AI غير متاحة"

        prompt = f"""قارن بين الكتابين التاليين:

الكتاب الأول: {book1_title}
{book1_desc}

الكتاب الثاني: {book2_title}
{book2_desc}

يجب أن يشمل المقارنة:
- التشابهات
- الاختلافات
- أيهما أنسب لأي نوع من القراء"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"حدث خطأ: {str(e)}"

    # ==========================================
    # 🎭 تحليل المشاعر والمحتوى
    # ==========================================

    async def analyze_sentiment(self, text: str) -> Dict[str, any]:
        """تحليل مشاعر النص"""
        if not self.client:
            return {"sentiment": "غير متاح", "score": 0}

        prompt = f"""حلل مشاعر النص التالي وحدد:
1. هل هو إيجابي، سلبي، أم محايد
2. الدرجة من -1 إلى 1

النص:
{text}

أجب بالصيغة:
المشاعر: [إيجابي/سلبي/محايد]
الدرجة: [رقم بين -1 و 1]"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100
            )
            content = response.choices[0].message.content.strip()

            sentiment = "محايد"
            score = 0.0

            if "إيجابي" in content:
                sentiment = "إيجابي"
                score = 0.7
            elif "سلبي" in content:
                sentiment = "سلبي"
                score = -0.7

            return {"sentiment": sentiment, "score": score}
        except Exception:
            return {"sentiment": "غير متاح", "score": 0}

    async def content_rating(self, text: str) -> Dict[str, any]:
        """تقييم محتوى الكتاب"""
        if not self.client:
            return {"rating": "غير محدد", "warnings": [], "suitable_for": []}

        prompt = f"""قم بتقييم محتوى النص التالي:

{text[:1500]}

أجب عن:
1. هل يناسب الأطفال؟
2. هل يحتوي على محتوى للبالغين فقط؟
3. أي تحذيرات ضرورية؟

أجب بالصيغة:
يناسب الأطفال: [نعم/لا]
للبالغين فقط: [نعم/لا]
تحذيرات: [قائمة التحذيرات]"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200
            )
            content = response.choices[0].message.content.strip()

            suitable_for = []
            warnings = []
            rating = "عام"

            if "يناسب الأطفال: لا" in content or "لا يناسب الأطفال" in content:
                suitable_for.append("adults_only")
                rating = "للبالغين"
            else:
                suitable_for.append("all_ages")

            if "البالغين فقط: نعم" in content:
                suitable_for.append("adults_only")
                warnings.append("محتوى للبالغين")

            return {
                "rating": rating,
                "warnings": warnings,
                "suitable_for": suitable_for
            }
        except Exception:
            return {"rating": "غير محدد", "warnings": [], "suitable_for": []}

    async def analyze_tone(self, text: str) -> str:
        """تقييم نبرة الكتاب"""
        if not self.client:
            return "غير متاح"

        prompt = f"""صف نبرة وأجواء الكتاب التالي:

{text[:1500]}

حدد:
- النبرة العامة (رسمية، عادية، ساخرة، درامية، إلخ)
- الأجواء (مثيرة، هادئة، مشوقة، حزينة، إلخ)
- مستوى الصعوبة"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"حدث خطأ: {str(e)}"

    # ==========================================
    # 🤖 مساعد القراءة الذكي
    # ==========================================

    async def smart_reading_assistant(
        self,
        query: str,
        book_content: str = "",
        book_title: str = ""
    ) -> str:
        """مساعد قراءة ذكي شامل"""
        if not self.client:
            return "خدمة AI غير متاحة"

        context = ""
        if book_title:
            context += f"كتاب: {book_title}\n"
        if book_content:
            context += f"المحتوى:\n{book_content[:2000]}\n"

        prompt = f"""{context}

المستخدم يسأل: {query}

أنا مساعد ذكي متخصص في الكتب. ساعد المستخدم بأفضل طريقة ممكنة.
إذا كان السؤال عن محتوى محدد، أجب بناءً على المحتوى.
إذا كان عاماً، أجب بناءً على معرفتي."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.max_tokens
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"حدث خطأ: {str(e)}"

    # ==========================================
    # 📚 تلخيص وتحليل متقدم
    # ==========================================

    async def generate_book_analysis(self, book_data: Dict) -> Dict[str, str]:
        """تحليل كامل للكتاب"""
        if not self.client:
            return {}

        title = book_data.get('title', '')
        author = book_data.get('author', '')
        description = book_data.get('description', '')

        prompt = f"""قدم تحليلاً شاملاً للكتاب التالي:

العنوان: {title}
المؤلف: {author}
الوصف: {description}

يجب أن يشمل التحليل:
1. ملخص سريع
2. الموضوع الرئيسي
3. الفئة المستهدفة
4. نقاط القوة
5. التقييم العام (1-5 نجوم)
6. لماذا يجب قراءته؟"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800
            )

            content = response.choices[0].message.content.strip()

            # استخراج التقييم
            rating = 3.0
            for i in range(1, 6):
                stars = "★" * i + "☆" * (5 - i)
                if stars in content or str(i) in content.split('\n')[-1]:
                    rating = float(i)
                    break

            return {
                "analysis": content,
                "rating": rating
            }
        except Exception as e:
            return {"analysis": f"حدث خطأ: {str(e)}", "rating": 3.0}

    # ==========================================
    # 🔍 بحث ذكي محسن
    # ==========================================

    async def semantic_search_enhanced(
        self,
        query: str,
        documents: List[str],
        top_k: int = 5
    ) -> List[Tuple[str, float]]:
        """بحث دلالي محسن مع تقييم"""
        if not self.client:
            return []

        query_embedding = await self.generate_embeddings(query)
        if not query_embedding:
            return []

        results = []
        for doc in documents:
            doc_embedding = await self.generate_embeddings(doc)
            if doc_embedding:
                similarity = await self.similarity_score(query, doc)
                results.append((doc, similarity))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    # ==========================================
    # 📊 إحصائيات وتحليلات
    # ==========================================

    async def analyze_user_preferences(
        self,
        user_history: List[Dict]
    ) -> Dict[str, any]:
        """تحليل تفضيلات المستخدم"""
        if not self.client or not user_history:
            return {}

        prompt = """حلل سلوك المستخدم التالي في المكتبة:

"""

        for item in user_history[:20]:
            action = item.get('action', '')
            book = item.get('book_title', '')
            category = item.get('category', '')
            prompt += f"- {action}: {book} ({category})\n"

        prompt += """
استخرج:
1. التصنيفات المفضلة
2. نوعية الكتب المفضلة
3. أنماط القراءة
4. توصيات لتحسين التجربة"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500
            )

            content = response.choices[0].message.content.strip()

            return {
                "preferences": content,
                "preferred_categories": self._extract_list(content, ["الأدب", "العلوم", "التاريخ", "الفلسفة"]),
                "recommended_actions": []
            }
        except Exception:
            return {}

    def _extract_list(self, text: str, keywords: List[str]) -> List[str]:
        """استخراج قائمة من النص"""
        found = []
        for keyword in keywords:
            if keyword in text:
                found.append(keyword)
        return found


# Singleton instance
ai_service = AIService()
