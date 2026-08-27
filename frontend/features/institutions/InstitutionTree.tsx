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
 * PR2 (RF-F03): expanding an institution lazily fetches its sedes,
 * facultades and centers (useQuery gated by `enabled: isExpanded`) and
 * renders them as children. Each child node carries per-kind actions
 * (detail/edit links, FSM transitions, delete) with the admin write
 * threshold (RF-F05).
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
import { useFacultades, useResearchCenters, useSedes } from "@/features/institutions/queries";
import {
  useDeleteCenter,
  useDeleteFacultad,
  useDeleteInstitution,
  useDeleteSede,
  useCenterTransition,
  useFacultadTransition,
  useInstitutionTransition,
  useSedeTransition,
} from "@/features/institutions/mutations";
import {
  getEntityActions,
  isDestructiveEntityAction,
  type FsmAction,
} from "@/features/institutions/fsm";
import type { EntityKind, InstitutionTreeNode } from "@/features/institutions/types";

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

/** Per-kind UI metadata: label, write-role threshold (RF-F05). */
const KIND_META: Record<EntityKind, { label: string; deletedLabel: string; minRoles: string[] }> = {
  institution: { label: "Institución", deletedLabel: "Institución eliminada.", minRoles: ["superadmin"] },
  sede: { label: "Sede", deletedLabel: "Sede eliminada.", minRoles: ["admin", "superadmin"] },
  facultad: { label: "Facultad", deletedLabel: "Facultad eliminada.", minRoles: ["admin", "superadmin"] },
  center: {
    label: "Centro de investigación",
    deletedLabel: "Centro de investigación eliminado.",
    minRoles: ["admin", "superadmin"],
  },
  // PR3: groups/lines are directed by directors.
  group: { label: "Grupo", deletedLabel: "Grupo eliminado.", minRoles: ["director", "admin", "superadmin"] },
  line: { label: "Línea", deletedLabel: "Línea eliminada.", minRoles: ["director", "admin", "superadmin"] },
};

/** Detail route of a node, derived from its kind and the root institution id. */
function detailUrl(kind: EntityKind, nodeId: string, institutionId: string): string {
  switch (kind) {
    case "sede":
      return `/institutions/${institutionId}/sedes/${nodeId}`;
    case "facultad":
      return `/institutions/${institutionId}/facultades/${nodeId}`;
    case "center":
      return `/institutions/${institutionId}/centers/${nodeId}`;
    default:
      return `/institutions/${nodeId}`;
  }
}

export function InstitutionTree({ nodes }: InstitutionTreeProps) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [focusedId, setFocusedId] = useState<string | null>(null);
  const [lazyChildren, setLazyChildren] = useState<Record<string, InstitutionTreeNode[]>>({});
  const nodeRefs = useRef<Map<string, HTMLElement>>(new Map());

  /** Lift lazily fetched children up so keyboard nav sees them. */
  const handleLazyChildren = useCallback(
    (parentId: string, children: InstitutionTreeNode[]) => {
      setLazyChildren((prev) => {
        const current = prev[parentId];
        if (
          current &&
          current.length === children.length &&
          current.every((c, i) => c.id === children[i]?.id)
        ) {
          return prev;
        }
        return { ...prev, [parentId]: children };
      });
    },
    [],
  );

  /** Merge lazy children under institution nodes; static children stay. */
  const mergedNodes = useMemo(
    () =>
      nodes.map((node) =>
        node.kind === "institution"
          ? { ...node, children: [...node.children, ...(lazyChildren[node.id] ?? [])] }
          : node,
      ),
    [nodes, lazyChildren],
  );

  const visible = flattenVisibleNodes(mergedNodes, expandedIds);
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
          const parentId = findParentId(mergedNodes, node.id);
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

  if (mergedNodes.length === 0) return null;

  return (
    <ul
      role="tree"
      aria-label="Estructura institucional"
      onKeyDown={handleKeyDown}
      className="space-y-1"
    >
      {mergedNodes.map((node, index) => (
        <TreeNode
          key={node.id}
          node={node}
          depth={0}
          institutionId={node.id}
          tabIndex={focusedId === null ? (index === 0 ? 0 : -1) : focusedId === node.id ? 0 : -1}
          expandedIds={expandedIds}
          focusedId={focusedId}
          onToggle={toggle}
          onFocus={setFocusedId}
          registerRef={registerRef}
          onLazyChildren={handleLazyChildren}
        />
      ))}
    </ul>
  );
}

interface TreeNodeProps {
  node: InstitutionTreeNode;
  depth: number;
  /** Root institution id — used to build child detail/edit URLs. */
  institutionId: string;
  /** Roving-focus tabIndex: 0 for the active node, -1 otherwise. */
  tabIndex: number;
  expandedIds: Set<string>;
  focusedId: string | null;
  onToggle: (id: string) => void;
  onFocus: (id: string) => void;
  registerRef: (id: string, el: HTMLElement | null) => void;
  onLazyChildren: (parentId: string, children: InstitutionTreeNode[]) => void;
}

