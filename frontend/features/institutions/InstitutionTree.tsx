"use client";

/**
 * InstitutionTree — recursive disclosure tree for the 6-entity hierarchy.
 *
 * Spec (institutions-ui RF-F01 / RNF-01):
 *   - role="tree" / role="treeitem" / role="group" with aria-expanded.
 *   - Roving focus: exactly one visible node has tabIndex 0.
 *   - Keyboard navigation: ArrowUp/ArrowDown (prev/next visible node),
 *     ArrowRight (expand, or first child when expanded), ArrowLeft
 *     (collapse, or focus parent), Home/End, Enter/Space (toggle).
 *   - Each node shows name, code, StatusBadge and an action menu.
 *
 * PR1 renders root institutions (children arrive in PR2/PR3), but the
 * component is fully recursive — the page just passes root nodes.
 */

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import { ChevronRight, MoreHorizontal, Pencil, Trash2, ExternalLink } from "lucide-react";

import { StatusBadge } from "@/components/shared/StatusBadge";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { getErrorMessage } from "@/lib/errors";
import { useAuthStore } from "@/store/auth";
import { useDeleteInstitution, useInstitutionTransition } from "@/features/institutions/mutations";
import {
  getEntityActions,
  isDestructiveEntityAction,
  type FsmAction,
} from "@/features/institutions/fsm";
import type { InstitutionTreeNode } from "@/features/institutions/types";

/** Flatten visible nodes in document order (recursive, expansion-aware). */
export function flattenVisibleNodes(
  nodes: InstitutionTreeNode[],
  expandedIds: Set<string>,
): InstitutionTreeNode[] {
  const visible: InstitutionTreeNode[] = [];
  for (const node of nodes) {
    visible.push(node);
    if (expandedIds.has(node.id) && node.children.length > 0) {
      visible.push(...flattenVisibleNodes(node.children, expandedIds));
    }
  }
  return visible;
}

/** Find the parent id of `id` within the subtree, or null. */
export function findParentId(nodes: InstitutionTreeNode[], id: string): string | null {
  for (const node of nodes) {
    if (node.children.some((c) => c.id === id)) return node.id;
    const nested = findParentId(node.children, id);
    if (nested) return nested;
  }
  return null;
}

interface InstitutionTreeProps {
  nodes: InstitutionTreeNode[];
}

/** Pending confirmation: delete node or run a destructive FSM action. */
type ConfirmState =
  | { kind: "delete"; node: InstitutionTreeNode }
  | { kind: "fsm"; node: InstitutionTreeNode; action: FsmAction }
  | null;

export function InstitutionTree({ nodes }: InstitutionTreeProps) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [focusedId, setFocusedId] = useState<string | null>(null);
  const nodeRefs = useRef<Map<string, HTMLElement>>(new Map());

  const visible = flattenVisibleNodes(nodes, expandedIds);
  const focusedIndex = visible.findIndex((n) => n.id === focusedId);

  // Roving focus: keep the focused node's DOM element focused.
  useEffect(() => {
    if (focusedId) {
      nodeRefs.current.get(focusedId)?.focus();
    }
  }, [focusedId]);

  function toggle(id: string) {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function moveFocus(index: number) {
    if (visible.length === 0) return;
    const clamped = Math.max(0, Math.min(index, visible.length - 1));
    const node = visible[clamped];
    if (node) setFocusedId(node.id);
  }

  function registerRef(id: string, el: HTMLElement | null) {
    if (el) nodeRefs.current.set(id, el);
    else nodeRefs.current.delete(id);
  }

  /** WCAG 2.1 AA tree keyboard pattern. */
  function handleKeyDown(e: React.KeyboardEvent) {
    if (focusedIndex === -1) return;

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        moveFocus(focusedIndex + 1);
        break;
      case "ArrowUp":
        e.preventDefault();
        moveFocus(focusedIndex - 1);
        break;
      case "ArrowRight": {
        e.preventDefault();
        const node = visible[focusedIndex];
        if (!node) break;
        if (node.children.length > 0 && !expandedIds.has(node.id)) {
          toggle(node.id);
        } else if (node.children.length > 0) {
          const firstChild = node.children[0];
          if (firstChild) {
            const idx = visible.findIndex((n) => n.id === firstChild.id);
            if (idx !== -1) moveFocus(idx);
          }
        }
        break;
      }
      case "ArrowLeft": {
        e.preventDefault();
        const node = visible[focusedIndex];
        if (!node) break;
        if (node.children.length > 0 && expandedIds.has(node.id)) {
          toggle(node.id);
        } else {
          const parentId = findParentId(nodes, node.id);
          if (parentId) {
            const idx = visible.findIndex((n) => n.id === parentId);
            if (idx !== -1) moveFocus(idx);
          }
        }
        break;
      }
      case "Home":
        e.preventDefault();
        moveFocus(0);
        break;
      case "End":
        e.preventDefault();
        moveFocus(visible.length - 1);
        break;
      case "Enter":
      case " ": {
        e.preventDefault();
        const node = visible[focusedIndex];
        if (node && node.children.length > 0) toggle(node.id);
        break;
      }
      default:
        break;
    }
  }

  if (nodes.length === 0) return null;

  return (
    <ul
      role="tree"
      aria-label="Estructura institucional"
      onKeyDown={handleKeyDown}
      className="space-y-1"
    >
      {nodes.map((node, index) => (
        <TreeNode
          key={node.id}
          node={node}
          depth={0}
          tabIndex={focusedId === null ? (index === 0 ? 0 : -1) : focusedId === node.id ? 0 : -1}
          expandedIds={expandedIds}
          focusedId={focusedId}
          onToggle={toggle}
          onFocus={setFocusedId}
          registerRef={registerRef}
        />
      ))}
    </ul>
  );
}

