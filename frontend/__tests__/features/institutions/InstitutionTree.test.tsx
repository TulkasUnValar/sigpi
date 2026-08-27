/**
 * InstitutionTree — recursive tree, roving focus, keyboard navigation,
 * and per-node action menu.
 *
 * Spec (institutions-ui RF-F01 / RNF-01):
 *   - role="tree"/"treeitem", aria-expanded, aria-level.
 *   - ArrowUp/Down/Left/Right, Home/End, Enter/Space follow the WCAG 2.1
 *     AA tree pattern (roving focus: one tabIndex 0 node at a time).
 *   - Each node renders name, code, StatusBadge and an action menu.
 */

import { render, screen, waitFor, within, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";

jest.mock("next/link", () => {
  return {
    __esModule: true,
    default: ({ href, children, ...rest }: { href: string; children: React.ReactNode }) => (
      <a href={href} {...rest}>
        {children}
      </a>
    ),
  };
});

jest.mock("@/lib/api", () => ({
  api: {
    get: jest.fn(),
    post: jest.fn(),
    patch: jest.fn(),
    delete: jest.fn(),
    upload: jest.fn(),
  },
  getCSRFToken: jest.fn(),
  API_BASE: "http://localhost:8000",
}));

import * as api from "@/lib/api";
import {
  InstitutionTree,
  flattenVisibleNodes,
  findParentId,
} from "@/features/institutions/InstitutionTree";
import type { InstitutionTreeNode } from "@/features/institutions/types";

const nodes: InstitutionTreeNode[] = [
  {
    id: "inst-1",
    kind: "institution",
    name: "Universidad Nacional",
    code: "UNAL",
    status: "active",
    is_active: true,
    children: [
      {
        id: "sede-1",
        kind: "sede",
        name: "Sede Bogotá",
        code: "S-BOG",
        status: "active",
        is_active: true,
        children: [],
      },
      {
        id: "sede-2",
        kind: "sede",
        name: "Sede Medellín",
        code: "S-MED",
        status: "deactivated",
        is_active: false,
        children: [],
      },
    ],
  },
  {
    id: "inst-2",
    kind: "institution",
    name: "Universidad del Valle",
    code: "UVAL",
    status: "active",
    is_active: true,
    children: [],
  },
];

beforeEach(() => {
  jest.clearAllMocks();
});

function renderTree(roles: string[] = ["superadmin"]) {
  useAuthStore.setState({
    roles,
    isAuthenticated: true,
    isLoading: false,
    activeInstitution: { id: "inst-1", name: "Universidad Alpha" },
    institutions: [],
    centers: [],
  });

  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const invalidateSpy = jest.spyOn(qc, "invalidateQueries");

  const utils = render(
    <QueryClientProvider client={qc}>
      <InstitutionTree nodes={nodes} />
    </QueryClientProvider>,
  );
  return { qc, invalidateSpy, ...utils };
}

function treeitems(container: HTMLElement): HTMLElement[] {
  return Array.from(container.querySelectorAll<HTMLElement>('[role="treeitem"]'));
}

async function focusNode(container: HTMLElement, index: number) {
  const items = treeitems(container);
  const target = items[index];
  if (!target) throw new Error(`No treeitem at index ${index}`);
  fireEvent.click(target);
  await waitFor(() => expect(target).toHaveFocus());
  return items;
}

describe("flattenVisibleNodes", () => {
  it("returns roots only when nothing is expanded", () => {
    const visible = flattenVisibleNodes(nodes, new Set());
    expect(visible.map((n) => n.id)).toEqual(["inst-1", "inst-2"]);
  });

  it("recurses into expanded nodes in document order", () => {
    const visible = flattenVisibleNodes(nodes, new Set(["inst-1"]));
    expect(visible.map((n) => n.id)).toEqual(["inst-1", "sede-1", "sede-2", "inst-2"]);
  });

  it("skips expansion for leaf nodes even when marked expanded", () => {
    const visible = flattenVisibleNodes(nodes, new Set(["sede-1"]));
    expect(visible.map((n) => n.id)).toEqual(["inst-1", "inst-2"]);
  });
});

describe("findParentId", () => {
  it("finds a direct parent", () => {
    expect(findParentId(nodes, "sede-1")).toBe("inst-1");
  });

  it("returns null for a root node", () => {
    expect(findParentId(nodes, "inst-1")).toBeNull();
  });

  it("returns null when the node does not exist", () => {
    expect(findParentId(nodes, "missing")).toBeNull();
  });
});

describe("InstitutionTree — structure", () => {
  it("renders a tree with treeitems, names, codes and badges", () => {
    const { container } = renderTree();

    expect(screen.getByRole("tree")).toBeInTheDocument();
    expect(screen.getByRole("tree", { name: "Estructura institucional" })).toBeInTheDocument();

    const items = treeitems(container);
    expect(items).toHaveLength(2);
    expect(screen.getByText("Universidad Nacional")).toBeInTheDocument();
    expect(screen.getByText("UNAL")).toBeInTheDocument();
    expect(screen.getAllByText("Activa").length).toBeGreaterThan(0);
  });

  it("renders aria-level on treeitems", () => {
    const { container } = renderTree();
    const items = treeitems(container);
    expect(items[0]).toHaveAttribute("aria-level", "1");
  });

  it("renders nothing for an empty node list", () => {
    const { container } = render(
      <QueryClientProvider
        client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
      >
        <InstitutionTree nodes={[]} />
      </QueryClientProvider>,
    );
    expect(container.firstChild).toBeNull();
  });

  it("hides children until expanded (aria-expanded=false)", () => {
    const { container } = renderTree();

    expect(screen.queryByText("Sede Bogotá")).not.toBeInTheDocument();
    const root = treeitems(container)[0];
    expect(root).toHaveAttribute("aria-expanded", "false");
  });

  it("leaf nodes expose no aria-expanded and no expand button", () => {
    renderTree();
    // Expand inst-1 via the toggle button.
    const toggle = screen.getByRole("button", { name: "Expandir Universidad Nacional" });
    fireEvent.click(toggle);

    // sede-1 (leaf) → its treeitem has no aria-expanded attribute.
    const sedeLink = screen.getByText("Sede Bogotá");
    const sedeItem = sedeLink.closest('[role="treeitem"]');
    expect(sedeItem).not.toHaveAttribute("aria-expanded");
    expect(screen.queryByRole("button", { name: "Expandir Sede Bogotá" })).not.toBeInTheDocument();
  });
});

describe("InstitutionTree — roving focus", () => {
  it("gives tabIndex 0 to exactly one visible node at a time", async () => {
    const { container } = renderTree();
    const items = treeitems(container);

    expect(items[0]).toHaveAttribute("tabindex", "0");
    expect(items[1]).toHaveAttribute("tabindex", "-1");

    await focusNode(container, 1);
    const after = treeitems(container);
    expect(after[0]).toHaveAttribute("tabindex", "-1");
    expect(after[1]).toHaveAttribute("tabindex", "0");
  });
});

describe("InstitutionTree — keyboard navigation", () => {
  it("ArrowDown moves focus to the next visible node", async () => {
    const { container } = renderTree();
    await focusNode(container, 0);

    fireEvent.keyDown(screen.getByRole("tree"), { key: "ArrowDown" });

    await waitFor(() => {
      const items = treeitems(container);
      expect(items[1]).toHaveFocus();
      expect(items[1]).toHaveAttribute("tabindex", "0");
    });
  });

  it("ArrowUp moves focus to the previous visible node", async () => {
    const { container } = renderTree();
    await focusNode(container, 1);

    fireEvent.keyDown(screen.getByRole("tree"), { key: "ArrowUp" });

    await waitFor(() => {
      expect(treeitems(container)[0]).toHaveFocus();
    });
  });

  it("ArrowRight expands a collapsed node and reveals children", async () => {
    const { container } = renderTree();
    await focusNode(container, 0);

    fireEvent.keyDown(screen.getByRole("tree"), { key: "ArrowRight" });

    await waitFor(() => {
      const root = treeitems(container)[0];
      expect(root).toHaveAttribute("aria-expanded", "true");
      expect(screen.getByText("Sede Bogotá")).toBeInTheDocument();
    });
  });

  it("ArrowRight on an expanded node focuses its first child", async () => {
    const { container } = renderTree();
    await focusNode(container, 0);

    fireEvent.keyDown(screen.getByRole("tree"), { key: "ArrowRight" });
    fireEvent.keyDown(screen.getByRole("tree"), { key: "ArrowRight" });

    await waitFor(() => {
      const items = treeitems(container);
      // visible: inst-1, sede-1, sede-2, inst-2 → first child is sede-1
      expect(items[1]).toHaveFocus();
      expect(items[1]?.textContent).toContain("Sede Bogotá");
    });
  });

  it("ArrowLeft collapses an expanded node", async () => {
    const { container } = renderTree();
    await focusNode(container, 0);

    fireEvent.keyDown(screen.getByRole("tree"), { key: "ArrowRight" });
    await waitFor(() => {
      expect(treeitems(container)[0]).toHaveAttribute("aria-expanded", "true");
    });

    fireEvent.keyDown(screen.getByRole("tree"), { key: "ArrowLeft" });

    await waitFor(() => {
      expect(treeitems(container)[0]).toHaveAttribute("aria-expanded", "false");
      expect(screen.queryByText("Sede Bogotá")).not.toBeInTheDocument();
    });
  });

  it("ArrowLeft on a collapsed child moves focus to its parent", async () => {
    const { container } = renderTree();
    await focusNode(container, 0);

    // Expand inst-1, then focus the first child.
    fireEvent.keyDown(screen.getByRole("tree"), { key: "ArrowRight" });
    fireEvent.keyDown(screen.getByRole("tree"), { key: "ArrowRight" });
    await waitFor(() => {
      expect(treeitems(container)[1]?.textContent).toContain("Sede Bogotá");
    });

    fireEvent.keyDown(screen.getByRole("tree"), { key: "ArrowLeft" });

    await waitFor(() => {
      expect(treeitems(container)[0]).toHaveFocus();
    });
  });

  it("Home and End jump to the first and last visible nodes", async () => {
    const { container } = renderTree();
    await focusNode(container, 1);

    fireEvent.keyDown(screen.getByRole("tree"), { key: "Home" });
    await waitFor(() => {
      expect(treeitems(container)[0]).toHaveFocus();
    });

    fireEvent.keyDown(screen.getByRole("tree"), { key: "End" });
    await waitFor(() => {
      expect(treeitems(container)[1]).toHaveFocus();
    });
  });

  it("Enter and Space toggle expansion", async () => {
    const { container } = renderTree();
    await focusNode(container, 0);

    fireEvent.keyDown(screen.getByRole("tree"), { key: "Enter" });
    await waitFor(() => {
      expect(treeitems(container)[0]).toHaveAttribute("aria-expanded", "true");
    });

    fireEvent.keyDown(screen.getByRole("tree"), { key: " " });
    await waitFor(() => {
      expect(treeitems(container)[0]).toHaveAttribute("aria-expanded", "false");
    });
  });

  it("ignores keys when nothing is focused", () => {
    renderTree();
    const tree = screen.getByRole("tree");
    fireEvent.keyDown(tree, { key: "ArrowDown" });
    // No crash and no focus change.
    expect(tree).toBeInTheDocument();
  });
});

describe("InstitutionTree — expand toggle button", () => {
  it("expands and collapses via the aria-labelled toggle button", () => {
    renderTree();

    fireEvent.click(screen.getByRole("button", { name: "Expandir Universidad Nacional" }));
    expect(screen.getByText("Sede Bogotá")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Contraer Universidad Nacional" }),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Contraer Universidad Nacional" }));
    expect(screen.queryByText("Sede Bogotá")).not.toBeInTheDocument();
  });
});

