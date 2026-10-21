import clsx from "clsx";
import { Lock, Send } from "lucide-react";
import { useState, type KeyboardEvent } from "react";
import { useConversationActions } from "@/api/hooks";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";

export function Composer({
  conversationId,
  canReply,
  canNote,
  blockedReason,
}: {
  conversationId: number;
  canReply: boolean;
  canNote: boolean;
  blockedReason: string | null;
}) {
  const [text, setText] = useState("");
  // Si no se puede responder, el modo es nota; al aceptar el caso vuelve solo a "Responder".
  const [note, setNote] = useState(false);
  const { send } = useConversationActions(conversationId);
  const toast = useToast();
  const isNote = note || !canReply;
  const enabled = isNote ? canNote : canReply;

  const submit = () => {
    const body = text.trim();
    if (!body || !enabled) return;
    send.mutate(
      { body, is_internal_note: isNote },
      {
        onSuccess: () => setText(""),
        onError: (error) => toast.error(error.message),
      },
    );
  };

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      submit();
    }
  };

  if (!canReply && !canNote) {
    return (
      <div className="border-t border-line bg-surface px-4 py-3 text-sm text-ink-3">
        {blockedReason}
      </div>
    );
  }

  return (
    <div className={clsx("border-t border-line p-3", isNote ? "bg-note-soft" : "bg-surface")}>
      <div className="mb-2 flex items-center gap-2 text-xs">
        <button
          type="button"
          onClick={() => setNote(false)}
          disabled={!canReply}
          className={clsx(
            "rounded-md px-2 py-1 font-medium",
            !isNote ? "bg-brand-soft text-brand" : "text-ink-3 disabled:opacity-40",
          )}
        >
          Responder
        </button>
        <button
          type="button"
          onClick={() => setNote(true)}
          disabled={!canNote}
          className={clsx(
            "flex items-center gap-1 rounded-md px-2 py-1 font-medium",
            isNote ? "bg-note/15 text-note" : "text-ink-3",
          )}
        >
          <Lock className="size-3" aria-hidden /> Nota interna
        </button>
        {!canReply && blockedReason && <span className="text-ink-3">{blockedReason}</span>}
      </div>
      <div className="flex items-end gap-2">
        <label className="sr-only" htmlFor="composer">
          {isNote ? "Nota interna" : "Respuesta al paciente"}
        </label>
        <textarea
          id="composer"
          rows={2}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={
            isNote ? "Nota visible solo para el equipo…" : "Escriba su respuesta… (Ctrl+Enter)"
          }
          className="max-h-40 min-h-[2.75rem] flex-1 resize-y rounded-lg border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-brand"
        />
        <Button
          variant="primary"
          onClick={submit}
          disabled={!text.trim() || send.isPending}
          aria-label={isNote ? "Guardar nota" : "Enviar"}
        >
          <Send className="size-4" aria-hidden />
        </Button>
      </div>
    </div>
  );
}
