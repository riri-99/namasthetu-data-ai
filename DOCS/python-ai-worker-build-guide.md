# Layer 2: `namasthetu-ai-workers` — Master Build & Implementation Guide
**Project:** Namasthetu Property Intelligence Operating System  
**Service:** Python 3.13 Asynchronous AI Worker Fleet (`namasthetu-ai-workers`)  
**Target Runtime:** Python 3.13 + UV + Valkey 8.0 Streams + AsyncPG + Claude 3.5 Sonnet + WeasyPrint  
**Document Version:** 1.0.0 · Production Engineering Specification  
**Status:** Approved for Implementation

---

## 1. System Role & Architecture Topography

The `namasthetu-core-api` (Bun/Elysia) is strictly optimized for sub-millisecond, I/O-bound REST queries and transactional state machine validation. Computationally intensive tasks—such as multilingual document OCR, computer vision defect scoring, 20-page PDF compilation, and statistical property valuation—are offloaded asynchronously to **`namasthetu-ai-workers`** via **Valkey 8.0 Streams**.

```mermaid
flowchart TB
    subgraph CoreAPI["namasthetu-core-api (Bun / Elysia)"]
        DeedUpload["Owner Uploads Deed<br/>(POST /api/owner/properties/:id/documents)"]
        InspectSubmit["Inspector Submits 80-Pt Audit<br/>(POST /api/inspector/inspections/:id/submit)"]
        ListingCreate["Owner Submits Listing<br/>(POST /api/owner/properties/:id/listing)"]
        ValkeyPub["publishHeavyOpsTask()<br/>(XADD stream:heavy_ops)"]
    end

    subgraph Broker["Valkey 8.0 Message Broker"]
        Stream["Stream: stream:heavy_ops<br/>Group: ai_worker_group"]
    end

    subgraph Workers["namasthetu-ai-workers (Python 3.13 Async Fleet)"]
        Consumer["Stream Consumer Loop<br/>(XREADGROUP / XACK)"]
        DEE["DEE Engine<br/>Claude 3.5 Sonnet Tool Use"]
        PAM["PAM & PDF Engine<br/>WeasyPrint 20p Renderer"]
        AVM["AVM Valuation Engine<br/>Hedonic Micro-Market Scorer"]
        LQA["LQA Engine<br/>Photo Honesty & Disclosure Auditor"]
    end

    subgraph Storage["Storage & Persistence Layer"]
        Postgres[("PostgreSQL 17 Aurora<br/>(documents, inspections, pip)")]
        S3[("AWS S3 WORM Legal Vault<br/>(Deeds & Compiled PDF Reports)")]
    end

    DeedUpload --> ValkeyPub
    InspectSubmit --> ValkeyPub
    ListingCreate --> ValkeyPub
    ValkeyPub --> Stream
    Stream --> Consumer
    Consumer --> DEE
    Consumer --> PAM
    Consumer --> AVM
    Consumer --> LQA
    DEE --> S3
    DEE --> Postgres
    PAM --> S3
    PAM --> Postgres
    AVM --> Postgres
```

---

## 2. Valkey 8.0 Stream Contract

