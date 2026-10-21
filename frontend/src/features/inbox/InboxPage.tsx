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
    <div className="grid h-full min-h-0 grid-cols-[minmax(0,1fr)] lg:grid-cols-[23rem_minmax(0,1fr)] xl:grid-cols-[23rem_minmax(0,1fr)_21rem]">
      <div
        className={clsx(
          "flex min-h-0 flex-col border-line bg-surface lg:border-r",
          selectedId !== null && "hidden lg:flex",
        )}
      >
        <div className="flex items-center justify-between px-4 pt-5 pb-4">
          <h1 className="text-xl font-semibold">Conversaciones</h1>
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

      <div className={clsx("min-h-0", selectedId === null && "hidden lg:block")}>
        {selectedId === null && (
          <div className="flex h-full flex-col items-center justify-center gap-3 bg-surface-2 text-sm text-ink-3">
            <div className="flex size-12 items-center justify-center rounded-2xl bg-surface shadow-card ring-1 ring-black/5">
              <MessagesSquare className="size-5 text-ink-2" aria-hidden />
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
              className="fixed inset-0 z-30 bg-zinc-950/20 xl:hidden"
              onClick={() => setShowInspector(false)}
              aria-hidden
            />
          )}
          <div
            className={clsx(
              "min-h-0 border-l border-line bg-surface",
              showInspector
                ? "fixed inset-y-0 right-0 z-40 w-[min(21rem,92vw)] shadow-pop"
                : "hidden",
              "xl:static xl:z-auto xl:block xl:w-auto xl:shadow-none",
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