interface TreeNodeProps {
  node: InstitutionTreeNode;
  depth: number;
  /** Roving-focus tabIndex: 0 for the active node, -1 otherwise. */
  tabIndex: number;
  expandedIds: Set<string>;
  focusedId: string | null;
  onToggle: (id: string) => void;
  onFocus: (id: string) => void;
  registerRef: (id: string, el: HTMLElement | null) => void;
}

function TreeNode({
  node,
  depth,
  tabIndex,
  expandedIds,
  focusedId,
  onToggle,
  onFocus,
  registerRef,
}: TreeNodeProps) {
  const isExpanded = expandedIds.has(node.id);
  const hasChildren = node.children.length > 0;

  return (
    <li
      role="treeitem"
      aria-level={depth + 1}
      aria-expanded={hasChildren ? isExpanded : undefined}
      aria-selected={focusedId === node.id}
      tabIndex={tabIndex}
      ref={(el) => registerRef(node.id, el)}
      onClick={() => onFocus(node.id)}
      className="rounded-md outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <div
        className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm"
        style={{ paddingLeft: `${depth * 1.5 + 0.5}rem` }}
      >
        {hasChildren ? (
          <button
            type="button"
            aria-label={isExpanded ? `Contraer ${node.name}` : `Expandir ${node.name}`}
            onClick={(e) => {
              e.stopPropagation();
              onToggle(node.id);
            }}
            className="flex h-5 w-5 items-center justify-center rounded text-muted-foreground hover:bg-accent"
          >
            <ChevronRight
              className={`h-4 w-4 transition-transform ${isExpanded ? "rotate-90" : ""}`}
              aria-hidden="true"
            />
          </button>
        ) : (
          <span className="w-5" aria-hidden="true" />
        )}

        <Link
          href={`/institutions/${node.id}`}
          onClick={(e) => e.stopPropagation()}
          className="font-medium hover:underline"
        >
          {node.name}
        </Link>
        <span className="text-xs text-muted-foreground">{node.code}</span>
        <StatusBadge status={node.status} />
        <NodeActions node={node} />
      </div>

      {hasChildren && isExpanded ? (
        <ul role="group">
          {node.children.map((child) => (
            <TreeNode
              key={child.id}
              node={child}
              depth={depth + 1}
              tabIndex={focusedId === child.id ? 0 : -1}
              expandedIds={expandedIds}
              focusedId={focusedId}
              onToggle={onToggle}
              onFocus={onFocus}
              registerRef={registerRef}
            />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

/** Per-node action menu: detail/edit links, FSM transitions, delete. */
function NodeActions({ node }: { node: InstitutionTreeNode }) {
  const roles = useAuthStore((s) => s.roles);
  const transition = useInstitutionTransition();
  const remove = useDeleteInstitution();
  const [confirm, setConfirm] = useState<ConfirmState>(null);

  const fsmActions = getEntityActions(node.status, roles);

  function runFsm(action: FsmAction) {
    transition.mutate(
      { id: node.id, action: action.name },
      {
        onSuccess: () => {
          toast.success(`Institución ${action.label.toLowerCase()}.`);
        },
        onError: (error) => {
          toast.error(getErrorMessage(error));
        },
      },
    );
  }

  function runDelete() {
    remove.mutate(node.id, {
      onSuccess: () => {
        toast.success("Institución eliminada.");
      },
      onError: (error) => {
        toast.error(getErrorMessage(error));
      },
    });
  }

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 w-7 p-0"
            aria-label={`Acciones de ${node.name}`}
          >
            <MoreHorizontal className="h-4 w-4" aria-hidden="true" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start">
          <DropdownMenuLabel>{node.name}</DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem asChild>
            <Link href={`/institutions/${node.id}`}>
              <ExternalLink className="mr-2 h-4 w-4" aria-hidden="true" />
              Ver detalle
            </Link>
          </DropdownMenuItem>
          <DropdownMenuItem asChild>
            <Link href={`/institutions/${node.id}/edit`}>
              <Pencil className="mr-2 h-4 w-4" aria-hidden="true" />
              Editar
            </Link>
          </DropdownMenuItem>

          {fsmActions.length > 0 ? (
            <>
              <DropdownMenuSeparator />
              {fsmActions.map((action) => (
                <DropdownMenuItem
                  key={action.name}
                  onSelect={() => {
                    if (isDestructiveEntityAction(action.name)) {
                      setConfirm({ kind: "fsm", node, action });
                    } else {
                      runFsm(action);
                    }
                  }}
                >
                  {action.label}
                </DropdownMenuItem>
              ))}
            </>
          ) : null}

          <DropdownMenuSeparator />
          <DropdownMenuItem
            className="text-destructive focus:text-destructive"
            onSelect={() => setConfirm({ kind: "delete", node })}
          >
            <Trash2 className="mr-2 h-4 w-4" aria-hidden="true" />
            Eliminar
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      {confirm?.kind === "delete" ? (
        <ConfirmDialog
          open
          onOpenChange={(open) => {
            if (!open) setConfirm(null);
          }}
          title="¿Eliminar institución?"
          description="Esta acción no se puede deshacer."
          confirmLabel="Eliminar"
          cancelLabel="Cancelar"
          destructive
          onConfirm={runDelete}
        />
      ) : null}

      {confirm?.kind === "fsm" ? (
        <ConfirmDialog
          open
          onOpenChange={(open) => {
            if (!open) setConfirm(null);
          }}
          title={`¿Confirmar "${confirm.action.label}"?`}
          description="Esta acción no se puede deshacer."
          confirmLabel={confirm.action.label}
          cancelLabel="Cancelar"
          destructive
          onConfirm={() => runFsm(confirm.action)}
        />
      ) : null}
    </>
  );
}