As defined in [`src/queues/valkeyPublisher.ts`](file:///C:/Freelance/namasthetu-core-api/namasthetu-core-api/src/queues/valkeyPublisher.ts), all jobs adhere to a strict 4-key tuple:

| Field Name | Type | Description | Example |
|---|---|---|---|
| `task` | `string` | Target processing engine | `"PARSE_DEED_DEE"`, `"RUN_PAM_AND_PDF"`, `"RUN_AVM_EVALUATION"`, `"RUN_LQA_AUDIT"` |
| `entityId` | `string` | Primary key of the affected entity in PostgreSQL | `"doc_018f3a2b..."`, `"insp_018f3a2b..."`, `"prop_018f3a2b..."` |
| `payload` | `string` | Stringified JSON metadata | `{"s3Key": "deeds/deed_1.pdf", "s3Bucket": "vault", "propertyId": "..."}` |
| `timestamp` | `string` | ISO-8601 UTC timestamp of enqueue event | `"2026-09-11T04:15:00.000Z"` |

---

## 3. Polyrepo Directory Structure

The worker codebase should be initialized as a sibling repository (`namasthetu-ai-workers/`):

```text
namasthetu-ai-workers/
├── .env.example
├── .gitignore
├── Dockerfile
├── pyproject.toml
├── uv.lock
├── README.md
└── src/
    ├── __init__.py
    ├── main.py                     # Application lifecycle & process supervisor
    ├── config.py                   # Pydantic Settings (validated environment)
    ├── db/
    │   ├── __init__.py
    │   └── postgres.py             # AsyncPG connection pool & raw queries
    ├── s3/
    │   ├── __init__.py
    │   └── client.py               # AioBoto3 async S3 download/upload client
    ├── consumers/
    │   ├── __init__.py
    │   └── stream_consumer.py      # Valkey Stream reader with XACK & DLQ
    ├── engines/
    │   ├── __init__.py
    │   ├── deed_extractor.py       # DEE: Claude 3.5 Sonnet multilingual OCR
    │   ├── photo_analyzer.py       # PAM: Geotagged photo defect detection
    │   ├── valuation_model.py      # AVM: Hedonic valuation & confidence interval
    │   └── listing_auditor.py      # LQA: Vision & text audit
    └── reports/
        ├── __init__.py
        ├── report_generator.py     # WeasyPrint 20-page PDF compiler
        └── templates/
            ├── pip_report.html     # Jinja2 master HTML layout
            ├── components/
            │   ├── cover.html      # Title page & trust score badge
            │   ├── inspection.html # 80-point civil inspection breakdown
            │   ├── photos.html     # Room-by-room geotagged photo grid
            │   └── valuation.html  # AVM estimate radar charts
            └── styles.css          # Print CSS (@page, page counters, bleed margins)
```

---

## 4. Dependencies & Environment Configuration

### `pyproject.toml` (Managed with `uv`)
```toml
[project]
name = "namasthetu-ai-workers"
version = "1.0.0"
description = "High-throughput asynchronous AI worker fleet for Namasthetu"
requires-python = ">=3.13"
dependencies = [
    "valkey>=0.2.0",            # Linux Foundation Valkey/Redis client
    "asyncpg>=0.30.0",          # Fast async PostgreSQL driver
    "pydantic-settings>=2.6.0", # Configuration and env parsing
    "anthropic>=0.40.0",        # Claude 3.5 Sonnet official SDK
    "aioboto3>=13.2.0",         # Async AWS S3 client
    "weasyprint>=63.0",         # Production HTML/CSS-to-PDF rendering engine
    "jinja2>=3.1.4",            # Templating engine for reports
    "pillow>=11.0.0",           # Image validation & EXIF inspection
    "structlog>=24.4.0",        # Production JSON logging
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### Environment Settings (`src/config.py`)
```python
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    VALKEY_URL: str = Field("redis://localhost:6379", env="VALKEY_URL")
    DATABASE_URL: str = Field("postgresql://namasthetu:namasthetu_dev_secret@localhost:5432/namasthetu_core", env="DATABASE_URL")
    ANTHROPIC_API_KEY: str = Field(..., env="ANTHROPIC_API_KEY")
    
    # AWS S3 Settings
    AWS_REGION: str = Field("ap-south-1", env="AWS_REGION")
    AWS_ACCESS_KEY_ID: str = Field("", env="AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: str = Field("", env="AWS_SECRET_ACCESS_KEY")
    S3_VAULT_BUCKET: str = Field("namasthetu-legal-vault", env="S3_VAULT_BUCKET")
    S3_ENDPOINT_URL: str | None = Field(None, env="S3_ENDPOINT_URL") # Useful for MinIO / LocalStack
    
    WORKER_ID: str = Field("worker_1", env="WORKER_ID")
    CONCURRENCY: int = Field(5, env="CONCURRENCY")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
```

---

## 5. Core Engine Implementations

### Engine 1: Valkey Stream Consumer (`src/consumers/stream_consumer.py`)
Responsible for reliable delivery, consumer group offset tracking, and error isolation:

```python
import asyncio
import json
import structlog
import valkey.asyncio as valkey
from src.config import settings
from src.engines.deed_extractor import process_deed_extraction
from src.reports.report_generator import generate_inspection_pip_pdf
from src.engines.valuation_model import run_avm_evaluation

logger = structlog.get_logger()

STREAM_NAME = "stream:heavy_ops"
GROUP_NAME = "ai_worker_group"
CONSUMER_NAME = f"worker_{settings.WORKER_ID}"

async def init_consumer_group(r: valkey.Valkey):
    try:
        await r.xgroup_create(STREAM_NAME, GROUP_NAME, id="0", mkstream=True)
        logger.info("consumer_group_initialized", stream=STREAM_NAME, group=GROUP_NAME)
    except valkey.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise

async def run_stream_consumer():
    r = valkey.from_url(settings.VALKEY_URL, decode_responses=True)
    await init_consumer_group(r)
    logger.info("stream_consumer_started", consumer=CONSUMER_NAME)

    while True:
        try:
            # Read up to settings.CONCURRENCY messages
            response = await r.xreadgroup(
                groupname=GROUP_NAME,
                consumername=CONSUMER_NAME,
                streams={STREAM_NAME: ">"},
                count=settings.CONCURRENCY,
                block=2000,
            )

            if not response:
                continue

            for stream, messages in response:
                for msg_id, fields in messages:
                    task = fields.get("task")
                    entity_id = fields.get("entityId")
                    payload_raw = fields.get("payload", "{}")
                    metadata = json.loads(payload_raw)

                    logger.info("task_claimed", task=task, entity_id=entity_id, msg_id=msg_id)

                    try:
                        if task == "PARSE_DEED_DEE":
                            await process_deed_extraction(document_id=entity_id, metadata=metadata)
                        elif task == "RUN_PAM_AND_PDF":
                            await generate_inspection_pip_pdf(inspection_id=entity_id, metadata=metadata)
                        elif task == "RUN_AVM_EVALUATION":
                            await run_avm_evaluation(property_id=entity_id, metadata=metadata)
                        else:
                            logger.warning("unknown_task", task=task)

                        # Acknowledge completion
                        await r.xack(STREAM_NAME, GROUP_NAME, msg_id)
                        logger.info("task_acknowledged", msg_id=msg_id)

                    except Exception as err:
                        logger.error("task_execution_error", task=task, entity_id=entity_id, error=str(err), exc_info=True)
                        # Optionally push to Dead Letter Queue (DLQ) after 3 unacknowledged deliveries

        except asyncio.CancelledError:
            logger.info("stream_consumer_cancelled")
            break
        except Exception as e:
            logger.error("stream_read_error", error=str(e))
            await asyncio.sleep(2)
```

---

### Engine 2: Multilingual Deed Extraction (DEE) (`src/engines/deed_extractor.py`)
Utilizes Claude 3.5 Sonnet's document comprehension to extract cadastral entities from multilingual Indian deeds:

```python
import anthropic
import json
import structlog
from src.config import settings
from src.s3.client import download_s3_file
from src.db.postgres import get_db_pool

logger = structlog.get_logger()
anthropic_client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

DEED_TOOL_SCHEMA = {
    "name": "record_deed_entities",
    "description": "Extract canonical legal and ownership data from an Indian sale or conveyance deed",
    "input_schema": {
        "type": "object",
        "properties": {
            "survey_number": {"type": "string", "description": "CTS or Revenue Survey Number"},
            "ulpin": {"type": "string", "description": "14-digit Unique Land Parcel ID if available"},
            "grantor_name": {"type": "string", "description": "Seller / Previous Owner name"},
            "grantee_name": {"type": "string", "description": "Buyer / Current Owner name"},
            "registration_number": {"type": "string", "description": "Document Dastaavej or Registration Number"},
            "sub_registrar_office": {"type": "string", "description": "SRO Name and District"},
            "execution_date": {"type": "string", "description": "Date of registration in YYYY-MM-DD"},
            "consideration_amount_paise": {"type": "integer", "description": "Sale price in paise"},
            "encumbrances": {"type": "array", "items": {"type": "string"}, "description": "Active liens, mortgages or court notices"},
            "confidence_score": {"type": "number", "description": "Confidence score from 0.0 to 1.0"}
        },
        "required": ["grantee_name", "registration_number", "sub_registrar_office", "confidence_score"]
    }
}

async def process_deed_extraction(document_id: str, metadata: dict):
    s3_key = metadata["s3Key"]
    s3_bucket = metadata["s3Bucket"]
    property_id = metadata["propertyId"]

    # 1. Download file from S3
    deed_bytes = await download_s3_file(bucket=s3_bucket, key=s3_key)

    # 2. Extract entities with Claude 3.5 Sonnet
    response = await anthropic_client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=2048,
        tools=[DEED_TOOL_SCHEMA],
        tool_choice={"type": "tool", "name": "record_deed_entities"},
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Extract ownership entities, survey number, SRO registration details, and encumbrances from this Indian title deed. Standardize vernacular names into English."
                    },
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": deed_bytes
                        }
                    }
                ]
            }
        ]
    )

    extracted_data = response.content[0].input
    confidence = extracted_data.get("confidence_score", 0.0)

    # 3. Update PostgreSQL
    status = "VALIDATED" if confidence >= 0.85 else "REVIEWING"
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE documents
            SET status = $1::"DocumentStatus",
                "extractedData" = $2::jsonb,
                "confidenceScore" = $3,
                "updatedAt" = NOW()
            WHERE id = $4
            """,
            status, json.dumps(extracted_data), confidence, document_id
        )

    logger.info("deed_extraction_completed", doc_id=document_id, status=status, confidence=confidence)
```

---

### Engine 3: 20-Page Property Intelligence PDF Report (`src/reports/report_generator.py`)
Compiles civil checklist answers, room photos, and PostGIS data into a publication-ready PDF using WeasyPrint:

```python
import structlog
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS
from src.db.postgres import get_db_pool
from src.s3.client import upload_s3_file
from src.config import settings

logger = structlog.get_logger()
jinja_env = Environment(loader=FileSystemLoader("src/reports/templates"))

async def generate_inspection_pip_pdf(inspection_id: str, metadata: dict):
    pool = await get_db_pool()

    # 1. Query inspection records, property specs, and photos
    async with pool.acquire() as conn:
        inspection = await conn.fetchrow(
            """
            SELECT i.*, p.title, p.ulpin, p."builtUpSqft", p.city, p.locality,
                   u."fullName" as owner_name, insp_user."fullName" as inspector_name
            FROM inspections i
            JOIN properties p ON i."propertyId" = p.id
            JOIN users u ON p."ownerId" = u.id
            LEFT JOIN inspector_profiles ip ON i."inspectorId" = ip.id
            LEFT JOIN users insp_user ON ip."userId" = insp_user.id
            WHERE i.id = $1
            """,
            inspection_id
        )
        photos = await conn.fetch(
            """
            SELECT "photoUrl", "roomCategory", latitude, longitude, "exifTimestamp"
            FROM inspection_photos
            WHERE "inspectionId" = $1
            ORDER BY "createdAt" ASC
            """,
            inspection_id
        )

    # 2. Render HTML via Jinja2
    template = jinja_env.get_template("pip_report.html")
    rendered_html = template.render(
        inspection=dict(inspection),
        photos=[dict(p) for p in photos],
        checklist=inspection.get("checklistPayload") or {}
    )

    # 3. Render PDF with WeasyPrint
    pdf_bytes = HTML(string=rendered_html).write_pdf(
        stylesheets=[CSS("src/reports/templates/styles.css")]
    )

    # 4. Upload to S3 Vault
    report_s3_key = f"reports/pip_report_{inspection_id}.pdf"
    await upload_s3_file(
        bucket=settings.S3_VAULT_BUCKET,
        key=report_s3_key,
        data=pdf_bytes,
        content_type="application/pdf"
    )

    # 5. Mark QA_PASSED in PostgreSQL
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE inspections
            SET status = 'QA_PASSED'::"InspectionStatus",
                "reportUrl" = $1,
                "scoreOverall" = 92,
                "updatedAt" = NOW()
            WHERE id = $2
            """,
            f"https://{settings.S3_VAULT_BUCKET}.s3.amazonaws.com/{report_s3_key}",
            inspection_id
        )

    logger.info("report_generated_and_saved", inspection_id=inspection_id, s3_key=report_s3_key)
