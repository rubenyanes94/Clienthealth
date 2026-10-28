import clsx from "clsx";
import { ArrowUp, Lock, Sparkles, WandSparkles } from "lucide-react";
import { useState, type KeyboardEvent } from "react";
import { useConversationActions, useCopilot } from "@/api/hooks";
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
  const copilot = useCopilot(conversationId);
  const toast = useToast();
  const isNote = note || !canReply;
  const enabled = isNote ? canNote : canReply;
  const thinking = copilot.suggest.isPending || copilot.rewrite.isPending;

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

  const fill = (result: { text: string }) => setText(result.text);
  const onError = (error: Error) => toast.error(error.message);

  if (!canReply && !canNote) {
    return (
      <div className="border-t border-line bg-surface px-5 py-5 text-center text-sm text-ink-3">
        {blockedReason}
      </div>
    );
  }

  return (
    <div className="border-t border-line bg-surface p-3 sm:px-5 sm:pb-4">
      <div className="mb-3 flex flex-wrap items-center gap-1.5 text-[13px]">
        <button
          type="button"
          onClick={() => setNote(false)}
          disabled={!canReply}
          className={clsx(
            "h-9 rounded-full px-4 font-medium transition",
            !isNote
              ? "bg-ink text-white"
              : "bg-surface-3 text-ink-3 hover:text-ink disabled:opacity-40",
          )}
        >
          Responder
        </button>
        <button
          type="button"
          onClick={() => setNote(true)}
          disabled={!canNote}
          className={clsx(
            "flex h-9 items-center gap-1.5 rounded-full px-4 font-medium transition",
            isNote
              ? "bg-note-soft text-note ring-1 ring-yellow-600/20"
              : "bg-surface-3 text-ink-3 hover:text-ink",
          )}
        >
          <Lock className="size-3" aria-hidden /> Nota interna
        </button>
        {!canReply && blockedReason && <span className="ml-1 text-ink-3">{blockedReason}</span>}
        {canReply && !isNote && (
          <div className="ml-auto flex gap-1">
            <Button
              variant="ai"
              size="sm"
              disabled={thinking}
              onClick={() => copilot.suggest.mutate(undefined, { onSuccess: fill, onError })}
            >
              <Sparkles className="size-3.5" aria-hidden />
              {copilot.suggest.isPending ? "Pensando…" : "Sugerir"}
            </Button>
            <Button
              variant="ai"
              size="sm"
              disabled={thinking || !text.trim()}
              onClick={() => copilot.rewrite.mutate(text, { onSuccess: fill, onError })}
            >
              <WandSparkles className="size-3.5" aria-hidden />
              {copilot.rewrite.isPending ? "Mejorando…" : "Mejorar"}
            </Button>
          </div>
        )}
      </div>
      <div
        className={clsx(
          "flex items-end gap-2 rounded-3xl p-2 ring-1 ring-inset transition focus-within:ring-2",
          isNote
            ? "bg-note-soft ring-yellow-600/25 focus-within:ring-note"
            : "bg-surface-2 ring-line-strong focus-within:bg-surface focus-within:ring-ink",
        )}
      >
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
            isNote ? "Nota visible solo para el equipo…" : "Escriba su respuesta…  (Ctrl+Enter)"
          }
          className="max-h-48 min-h-12 flex-1 resize-none bg-transparent px-3 py-2 text-base outline-none placeholder:text-ink-3"
        />
        <Button
          variant="primary"
          className="size-12 px-0"
          onClick={submit}
          disabled={!text.trim() || send.isPending}
          aria-label={isNote ? "Guardar nota" : "Enviar"}
        >
          <ArrowUp className="size-5" aria-hidden />
        </Button>
      </div>
      {canReply && !isNote && (
        <p className="mt-2 px-2 text-xs text-ink-3">
          Las propuestas del copiloto no se envían solas: revíselas antes de enviar.
        </p>
      )}
    </div>
  );
}
