"""
LLM 多模态服务 (google-genai 原生 SDK)
- 使用 google.genai 直接调用 Gemini，不经过 OpenAI 兼容层
- 支持纯文字问诊 + 图片（Base64）问诊
- 流式输出 + 合规拦截层
"""
from __future__ import annotations
from typing import Optional, AsyncGenerator
import asyncio
import base64
import logging

from google import genai
from google.genai import types
from google.genai.errors import ClientError, ServerError

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── 合规系统 Prompt ────────────────────────────────────────────────
COMPLIANCE_SYSTEM_PROMPT = """你是"宠物阿福"APP内的宠物健康AI助手，定位为"兽医学术文献智能检索工具"，而非执业兽医。

你必须严格遵守以下规则：
1. **禁止使用任何确诊性语言**：绝对禁止"确诊为XX"、"患有XX病"、"诊断结果为"等确定性表述。
2. **必须使用参考性描述**：将所有可能的诊断替换为"具有XX疾病的部分特征"、"高度疑似XX问题"、"症状与XX常见表现相符"。
3. **每次回复结尾必须附加免责声明**：
   "⚠️ 本内容来源于兽医学术文献检索，仅供参考，不作为最终医疗判断依据。请尽快前往正规宠物医院，由执业兽医进行专业诊断。"
4. **识别高危症状**：若用户描述含有"大量出血"、"持续抽搐"、"昏迷"、"呼吸困难"等字样，立即建议紧急就医，不进行病情分析。
5. **语言风格**：用普通主人能理解的通俗语言，避免过度专业术语。结构清晰，使用列表。
"""

EMERGENCY_KEYWORDS = ["大量出血", "持续抽搐", "抽搐不止", "昏迷", "呼吸困难", "休克", "瞳孔散大"]
DISCLAIMER = (
    "\n\n---\n"
    "⚠️ **免责声明**：本内容来源于兽医学术文献检索，仅供参考，不作为最终医疗判断依据。"
    "请尽快前往正规宠物医院，由执业兽医进行专业诊断。"
)


def _is_emergency(text: str) -> bool:
    return any(kw in text for kw in EMERGENCY_KEYWORDS)


def _compliance_check(text: str) -> str:
    replacements = {
        "确诊为": "具有以下疾病部分特征：",
        "确诊": "高度疑似",
        "诊断为": "症状与以下情况相符：",
        "患有": "出现类似",
        "感染了": "疑似存在",
        "必须服用": "建议在兽医指导下考虑",
        "立即注射": "建议尽快就医评估是否需要注射",
    }
    for banned, replacement in replacements.items():
        text = text.replace(banned, replacement)
    return text


class LLMService:
    def __init__(self):
        self._client = genai.Client(api_key=settings.openai_api_key)
        self.model = "gemini-2.0-flash"

    async def analyze_stream(
        self,
        user_text: str,
        image_base64: Optional[str] = None,
        rag_context: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        # 紧急情况直接短路
        if _is_emergency(user_text):
            yield "🚨 **紧急提示**：您描述的症状属于高危状况，请立即停止任何居家处理，"
            yield "**马上前往最近的24小时宠物急诊医院**。时间就是生命，请勿拖延！"
            return

        # 构建消息内容
        contents = []

        # 图片
        if image_base64:
            contents.append(
                types.Part.from_bytes(
                    data=base64.b64decode(image_base64),
                    mime_type="image/jpeg",
                )
            )

        # 文字 + RAG 上下文
        prompt_text = user_text
        if rag_context:
            prompt_text = (
                f"【相关兽医文献参考】\n{rag_context}\n\n"
                f"【用户描述的症状】\n{user_text}"
            )
        contents.append(prompt_text)

        config = types.GenerateContentConfig(
            system_instruction=COMPLIANCE_SYSTEM_PROMPT,
            max_output_tokens=1500,
            temperature=0.3,
        )

        full_response = ""
        try:
            # 用 asyncio 包装同步的 stream 调用
            loop = asyncio.get_event_loop()

            def _sync_stream():
                chunks = []
                for chunk in self._client.models.generate_content_stream(
                    model=self.model,
                    contents=contents,
                    config=config,
                ):
                    chunks.append(chunk.text or "")
                return chunks

            chunks = await asyncio.wait_for(
                loop.run_in_executor(None, _sync_stream),
                timeout=30.0,
            )

            for text in chunks:
                if text:
                    cleaned = _compliance_check(text)
                    full_response += cleaned
                    yield cleaned

        except asyncio.TimeoutError:
            yield "\n\n⏳ **AI 响应超时（30s）**，请稍后重试。"
            return
        except ClientError as e:
            code = getattr(e, 'status_code', 0)
            if code == 429:
                yield "\n\n⏳ **AI 服务暂时繁忙（频率限制）**，请稍等 30 秒后重试。"
            else:
                yield f"\n\n⚠️ **请求错误**（{code}），请稍后重试。"
            return
        except ServerError as e:
            yield f"\n\n⚠️ **服务器错误**，请稍后重试。"
            return
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            yield f"\n\n⚠️ **未知错误**：{str(e)[:100]}"
            return

        if "免责声明" not in full_response and "仅供参考" not in full_response:
            yield DISCLAIMER


# 单例
llm_service = LLMService()
