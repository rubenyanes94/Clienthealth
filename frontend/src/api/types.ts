import type { components } from "./schema";

type S = components["schemas"];

export type Agent = S["AgentOut"];
export type Area = S["AreaOut"];
export type Reason = S["ReasonOut"];
export type ConversationSummary = S["ConversationSummary"];
export type ConversationDetail = S["ConversationDetail"];
export type Message = S["MessageOut"];
export type ConversationEvent = S["EventOut"];
export type ConversationStatus = S["ConversationStatus"];
export type EventType = S["EventType"];
export type LiveMetrics = S["LiveMetrics"];
export type Survey = S["SurveyOut"];
export type InboxFilter = "open" | "queue" | "mine" | "pending" | "closed" | "bot" | "all";
