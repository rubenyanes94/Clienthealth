import clsx from "clsx";
import { FlaskConical, MessagesSquare } from "lucide-react";
import { useState } from "react";
import { useParams, useSearchParams } from "react-router";
import { useConversation, useHealth, useMe } from "@/api/hooks";
import type { InboxFilter } from "@/api/types";
import { Button } from "@/components/ui/Button";
import { ChatView } from "./ChatView";
import { permissionsFor } from "./permissions";
import { ConversationList } from "./ConversationList";
import { Inspector } from "./Inspector";
import { SimulatorDialog } from "./SimulatorDialog";

const FILTERS: InboxFilter[] = ["open", "queue", "mine", "pending", "closed", "bot"];

export function InboxPage() {
  const params = useParams();
  const [search, setSearch] = useSearchParams();
  const me = useMe();
  const health = useHealth();
  const [showInspector, setShowInspector] = useState(false);
  const [simulator, setSimulator] = useState(false);

  const selectedId = params.id ? Number(params.id) : null;
  const raw = search.get("filtro") as InboxFilter | null;
  const filter: InboxFilter = raw && FILTERS.includes(raw) ? raw : "open";
  const conversation = useConversation(selectedId);
  const canSimulate =
    me.data?.role !== "agent" && health.data && health.data.environment !== "production";

  return (
    <div className="grid h-full min-h-0 grid-cols-[minmax(0,1fr)] gap-3 p-2 md:p-0 lg:grid-cols-[22rem_minmax(0,1fr)] xl:grid-cols-[23rem_minmax(0,1fr)_22rem]">
      <div
        className={clsx(
          "flex min-h-0 flex-col overflow-hidden rounded-3xl bg-surface shadow-card",
          selectedId !== null && "hidden lg:flex",
        )}
      >
        <div className="flex items-center justify-between px-5 pt-6 pb-4">
          <h1 className="text-2xl font-bold">Conversaciones</h1>
          {canSimulate && (
            <Button size="sm" variant="secondary" onClick={() => setSimulator(true)}>
              <FlaskConical className="size-3.5" aria-hidden /> Simular
            </Button>
          )}
        </div>
        <div className="min-h-0 flex-1">
          <ConversationList
            filter={filter}
            onFilter={(f) => setSearch({ filtro: f })}
            selectedId={selectedId}
          />
        </div>
      </div>

      <div
        className={clsx(
          "min-h-0 overflow-hidden rounded-3xl bg-surface shadow-card",
          selectedId === null && "hidden lg:block",
        )}
      >
        {selectedId === null && (
          <div className="flex h-full flex-col items-center justify-center gap-4 text-sm text-ink-3">
            <div className="flex size-16 items-center justify-center rounded-full bg-ink text-white shadow-pop">
              <MessagesSquare className="size-6" aria-hidden />
            </div>
            Seleccione una conversación
          </div>
        )}
        {conversation.isPending && selectedId !== null && (
          <p className="p-6 text-sm text-ink-3">Cargando…</p>
        )}
        {conversation.error && (
          <p className="p-6 text-sm text-danger">{conversation.error.message}</p>
        )}
        {conversation.data && (
          <ChatView
            conversation={conversation.data}
            backTo={`/conversaciones?filtro=${filter}`}
            onToggleInspector={() => setShowInspector((v) => !v)}
          />
        )}
      </div>

      {conversation.data && (
        <>
          {showInspector && (
            <div
              className="fixed inset-0 z-30 bg-zinc-950/30 backdrop-blur-[2px] xl:hidden"
              onClick={() => setShowInspector(false)}
              aria-hidden
            />
          )}
          <div
            className={clsx(
              "min-h-0 overflow-hidden rounded-3xl bg-surface",
              showInspector
                ? "fixed inset-y-2 right-2 z-40 w-[min(24rem,92vw)] shadow-pop"
                : "hidden",
              "xl:static xl:z-auto xl:block xl:w-auto xl:shadow-card",
            )}
          >
            <Inspector
              conversation={conversation.data}
              canAct={permissionsFor(conversation.data, me.data).canAct}
            />
          </div>
        </>
      )}
      <SimulatorDialog open={simulator} onClose={() => setSimulator(false)} />
    </div>
  );
}