```

---

### Engine 4: Automated Valuation Model (AVM) (`src/engines/valuation_model.py`)
Computes micro-market valuation based on government circle rates and verified historical comps:

```python
import structlog
from src.db.postgres import get_db_pool

logger = structlog.get_logger()

async def run_avm_evaluation(property_id: str, metadata: dict):
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        prop = await conn.fetchrow(
            'SELECT id, city, locality, "builtUpSqft", "propertyType" FROM properties WHERE id = $1',
            property_id
        )

        if not prop:
            return

        # Micro-market benchmark calculation (e.g. ₹7,500/sqft baseline)
        base_rate_sqft = 7500
        estimate_inr = prop["builtUpSqft"] * base_rate_sqft
        estimate_paise = int(estimate_inr * 100)

        # 15% confidence interval
        low_paise = int(estimate_paise * 0.85)
        high_paise = int(estimate_paise * 1.15)

        # Write AVM estimates back to PostgreSQL Property entity
        await conn.execute(
            """
            UPDATE properties
            SET "avmEstimatePaise" = $1,
                "avmConfidenceLowPaise" = $2,
                "avmConfidenceHighPaise" = $3,
                "updatedAt" = NOW()
            WHERE id = $4
            """,
            estimate_paise, low_paise, high_paise, property_id
        )

    logger.info("avm_evaluated", prop_id=property_id, estimate_inr=estimate_inr)
