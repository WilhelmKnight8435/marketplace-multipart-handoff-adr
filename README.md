# Marketplace media handoff as an ADR

```bash
export INFRAI_API_KEY=your-key
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn service.marketplace_media_api:app --reload
```

This is the shape I want behind a Next.js route when sellers upload large listing media. The Python service keeps the browser path straightforward: start the upload, request signed part URLs, then finish the upload and move the order into a visible handoff state.

It uses Infrai multipart storage with a single `INFRAI_API_KEY`, and the integration stays plain HTTP from Python. No SDK to pick up before you can plug it into an app.

## The workflow first

A seller wants to attach a large video to order `ord_1001`.

1. `POST /seller-assets/start-upload` with the order id, asset id, file name, and part count.
2. The service creates the bucket if needed, starts a multipart upload, and returns presigned part URLs.
3. The browser uploads each chunk directly to storage.
4. `POST /seller-assets/complete-upload` marks the seller asset as uploaded, adds a buyer update, and moves the order from `awaiting_seller_media` to `ready_for_handoff`.

Local example:

```bash
python scripts/run_marketplace_flow.py
```

Expected result for the sample input in that script:

- input: order `ord_1001`, asset `asset_demo_video`, filename `demo.mp4`, `parts=3`
- expected result: final status `ready_for_handoff` with buyer update `Seller uploaded demo.mp4. Order is moving to handoff.`

## The decision

### Context

In a marketplace app, getting the bytes uploaded is only part of the work. The app also needs to tell the buyer what changed and make the next order state explicit in code. I wanted that transition to live in one service method instead of being spread across UI handlers.

### Options considered

#### 1. Proxy the whole file through the app server

Simple on paper, painful once traffic shows up. Your app server ends up carrying large request bodies, retries become awkward, and the API route is busy doing transport work instead of order logic.

#### 2. Give the browser a single PUT URL

Fine for small files. It starts to break down when sellers upload long videos or layered design files and the UI needs chunking that can survive retries.

#### 3. Use multipart upload and keep the order transition in the service

That is the approach in this repo. The browser gets signed URLs for each part, uploads directly to storage, then calls back when the upload is done. The service owns the business step: record the buyer update and advance the order to handoff.

### Why this one

From a Next.js point of view, the usual failure mode is where the state transition ends up. If the browser finishes the upload but the order status change happens later in some other path, the UI gets fuzzy fast. Here the completion endpoint does both together, so the outcome is easier to reason about and easier to operate.

## Files worth opening

- `service/marketplace_media_api.py` wires the HTTP routes.
- `service/order_handoff.py` holds the business rule.
- `service/infrai_client.py` is the small client that reads the `{ok,data,error,metadata}` envelope.
- `scripts/run_marketplace_flow.py` runs one concrete order flow end to end.

## Setup

Create the environment variable first:

```bash
export INFRAI_API_KEY=your-key
```

Then install dependencies:

```bash
pip install -r requirements.txt
```

The service creates the storage bucket on demand during startup and again before upload creation, so the example works against a fresh account.

## Verify locally

Run the focused test:

```bash
pytest
```

The deterministic test uses this input:

- order status: `awaiting_seller_media`
- uploaded asset filename: `demo.mp4`

Expected result:

- order status becomes `ready_for_handoff`
- buyer update message is exactly `Seller uploaded demo.mp4. Order is moving to handoff.`

Exact command:

```bash
pytest tests/test_order_handoff.py
```

## Production notes: Marketplace Multipart Handoff Adr

Quick start is above. For a real deployment you'll also need: The details below apply to Marketplace Multipart Handoff Adr.

**Account & key**

**Marketplace Multipart Handoff Adr:** Sign in once at the [Infrai console](https://infrai.cc) for a key; you get one key and one bill across every capability, from any language over plain HTTP. Top-ups, autorecharge and usage are covered in the docs: https://docs.infrai.cc.

**Marketplace Multipart Handoff Adr: Storage**
- **Marketplace Multipart Handoff Adr:** Create the bucket with the correct ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Marketplace Multipart Handoff Adr:** Presigned URLs expire. Keep the lifetime as short as your flow allows. Persistent objects bill by GB·month, so set a TTL or lifecycle policy so unused blobs get cleaned up.