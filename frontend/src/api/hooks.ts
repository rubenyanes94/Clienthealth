import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef } from "react";
import { api, unwrap } from "./client";
import type { InboxFilter } from "./types";

export const keys = {
  me: ["me"] as const,
  inbox: (filter: InboxFilter) => ["inbox", filter] as const,
  conversation: (id: number) => ["conversation", id] as const,
  catalog: ["catalog"] as const,
  live: ["live"] as const,
};

export function useMe() {
  return useQuery({
    queryKey: keys.me,
    queryFn: async () => {
      const { data, response } = await api.GET("/api/auth/me");
      return response.ok ? (data ?? null) : null;
    },
    staleTime: 5 * 60_000,
  });
}

export function useInbox(filter: InboxFilter) {
  return useQuery({
    queryKey: keys.inbox(filter),
    queryFn: () => unwrap(api.GET("/api/inbox", { params: { query: { filter } } })),
  });
}

export function useConversation(id: number | null) {
  return useQuery({
    queryKey: keys.conversation(id ?? 0),
    enabled: id !== null,
    queryFn: () =>
      unwrap(
        api.GET("/api/conversations/{conversation_id}", {
          params: { path: { conversation_id: id! } },
        }),
      ),
    refetchInterval: 3_000,
    refetchIntervalInBackground: false,
  });
}

export function useCatalog() {
  return useQuery({
    queryKey: keys.catalog,
    queryFn: () => unwrap(api.GET("/api/catalog")),
    staleTime: 10 * 60_000,
  });
}

export function useLiveMetrics() {
  return useQuery({
    queryKey: keys.live,
    queryFn: () => unwrap(api.GET("/api/metrics/live")),
    refetchInterval: 10_000,
    refetchIntervalInBackground: false,
  });
}

/** Polling de cambios (§8): cada 4 s con la pestaña visible; invalida lo que cambió. */
export function useInboxChanges(enabled: boolean) {
  const queryClient = useQueryClient();
  const since = useRef<string | null>(null);
  return useQuery({
    queryKey: ["inbox-changes"],
    enabled,
    refetchInterval: 4_000,
    refetchIntervalInBackground: false,
    queryFn: async () => {
      const result = await unwrap(
        api.GET("/api/inbox/changes", {
          params: {
            query: { since: since.current ?? new Date(Date.now() - 60_000).toISOString() },
          },
        }),
      );
      since.current = result.server_time;
      if (result.ids.length > 0) {
        await queryClient.invalidateQueries({ queryKey: ["inbox"] });
        await queryClient.invalidateQueries({ queryKey: keys.live });
        for (const id of result.ids) {
          await queryClient.invalidateQueries({ queryKey: keys.conversation(id) });
        }
      }
      return result;
    },
  });
}

type Action = "accept" | "pending" | "resume" | "reopen";

export function useConversationActions(id: number) {
  const queryClient = useQueryClient();
  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ["inbox"] });
    await queryClient.invalidateQueries({ queryKey: keys.conversation(id) });
    await queryClient.invalidateQueries({ queryKey: keys.live });
  };
  const path = { params: { path: { conversation_id: id } } };

  const simple = useMutation({
    mutationFn: (action: Action) => {
      switch (action) {
        case "accept":
          return unwrap(api.POST("/api/conversations/{conversation_id}/accept", path));
        case "pending":
          return unwrap(api.POST("/api/conversations/{conversation_id}/pending", path));
        case "resume":
          return unwrap(api.POST("/api/conversations/{conversation_id}/resume", path));
        case "reopen":
          return unwrap(api.POST("/api/conversations/{conversation_id}/reopen", path));
      }
    },
    onSuccess: refresh,
  });

  const send = useMutation({
    mutationFn: (body: { body: string; is_internal_note: boolean }) =>
      unwrap(api.POST("/api/conversations/{conversation_id}/messages", { ...path, body })),
    onSuccess: refresh,
  });

  const transfer = useMutation({
    mutationFn: (area_id: number) =>
      unwrap(
        api.POST("/api/conversations/{conversation_id}/transfer", { ...path, body: { area_id } }),
      ),
    onSuccess: refresh,
  });

  const close = useMutation({
    mutationFn: (contact_reason_id: number) =>
      unwrap(
        api.POST("/api/conversations/{conversation_id}/close", {
          ...path,
          body: { contact_reason_id },
        }),
      ),
    onSuccess: refresh,
  });

  return { simple, send, transfer, close };
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { email: string; password: string }) =>
      unwrap(api.POST("/api/auth/login", { body })),
    onSuccess: (agent) => queryClient.setQueryData(keys.me, agent),
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.POST("/api/auth/logout"),
    onSuccess: () => {
      queryClient.clear();
      window.location.assign("/login");
    },
  });
}

export function useSimulateInbound() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { text: string; wa_id: string; name: string | null }) =>
      unwrap(api.POST("/api/dev/simulate-inbound", { body })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["inbox"] }),
  });
}

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => unwrap(api.GET("/api/health")),
    staleTime: 60_000,
  });
}
