import asyncio
from urllib.parse import parse_qs, urlparse

from workers import Response, WorkerEntrypoint

MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
PROFESSIONS = ("electrician", "baker", "teacher", "gardener")
STYLES = ("practical", "cheerful")
PROMPT = "In one short {style} sentence, describe a great day in the life of a {profession}."


def response(data, status=200, extra_headers=None):
    return Response.json(data, status=status, headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", **(extra_headers or {})})


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        url = urlparse(request.url)
        if request.method != "GET":
            return response({"error": "Method not allowed"}, 405, {"Allow": "GET"})
        if url.path == "/health":
            return response({"status": "ok", "marker": "SERVERLESS_BUILD_LANGCHAIN_PYTHON_V1", "model": MODEL})
        if url.path == "/":
            return response({"framework": "LangChain", "pipeline": ["PromptTemplate", "ChatCloudflareWorkersAI", "StrOutputParser"], "model": MODEL, "max_tokens": 64, "professions": PROFESSIONS, "styles": STYLES, "routes": ["/prompt", "/generate"]})
        if url.path not in ("/prompt", "/generate"):
            return response({"error": "Not found"}, 404)
        query = parse_qs(url.query, keep_blank_values=True)
        profession, style = query.get("profession", ["electrician"]), query.get("style", ["practical"])
        if len(profession) != 1 or profession[0] not in PROFESSIONS or len(style) != 1 or style[0] not in STYLES:
            return response({"error": "Choose one allowed profession and style", "professions": PROFESSIONS, "styles": STYLES}, 400)
        values = {"profession": profession[0], "style": style[0]}
        # Keep deployment snapshots and health checks lightweight. Import the
        # patched LangChain modules only on routes that use them; Python caches
        # imports after the first use in each isolate.
        from langchain_core.prompts import PromptTemplate

        prompt = PromptTemplate.from_template(PROMPT)
        if url.path == "/prompt":
            return response({"prompt": prompt.format(**values), "model": MODEL, "inference": False})
        # Per-IP, per-location best-effort protection, not a global billing cap.
        # Use the platform-provided IP, never a caller-supplied query actor.
        key = request.headers.get("CF-Connecting-IP") or "local-development"
        limited = await self.env.INFERENCE_LIMITER.limit({"key": key})
        if not limited["success"]:
            return response({"error": "Inference limit reached; retry in a minute"}, 429, {"Retry-After": "60"})
        from langchain_cloudflare import ChatCloudflareWorkersAI
        from langchain_core.output_parsers import StrOutputParser

        llm = ChatCloudflareWorkersAI(model_name=MODEL, binding=self.env.AI, max_tokens=64)
        chain = prompt | llm | StrOutputParser()
        try:
            result = await asyncio.wait_for(chain.ainvoke(values), timeout=25)
            return response({"result": result, "model": MODEL, "max_tokens": 64, **values})
        except asyncio.TimeoutError:
            return response({"error": "Model inference timed out"}, 504)
        except Exception:
            return response({"error": "Model inference unavailable"}, 502)
