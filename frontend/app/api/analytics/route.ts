import { NextResponse } from 'next/server';

export async function GET() {
  const backend = process.env.ESCALATION_BACKEND_URL ?? 'http://127.0.0.1:8765';
  try {
    const response = await fetch(`${backend}/analytics`, { cache: 'no-store' });
    return NextResponse.json(await response.json(), { status: response.status });
  } catch {
    return NextResponse.json({ total: 0, successful: 0, failed: 0, success_rate: 0, failure_categories: [] }, { status: 503 });
  }
}
