"use client";

import { useContext, useEffect, useRef, useState } from "react";

import { WebSocketContext, type WebSocketContextValue } from "./context";
import type { StepUpdatePayload, WebSocketServerMessage, WebSocketStatus } from "./types";

export function useWebSocket(): WebSocketContextValue {
  const ctx = useContext(WebSocketContext);
  if (!ctx) {
    throw new Error("useWebSocket must be used within a WebSocketProvider");
  }
  return ctx;
}

export function useWebSocketStatus(): WebSocketStatus {
  return useWebSocket().status;
}

export function useSubscription(
  channel: string | undefined,
  onMessage: (message: WebSocketServerMessage) => void
) {
  const { subscribe } = useWebSocket();
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  useEffect(() => {
    if (!channel) return;
    return subscribe(channel, (message) => onMessageRef.current(message));
  }, [channel, subscribe]);
}

export function useProtocolUpdates<TPayload = unknown>(protocolId: number | undefined) {
  const [lastUpdate, setLastUpdate] = useState<WebSocketServerMessage | null>(null);

  useSubscription(protocolId ? `protocol:${protocolId}` : undefined, (message) => {
    setLastUpdate(message);
  });

  return lastUpdate as (WebSocketServerMessage & { payload?: TPayload }) | null;
}

/**
 * Hook to subscribe to step run updates via WebSocket
 * @param stepId - The step ID to subscribe to updates for
 * @returns The latest step update message or null if no updates received
 */
export function useStepUpdates(stepId: number | undefined) {
  const [lastUpdate, setLastUpdate] = useState<WebSocketServerMessage | null>(null);

  useSubscription(stepId ? `step:${stepId}` : undefined, (message) => {
    setLastUpdate(message);
  });

  return lastUpdate as (WebSocketServerMessage & { payload?: StepUpdatePayload }) | null;
}
