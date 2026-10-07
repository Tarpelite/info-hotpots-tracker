import { normalizeSnapshot } from "../utils/normalizeSnapshot.js";

const DEFAULT_CONFIG = {
  snapshotEndpoint: "/api/public/snapshot",
  snapshotFallback: "/result/data.json",
  askEndpoint: "/api/ask"
};

function getConfig() {
  return { ...DEFAULT_CONFIG, ...(window.AI4S_PUBLIC_CONFIG ?? {}) };
}

async function fetchJson(url, options) {
  const response = await fetch(url, {
    headers: {
      Accept: "application/json",
      ...(options?.headers ?? {})
    },
    ...options
  });

  if (!response.ok) {
    const error = new Error(`HTTP ${response.status}`);
    error.status = response.status;
    error.url = url;
    throw error;
  }

  return response.json();
}

export async function fetchPublicSnapshot() {
  const config = getConfig();

  try {
    const data = await fetchJson(config.snapshotEndpoint);
    return { data: normalizeSnapshot(data), source: "api" };
  } catch (apiError) {
    const data = await fetchJson(config.snapshotFallback);
    return {
      data: normalizeSnapshot(data),
      source: "result-data",
      apiError: {
        message: apiError.message,
        status: apiError.status ?? null
      }
    };
  }
}

function normalizeAnswer(payload) {
  const body = payload?.data ?? payload;
  return {
    answer: body?.answer ?? body?.content ?? "",
    citations: body?.citations ?? body?.sources ?? [],
    evidence: body?.evidence ?? [],
    traceId: body?.trace_id ?? body?.traceId ?? ""
  };
}

export async function askQuestion(question) {
  const config = getConfig();
  const payload = await fetchJson(config.askEndpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ question })
  });

  return normalizeAnswer(payload);
}
