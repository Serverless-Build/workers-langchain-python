# LangChain on Workers

Compose a LangChain prompt, Workers AI chat model, and output parser into a real asynchronous inference pipeline without external API credentials.

## Run locally

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and Node.js 22 or later.

```sh
npm ci
uv sync --locked
uv run pywrangler dev --config wrangler.jsonc
```

## Check and deploy

```sh
uv run pywrangler deploy --config wrangler.jsonc
```

The configuration is portable: it contains no account ID, resource ID, or maintainer custom domain. Log in with Wrangler and select your own account before deploying. Generated dependencies and build outputs stay out of source control.

## Try the example

### Temporary accounts

Real inference is verified in a normal Cloudflare account. Temporary accounts currently reject the configured 70B model and the smaller Llama 3.2 1B model with Workers AI error 5034 (a payment method is required). This pattern therefore does not offer a temporary deployment. Use your own account for inference.

GET /prompt?profession=baker&style=cheerful inspects the real LangChain prompt without inference. GET /generate with those query parameters calls the actual Workers AI model. GET /health checks liveness. Only electrician, baker, teacher, and gardener are accepted; styles are practical or cheerful. Inference is capped at 64 output tokens, times out after 25 seconds, and uses a native per-IP, per-location limiter (5/minute). This is best-effort protection, not exact global quota accounting. Local development also runs inference remotely and requires account login. Workers AI usage applies; no external API key is required.

The LangChain pipeline is PromptTemplate | ChatCloudflareWorkersAI | StrOutputParser. Each request creates its own model chain; input is allowlisted and errors never reveal provider details.

## Pattern and live demo

- [Pattern page](https://serverless.build/patterns/langchain-workers)
- [Live deployment](https://workers-langchain-python.dwarven.workers.dev)