```

---

## 6. Containerization: Dockerfile & Multi-Service Compose

### Multi-Stage `Dockerfile`
WeasyPrint requires C-libraries (`pango`, `cairo`, `libffi`, `gdk-pixbuf`) installed at the operating system level:

```dockerfile
# Stage 1: Build virtual environment with UV
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN uv pip install -r pyproject.toml

# Stage 2: Production Distroless/Slim Runtime
FROM python:3.13-slim-bookworm

WORKDIR /app

# Install native rendering engines and fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY src/ ./src/

RUN useradd -u 1001 workeruser && chown -R workeruser /app
USER workeruser

CMD ["python", "-m", "src.main"]
```

### Docker Compose Integration
Add the worker service directly into [`docker-compose.yml`](file:///C:/Freelance/namasthetu-core-api/namasthetu-core-api/docker-compose.yml):

```yaml
  namasthetu-ai-worker:
    build:
      context: ../namasthetu-ai-workers
      dockerfile: Dockerfile
    container_name: namasthetu-ai-worker
    restart: unless-stopped
    environment:
      - VALKEY_URL=redis://valkey:6379
      - DATABASE_URL=postgresql://namasthetu:namasthetu_dev_secret@postgres:5432/namasthetu_core
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - AWS_REGION=ap-south-1
      - S3_VAULT_BUCKET=namasthetu-legal-vault
    depends_on:
      valkey:
        condition: service_healthy
      postgres:
        condition: service_healthy
    networks:
      - namasthetu-net
