import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { ToastProvider } from "@/components/ui/Toast";
import { Composer } from "./Composer";

function wrap(node: ReactNode) {
  return (
    <QueryClientProvider client={new QueryClient()}>
      <ToastProvider>{node}</ToastProvider>
    </QueryClientProvider>
  );
}

describe("Composer", () => {
  it("vuelve a modo respuesta al aceptar el caso (no deja al agente escribiendo notas)", () => {
    const props = { conversationId: 1, canNote: true, blockedReason: "Acepte el caso" };
    const { rerender } = render(wrap(<Composer {...props} canReply={false} />));
    expect(screen.getByLabelText("Nota interna", { selector: "textarea" })).toBeInTheDocument();

    rerender(wrap(<Composer {...props} canReply blockedReason={null} />));
    expect(screen.getByLabelText("Respuesta al paciente")).toBeInTheDocument();
  });
});
