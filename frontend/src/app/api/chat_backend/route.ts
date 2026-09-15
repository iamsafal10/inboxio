import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.INBOXIO_API_URL ?? "http://127.0.0.1:8000";
const CHAT_TIMEOUT_MS = 600_000; // 10 min — local Ollama can take several minutes

export async function POST(req: NextRequest) {
  const body = await req.text();
  const auth = req.headers.get("authorization");

  try {
    const res = await fetch(`${BACKEND}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(auth ? { Authorization: auth } : {}),
      },
      body,
      signal: AbortSignal.timeout(CHAT_TIMEOUT_MS),
    });

    const text = await res.text();
    return new NextResponse(text, {
      status: res.status,
      headers: {
        "Content-Type": res.headers.get("content-type") ?? "application/json",
      },
    });
  } catch (err: unknown) {
    const message =
      err instanceof Error ? err.message : "Failed to reach chat backend";
    return NextResponse.json(
      { detail: `Chat backend unreachable or timed out: ${message}` },
      { status: 504 }
    );
  }
}