function TreeNode({
  node,
  depth,
  institutionId,
  tabIndex,
  expandedIds,
  focusedId,
  onToggle,
  onFocus,
  registerRef,
  onLazyChildren,
}: TreeNodeProps) {
  const isExpanded = expandedIds.has(node.id);
  // Institution nodes can always have children (lazily loaded); other
  // kinds expand only when static children exist.
  const canExpand = node.kind === "institution" || node.children.length > 0;

  return (
    <li
      role="treeitem"
      aria-level={depth + 1}
      aria-expanded={canExpand ? isExpanded : undefined}
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
        {canExpand ? (
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
          href={detailUrl(node.kind, node.id, institutionId)}
          onClick={(e) => e.stopPropagation()}
          className="font-medium hover:underline"
        >
          {node.name}
        </Link>
        <span className="text-xs text-muted-foreground">{node.code}</span>
        <StatusBadge status={node.status} />
        <NodeActions node={node} institutionId={institutionId} />
      </div>

      {canExpand && isExpanded ? (
        <ul role="group">
          {node.kind === "institution" ? (
            <LazyChildrenLoader
              institutionId={node.id}
              expanded={isExpanded}
              onLoaded={onLazyChildren}
            />
          ) : null}
          {node.children.map((child) => (
            <TreeNode
              key={child.id}
              node={child}
              depth={depth + 1}
              institutionId={institutionId}
              tabIndex={focusedId === child.id ? 0 : -1}
              expandedIds={expandedIds}
              focusedId={focusedId}
              onToggle={onToggle}
              onFocus={onFocus}
              registerRef={registerRef}
              onLazyChildren={onLazyChildren}
            />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

/**
 * Fetches the sedes/facultades/centers of an expanded institution and
 * reports them up to the tree root. Renders nothing; the root merges the
 * results into the node's children so keyboard nav sees them.
 */
function LazyChildrenLoader({
  institutionId,
  expanded,
  onLoaded,
}: {
  institutionId: string;
  expanded: boolean;
  onLoaded: (parentId: string, children: InstitutionTreeNode[]) => void;
}) {
  const sedesQuery = useSedes(institutionId, expanded);
  const facultadesQuery = useFacultades(institutionId, undefined, expanded);
  const centersQuery = useResearchCenters(institutionId, "institution", null, expanded);

  useEffect(() => {
    const children: InstitutionTreeNode[] = [
      ...(sedesQuery.data?.results ?? []).map((s) => ({
        id: s.id,
        kind: "sede" as const,
        name: s.name,
        code: s.code,
        status: s.status,
        is_active: s.is_active,
        children: [] as InstitutionTreeNode[],
      })),
      ...(facultadesQuery.data?.results ?? []).map((f) => ({
        id: f.id,
        kind: "facultad" as const,
        name: f.name,
        code: f.code,
        status: f.status,
        is_active: f.is_active,
        children: [] as InstitutionTreeNode[],
      })),
      ...(centersQuery.data?.results ?? []).map((c) => ({
        id: c.id,
        kind: "center" as const,
        name: c.name,
        code: c.code,
        status: c.status,
        is_active: c.is_active,
        children: [] as InstitutionTreeNode[],
      })),
    ];
    onLoaded(institutionId, children);
  }, [
    institutionId,
    expanded,
    sedesQuery.data,
    facultadesQuery.data,
    centersQuery.data,
    onLoaded,
  ]);

  return null;
}

/** Per-node action menu: detail/edit links, FSM transitions, delete. */
function NodeActions({
  node,
  institutionId,
}: {
  node: InstitutionTreeNode;
  institutionId: string;
}) {
  const roles = useAuthStore((s) => s.roles);
  // All four transition/delete hooks are registered unconditionally and
  // selected by kind — keeps hook order stable across renders.
  const institutionTransition = useInstitutionTransition();
  const sedeTransition = useSedeTransition();
  const facultadTransition = useFacultadTransition();
  const centerTransition = useCenterTransition();
  const deleteInstitution = useDeleteInstitution();
  const deleteSede = useDeleteSede();
  const deleteFacultad = useDeleteFacultad();
  const deleteCenter = useDeleteCenter();
  const [confirm, setConfirm] = useState<ConfirmState>(null);

  const meta = KIND_META[node.kind] ?? KIND_META.institution;
  const fsmActions = getEntityActions(node.status, roles, meta.minRoles);

  const transition =
    node.kind === "sede"
      ? sedeTransition
      : node.kind === "facultad"
        ? facultadTransition
        : node.kind === "center"
          ? centerTransition
          : institutionTransition;

  const remove =
    node.kind === "sede"
      ? deleteSede
      : node.kind === "facultad"
        ? deleteFacultad
        : node.kind === "center"
          ? deleteCenter
          : deleteInstitution;

  function runFsm(action: FsmAction) {
    transition.mutate(
      { id: node.id, action: action.name },
      {
        onSuccess: () => {
          toast.success(`${meta.label} ${action.label.toLowerCase()}.`);
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
        toast.success(meta.deletedLabel);
      },
      onError: (error) => {
        toast.error(getErrorMessage(error));
      },
    });
  }

  const nodeHref = detailUrl(node.kind, node.id, institutionId);

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
            <Link href={nodeHref}>
              <ExternalLink className="mr-2 h-4 w-4" aria-hidden="true" />
              Ver detalle
            </Link>
          </DropdownMenuItem>
          <DropdownMenuItem asChild>
            <Link href={`${nodeHref}/edit`}>
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
          title={`¿Eliminar ${meta.label.toLowerCase()}?`}
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