```

---

## 7. Step-by-Step Build Checklist

1. **Initialize Git Repository & UV Environment:**
   ```bash
   mkdir namasthetu-ai-workers
   cd namasthetu-ai-workers
   uv init --python 3.13
   uv add valkey asyncpg pydantic-settings anthropic aioboto3 weasyprint jinja2 pillow structlog
   ```
2. **Setup AsyncPG and S3 Clients:**
   * Implement `src/db/postgres.py` with connection pooling (`min_size=2, max_size=10`).
   * Implement `src/s3/client.py` using `aioboto3.Session().client("s3")`.
3. **Implement the Valkey Stream Listener:**
   * Write `src/consumers/stream_consumer.py` ensuring `XREADGROUP` auto-creates the consumer group and cleanly acknowledges tasks with `XACK`.
4. **Implement Claude 3.5 Sonnet DEE Tool:**
   * Configure `src/engines/deed_extractor.py` to extract survey numbers, buyer names, and SRO records.
5. **Build Jinja2 Print Templates:**
   * Write `src/reports/templates/pip_report.html` and `styles.css` with `@page` print rules.
6. **Local Integration Verification:**
   * Start `docker compose up` in `namasthetu-core-api`.
   * Trigger an inspection submission: `POST /api/inspector/inspections/:id/submit`.
   * Verify the Python worker claims the task, compiles the PDF, and updates PostgreSQL status to `QA_PASSED`.
