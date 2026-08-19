/**
 * AppProviders — wires QueryClientProvider + ThemeProvider.
 */

import { render, screen } from "@testing-library/react";
import { useQuery, QueryClient } from "@tanstack/react-query";
import { AppProviders, } from "@/components/providers/AppProviders";
import { getQueryClient } from "@/lib/query-client";

function Probe() {
  const { data } = useQuery({ queryKey: ["probe"], queryFn: () => "ok" });
  return <div>{data ?? "loading"}</div>;
}

describe("AppProviders", () => {
  it("provides a QueryClient context (hooks can query)", async () => {
    render(
      <AppProviders>
        <Probe />
      </AppProviders>,
    );

    expect(await screen.findByText("ok")).toBeInTheDocument();
  });

  it("registers the client for non-React consumers", () => {
    const { unmount } = render(
      <AppProviders>
        <div>child</div>
      </AppProviders>,
    );
    expect(getQueryClient()).toBeInstanceOf(QueryClient);
    unmount();
  });

  it("renders children under the ThemeProvider", () => {
    render(
      <AppProviders>
        <p>Contenido</p>
      </AppProviders>,
    );
    expect(screen.getByText("Contenido")).toBeInTheDocument();
  });
});