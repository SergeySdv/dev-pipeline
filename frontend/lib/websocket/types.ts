"use client"

export type WebSocketStatus = "disconnected" | "connecting" | "connected" | "error"

/**
 * Connection state for WebSocket with more granular reconnection tracking
 */
export type ConnectionState = "connecting" | "connected" | "disconnected" | "reconnecting"

/**
 * Channel types for WebSocket subscriptions
 * - protocol:{id} - Subscribe to protocol run updates
 * - step:{id} - Subscribe to step run updates
 * - events - Subscribe to system events
 * - agents - Subscribe to agent status updates
 */
export type Channel =
  | `protocol:${number}`
  | `step:${number}`
  | "events"
  | "agents"

export type WebSocketChannel = string

/**
 * WebSocket message types for different update categories
 */
export type WebSocketMessageType =
  | "protocol_update"
  | "step_update"
  | "event"
  | "ping"
  | "pong"

/**
 * Base WebSocket message structure
 */
export interface WebSocketMessage<TPayload = unknown> {
  type: WebSocketMessageType
  channel: string
  payload: TPayload
  timestamp: string
}

/**
 * Protocol update message payload
 */
export interface ProtocolUpdatePayload {
  id: number
  status: string
  updated_at: string
}

/**
 * Step update message payload
 */
export interface StepUpdatePayload {
  id: number
  status: string
  started_at?: string
  finished_at?: string
}

/**
 * Protocol update message
 */
export interface ProtocolUpdateMessage extends WebSocketMessage<ProtocolUpdatePayload> {
  type: "protocol_update"
  channel: `protocol:${number}`
}

/**
 * Step update message
 */
export interface StepUpdateMessage extends WebSocketMessage<StepUpdatePayload> {
  type: "step_update"
  channel: `step:${number}`
}

/**
 * Event message
 */
export interface EventMessage extends WebSocketMessage<unknown> {
  type: "event"
  channel: "events"
}

export type WebSocketEnvelope<TPayload = unknown> = {
  type: string
  channel?: WebSocketChannel
  payload?: TPayload
  id?: string
  ts?: string
}

export type WebSocketClientMessage =
  | { type: "ping" }
  | { type: "subscribe"; channels: WebSocketChannel[] }
  | { type: "unsubscribe"; channels: WebSocketChannel[] }
  | { type: "message"; channel: WebSocketChannel; payload: unknown }

export type WebSocketServerMessage = WebSocketEnvelope

