import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef } from "react";
import { api, unwrap } from "./client";
import type { CaseSearch, CaseStage, InboxFilter, PatientIn, Priority } from "./types";

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

const CASE_POLL_MS = 5_000;

export function useCases(search: CaseSearch) {
  return useQuery({
    queryKey: ["cases", search],
    queryFn: () => unwrap(api.POST("/api/cases/search", { body: search })),
    placeholderData: keepPreviousData,
    refetchInterval: CASE_POLL_MS,
    refetchIntervalInBackground: false,
  });
}

/** Situación de la sala. Sin datos de pacientes: solo conteos y tiempos. */
export function useCasesLive() {
  return useQuery({
    queryKey: ["cases-live"],
    queryFn: () => unwrap(api.GET("/api/cases/live")),
    refetchInterval: CASE_POLL_MS,
    refetchIntervalInBackground: false,
  });
}

export function useCase(id: number) {
  return useQuery({
    queryKey: ["case", id],
    queryFn: () => unwrap(api.GET("/api/cases/{case_id}", { params: { path: { case_id: id } } })),
    refetchInterval: CASE_POLL_MS,
    refetchIntervalInBackground: false,
  });
}

export function useCreateCase() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      patient_id: number;
      area_id: number;
      subject: string;
      description: string;
      priority: Priority;
      conversation_id: number | null;
    }) => unwrap(api.POST("/api/cases", { body })),
    onSuccess: async (created) => {
      await queryClient.invalidateQueries({ queryKey: ["cases"] });
      await queryClient.invalidateQueries({ queryKey: ["cases-live"] });
      await queryClient.invalidateQueries({ queryKey: ["patient", created.patient.id] });
      if (created.conversation_id !== null) {
        await queryClient.invalidateQueries({
          queryKey: keys.conversation(created.conversation_id),
        });
      }
    },
  });
}

export function useCaseActions(id: number) {
  const queryClient = useQueryClient();
  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ["case", id] });
    await queryClient.invalidateQueries({ queryKey: ["cases"] });
    await queryClient.invalidateQueries({ queryKey: ["cases-live"] });
  };
  const path = { params: { path: { case_id: id } } };
  return {
    stage: useMutation({
      mutationFn: (body: { stage: CaseStage; contact_reason_id?: number }) =>
        unwrap(api.POST("/api/cases/{case_id}/stage", { ...path, body })),
      // También si falla: lo normal es que otra tableta se haya adelantado.
      onSettled: refresh,
    }),
    transfer: useMutation({
      mutationFn: (area_id: number) =>
        unwrap(api.POST("/api/cases/{case_id}/transfer", { ...path, body: { area_id } })),
      onSettled: refresh,
    }),
    take: useMutation({
      mutationFn: () => unwrap(api.POST("/api/cases/{case_id}/take", path)),
      onSettled: refresh,
    }),
    update: useMutation({
      mutationFn: (body: { subject: string; description: string; priority: Priority }) =>
        unwrap(api.PATCH("/api/cases/{case_id}", { ...path, body })),
      onSettled: refresh,
    }),
    note: useMutation({
      mutationFn: (body: string) =>
        unwrap(api.POST("/api/cases/{case_id}/notes", { ...path, body: { body } })),
      onSettled: refresh,
    }),
  };
}

export function usePatientSearch(q: string) {
  return useQuery({
    queryKey: ["patients", q],
    queryFn: () => unwrap(api.POST("/api/patients/search", { body: { q } })),
    placeholderData: keepPreviousData,
  });
}

export function usePatient(id: number) {
  return useQuery({
    queryKey: ["patient", id],
    queryFn: () =>
      unwrap(api.GET("/api/patients/{patient_id}", { params: { path: { patient_id: id } } })),
  });
}

export function useSavePatient(id?: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: PatientIn) =>
      id === undefined
        ? unwrap(api.POST("/api/patients", { body }))
        : unwrap(
            api.PATCH("/api/patients/{patient_id}", {
              params: { path: { patient_id: id } },
              body,
            }),
          ),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["patients"] });
      await queryClient.invalidateQueries({ queryKey: ["patient"] });
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
    mutationFn: (body: { contact_reason_id: number; send_survey: boolean }) =>
      unwrap(api.POST("/api/conversations/{conversation_id}/close", { ...path, body })),
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

/** Copiloto: el resultado siempre lo revisa el agente antes de usarlo. */
export function useCopilot(id: number) {
  const path = { params: { path: { conversation_id: id } } };
  return {
    summary: useMutation({
      mutationFn: () => unwrap(api.POST("/api/copilot/{conversation_id}/summary", path)),
    }),
    suggest: useMutation({
      mutationFn: () => unwrap(api.POST("/api/copilot/{conversation_id}/suggest", path)),
    }),
    rewrite: useMutation({
      mutationFn: (draft: string) =>
        unwrap(api.POST("/api/copilot/{conversation_id}/rewrite", { ...path, body: { draft } })),
    }),
    reason: useMutation({
      mutationFn: () => unwrap(api.POST("/api/copilot/{conversation_id}/reason", path)),
    }),
  };
}

export function useContactConsent(conversationId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ contactId, optIn }: { contactId: number; optIn: boolean }) =>
      unwrap(
        api.PUT("/api/contacts/{contact_id}/consent", {
          params: { path: { contact_id: contactId } },
          body: { opt_in: optIn },
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.conversation(conversationId) }),
  });
}

type MetricsQuery = { from: string; to: string; area_id?: number };

/** Indicadores (supervisores). Se refrescan cada minuto con la pestaña visible. */
export function useMetrics(query: MetricsQuery) {
  const options = { params: { query } };
  const common = {
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
    placeholderData: keepPreviousData,
  };
  return {
    overview: useQuery({
      queryKey: ["metrics", "overview", query],
      queryFn: () => unwrap(api.GET("/api/metrics/overview", options)),
      ...common,
    }),
    byHour: useQuery({
      queryKey: ["metrics", "by-hour", query],
      queryFn: () => unwrap(api.GET("/api/metrics/by-hour", options)),
      ...common,
    }),
    byArea: useQuery({
      queryKey: ["metrics", "by-area", query],
      queryFn: () => unwrap(api.GET("/api/metrics/by-area", options)),
      ...common,
    }),
    byAgent: useQuery({
      queryKey: ["metrics", "by-agent", query],
      queryFn: () => unwrap(api.GET("/api/metrics/by-agent", options)),
      ...common,
    }),
    reasons: useQuery({
      queryKey: ["metrics", "reasons", query],
      queryFn: () => unwrap(api.GET("/api/metrics/reasons", options)),
      ...common,
    }),
    csatDaily: useQuery({
      queryKey: ["metrics", "csat-daily", query],
      queryFn: () => unwrap(api.GET("/api/metrics/csat-daily", options)),
      ...common,
    }),
  };
}