describe("InstitutionTree — action menu", () => {
  it("opens the per-node menu with detail/edit/delete items", async () => {
    const user = userEvent.setup();
    renderTree();

    await user.click(screen.getByRole("button", { name: "Acciones de Universidad Nacional" }));

    expect(await screen.findByRole("menuitem", { name: /ver detalle/i })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: /editar/i })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: /eliminar/i })).toBeInTheDocument();
  });

  it("links the detail and edit items to the institution routes", async () => {
    const user = userEvent.setup();
    renderTree();

    await user.click(screen.getByRole("button", { name: "Acciones de Universidad Nacional" }));

    const detail = await screen.findByRole("menuitem", { name: /ver detalle/i });
    const edit = screen.getByRole("menuitem", { name: /editar/i });
    expect(detail).toHaveAttribute("href", "/institutions/inst-1");
    expect(edit).toHaveAttribute("href", "/institutions/inst-1/edit");
  });

  it("shows FSM actions for a superadmin on an active node", async () => {
    const user = userEvent.setup();
    renderTree(["superadmin"]);

    await user.click(screen.getByRole("button", { name: "Acciones de Universidad Nacional" }));

    expect(await screen.findByRole("menuitem", { name: /desactivar/i })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: /archivar/i })).toBeInTheDocument();
  });

  it("hides FSM actions for roles without permission", async () => {
    const user = userEvent.setup();
    renderTree(["director"]);

    await user.click(screen.getByRole("button", { name: "Acciones de Universidad Nacional" }));

    expect(await screen.findByRole("menuitem", { name: /ver detalle/i })).toBeInTheDocument();
    expect(screen.queryByRole("menuitem", { name: /desactivar/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("menuitem", { name: /archivar/i })).not.toBeInTheDocument();
  });

  it("deletes a node after ConfirmDialog confirmation", async () => {
    const user = userEvent.setup();
    const { invalidateSpy } = renderTree();

    (api.api.delete as jest.Mock).mockResolvedValue(undefined);

    await user.click(screen.getByRole("button", { name: "Acciones de Universidad Nacional" }));
    await user.click(await screen.findByRole("menuitem", { name: /eliminar/i }));

    const dialog = await screen.findByRole("alertdialog");
    expect(dialog).toHaveTextContent(/¿eliminar institución\?/i);
    expect(api.api.delete).not.toHaveBeenCalled();

    await user.click(within(dialog).getByRole("button", { name: /eliminar/i }));

    await waitFor(() => {
      expect(api.api.delete).toHaveBeenCalledWith("/api/institutions/inst-1/", {
        sendInstitutionId: false,
      });
    });
    await waitFor(() => {
      const calls = invalidateSpy.mock.calls.map((c) => c[0]?.queryKey);
      expect(calls).toContainEqual(["institutions"]);
    });
  });

  it("cancelling the delete dialog does not call the API", async () => {
    const user = userEvent.setup();
    renderTree();

    await user.click(screen.getByRole("button", { name: "Acciones de Universidad Nacional" }));
    await user.click(await screen.findByRole("menuitem", { name: /eliminar/i }));

    const dialog = await screen.findByRole("alertdialog");
    await user.click(within(dialog).getByRole("button", { name: /cancelar/i }));

    expect(api.api.delete).not.toHaveBeenCalled();
  });

  it("confirms destructive FSM actions from the menu", async () => {
    const user = userEvent.setup();
    const { invalidateSpy } = renderTree(["superadmin"]);

    (api.api.post as jest.Mock).mockResolvedValue({
      id: "inst-1",
      status: "archived",
    });

    await user.click(screen.getByRole("button", { name: "Acciones de Universidad Nacional" }));
    await user.click(await screen.findByRole("menuitem", { name: /archivar/i }));

    const dialog = await screen.findByRole("alertdialog");
    await user.click(within(dialog).getByRole("button", { name: /archivar/i }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/institutions/inst-1/archive/",
        {},
        { sendInstitutionId: false },
      );
    });
    await waitFor(() => {
      const calls = invalidateSpy.mock.calls.map((c) => c[0]?.queryKey);
      expect(calls).toContainEqual(["institutions"]);
    });
  });

  it("runs non-destructive FSM actions (activate) without confirmation", async () => {
    const user = userEvent.setup();
    useAuthStore.setState({
      roles: ["superadmin"],
      isAuthenticated: true,
      isLoading: false,
      activeInstitution: { id: "inst-1", name: "Universidad Alpha" },
      institutions: [],
      centers: [],
    });

    const deactivatedNode: InstitutionTreeNode[] = [
      {
        id: "inst-2",
        kind: "institution",
        name: "Universidad del Valle",
        code: "UVAL",
        status: "deactivated",
        is_active: false,
        children: [],
      },
    ];

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    (api.api.post as jest.Mock).mockResolvedValue({
      id: "inst-2",
      status: "active",
    });

    render(
      <QueryClientProvider client={qc}>
        <InstitutionTree nodes={deactivatedNode} />
      </QueryClientProvider>,
    );

    await user.click(screen.getByRole("button", { name: "Acciones de Universidad del Valle" }));
    await user.click(await screen.findByRole("menuitem", { name: /activar/i }));

    await waitFor(() => {
      expect(api.api.post).toHaveBeenCalledWith(
        "/api/institutions/inst-2/activate/",
        {},
        { sendInstitutionId: false },
      );
    });
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
  });
});
