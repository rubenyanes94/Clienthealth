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
    <div className="grid h-full min-h-0 grid-cols-[minmax(0,1fr)] lg:grid-cols-[22rem_minmax(0,1fr)] xl:grid-cols-[22rem_minmax(0,1fr)_19rem]">
      <div
        className={clsx(
          "min-h-0 border-line bg-surface lg:border-r",
          selectedId !== null && "hidden lg:block",
        )}
      >
        <div className="flex items-center justify-between px-4 pt-4">
          <h1 className="text-lg font-semibold">Conversaciones</h1>
          {canSimulate && (
            <Button size="sm" variant="ghost" onClick={() => setSimulator(true)}>
              <FlaskConical className="size-4" aria-hidden /> Simular
            </Button>
          )}
        </div>
        <div className="h-[calc(100%-3rem)]">
          <ConversationList
            filter={filter}
            onFilter={(f) => setSearch({ filtro: f })}
            selectedId={selectedId}
          />
        </div>
      </div>

      <div className={clsx("min-h-0", selectedId === null && "hidden lg:block")}>
        {selectedId === null && (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-sm text-ink-3">
            <MessagesSquare className="size-8" aria-hidden />
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
        <div
          className={clsx(
            "min-h-0 border-l border-line bg-surface-2",
            showInspector
              ? "fixed inset-y-0 right-0 z-40 w-[min(19rem,100vw)] shadow-pop"
              : "hidden",
            "xl:static xl:block xl:w-auto xl:shadow-none",
          )}
        >
          <Inspector
            conversation={conversation.data}
            canAct={permissionsFor(conversation.data, me.data).canAct}
          />
        </div>
      )}
      <SimulatorDialog open={simulator} onClose={() => setSimulator(false)} />
    </div>
  );
}
