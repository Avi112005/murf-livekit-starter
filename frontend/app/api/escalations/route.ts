import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.ESCALATION_BACKEND_URL ?? 'http://127.0.0.1:8765';

export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/escalations`, { cache: 'no-store' });
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json(
      { escalations: [], message: 'Start the backend dashboard API first.' },
      { status: 503 }
    );
  }
}
