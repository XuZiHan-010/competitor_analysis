import type { NextRequest } from "next/server";

// Next's rewrites() proxy buffers responses and breaks long-lived
// text/event-stream over HTTP/2 (net::ERR_HTTP2_PROTOCOL_ERROR on Railway).
// This handler proxies the SSE stream manually, passing the backend's
// ReadableStream body straight through, so the PRD §五.Y SSE contract
// (heartbeat + Last-Event-ID reconnect) survives. Other /api/* routes keep
// using the rewrite; this filesystem route takes precedence for /events only.
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Keep in sync with next.config.ts rewrites() backendUrl resolution.
const backendUrl =
  process.env.BACKEND_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://127.0.0.1:8000";

function streamProxyErrorEvent(runId: string, message: string): Response {
  const event = {
    id: 0,
    run_id: runId,
    event: "stream.error",
    data: { message },
    created_at: new Date().toISOString(),
  };

  return new Response(`event: stream.error\ndata: ${JSON.stringify(event)}\n\n`, {
    status: 200,
    headers: {
      "content-type": "text/event-stream; charset=utf-8",
      "cache-control": "no-cache, no-transform",
      "x-accel-buffering": "no",
    },
  });
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
): Promise<Response> {
  const { id } = await params;

  const headers = new Headers({ accept: "text/event-stream" });
  // Same-origin request: forward the session cookie so the backend auth check
  // ([stream.py] 403 on missing/foreign user) passes, and Last-Event-ID so a
  // reconnect resumes after the last delivered event.
  const cookie = request.headers.get("cookie");
  if (cookie) headers.set("cookie", cookie);
  const lastEventId = request.headers.get("last-event-id");
  if (lastEventId) headers.set("last-event-id", lastEventId);

  let upstream: Response;
  try {
    upstream = await fetch(`${backendUrl}/api/tasks/${id}/events`, {
      headers,
      cache: "no-store",
      // Abort the upstream stream when the browser disconnects so the backend
      // StreamBridge subscriber is cleaned up.
      signal: request.signal,
    });
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      return new Response(null, { status: 204 });
    }
    return streamProxyErrorEvent(
      id,
      "事件流连接中断，任务仍可能在后台运行；页面将继续刷新任务状态。",
    );
  }

  if (!upstream.ok || !upstream.body) {
    if (upstream.status >= 500 || !upstream.body) {
      return streamProxyErrorEvent(
        id,
        "事件流暂时不可用，任务仍可能在后台运行；页面将继续刷新任务状态。",
      );
    }
    return new Response(await upstream.text(), { status: upstream.status });
  }

  return new Response(upstream.body, {
    status: 200,
    headers: {
      "content-type": "text/event-stream; charset=utf-8",
      "cache-control": "no-cache, no-transform",
      "x-accel-buffering": "no",
    },
  });
}
