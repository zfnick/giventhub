"use client";

import { memo, useEffect, useMemo, useState, useCallback } from "react";
import {
  ReactFlow,
  Controls,
  Background,
  Node,
  Edge,
  EdgeProps,
  InternalNode,
  useNodesState,
  useEdgesState,
  useInternalNode,
  getBezierPath,
  Handle,
  Position,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { User, Building2, Terminal, Users2, Network } from "lucide-react";

// ── Data types ──────────────────────────────────────────────────────────────

export type GraphKind = "people" | "tool" | "sponsor" | "asset" | "theme";

export interface GraphItem {
  name: string;
  role: string;
  detail: string;
}

export interface GraphCategory {
  id: string;
  label: string;
  kind: GraphKind;
  items: GraphItem[];
}

export interface PlaybookGraphData {
  root_label: string;
  categories: GraphCategory[];
}

// ── Custom node renderers ───────────────────────────────────────────────────

interface RootNodeData {
  label: string;
}

interface CategoryNodeData {
  label: string;
  type: "category";
  catId: string;
  color: string;
  count: number;
}

interface ItemNodeData {
  label: string;
  type: "item";
  itemData: GraphItem;
  catId: string;
  itemColor: string;
}

const RootNode = memo(function RootNode({ data }: { data: RootNodeData }) {
  return (
    <div className="bg-zinc-100 border-[3px] border-zinc-300 rounded-full w-32 h-32 flex items-center justify-center shadow-xl hover:bg-zinc-200 transition-colors">
      <div className="font-bold text-center text-sm text-zinc-800 px-2">{data.label}</div>
      <Handle type="source" position={Position.Bottom} className="opacity-0" />
      <Handle type="target" position={Position.Top} className="opacity-0" />
    </div>
  );
});

const CategoryNode = memo(function CategoryNode({ data }: { data: CategoryNodeData }) {
  return (
    <div
      className={`${data.color} rounded-full w-24 h-24 flex items-center justify-center shadow-lg transition-transform hover:scale-105 border-2 cursor-pointer`}
    >
      <div className="text-center px-2">
        <div className="font-semibold text-xs leading-tight">{data.label}</div>
        <div className="mt-1 text-[10px] font-medium opacity-70">
          {data.count} {data.count === 1 ? "item" : "items"}
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} className="opacity-0" />
      <Handle type="target" position={Position.Top} className="opacity-0" />
    </div>
  );
});

const ItemNode = memo(function ItemNode({ data }: { data: ItemNodeData }) {
  return (
    <div
      className={`${data.itemColor} rounded-full w-16 h-16 flex items-center justify-center shadow-md transition-transform hover:scale-110 border border-opacity-50 cursor-pointer`}
    >
      <div className="text-center text-[10px] font-medium leading-tight px-1 break-words line-clamp-2">
        {data.label}
      </div>
      <Handle type="source" position={Position.Bottom} className="opacity-0" />
      <Handle type="target" position={Position.Top} className="opacity-0" />
    </div>
  );
});

const nodeTypes = {
  rootNode: RootNode,
  categoryNode: CategoryNode,
  itemNode: ItemNode,
};

// ── Floating edges ──────────────────────────────────────────────────────────
// Nodes are circles, so edges should leave/enter on the border point that
// faces the other node — not always from the bottom.

function nodeCenter(node: InternalNode) {
  const w = node.measured?.width ?? 0;
  const h = node.measured?.height ?? 0;
  return {
    cx: node.internals.positionAbsolute.x + w / 2,
    cy: node.internals.positionAbsolute.y + h / 2,
    r: Math.min(w, h) / 2,
  };
}

function sideOf(ux: number, uy: number): Position {
  if (Math.abs(ux) >= Math.abs(uy)) {
    return ux > 0 ? Position.Right : Position.Left;
  }
  return uy > 0 ? Position.Bottom : Position.Top;
}

function getFloatingEdgeParams(source: InternalNode, target: InternalNode) {
  const s = nodeCenter(source);
  const t = nodeCenter(target);
  const dx = t.cx - s.cx;
  const dy = t.cy - s.cy;
  const dist = Math.hypot(dx, dy) || 1;
  const ux = dx / dist;
  const uy = dy / dist;
  return {
    sx: s.cx + ux * s.r,
    sy: s.cy + uy * s.r,
    tx: t.cx - ux * t.r,
    ty: t.cy - uy * t.r,
    sourcePos: sideOf(ux, uy),
    targetPos: sideOf(-ux, -uy),
  };
}

const FloatingEdge = memo(function FloatingEdge({
  source,
  target,
  markerEnd,
  style,
}: EdgeProps) {
  const sourceNode = useInternalNode(source);
  const targetNode = useInternalNode(target);
  if (!sourceNode || !targetNode) return null;

  const { sx, sy, tx, ty, sourcePos, targetPos } = getFloatingEdgeParams(
    sourceNode,
    targetNode,
  );
  const [path] = getBezierPath({
    sourceX: sx,
    sourceY: sy,
    sourcePosition: sourcePos,
    targetX: tx,
    targetY: ty,
    targetPosition: targetPos,
    curvature: 0.35,
  });

  return (
    <path
      className="react-flow__edge-path"
      d={path}
      markerEnd={markerEnd}
      style={style}
      fill="none"
    />
  );
});

const edgeTypes = {
  floating: FloatingEdge,
};

// ── Color palette by kind ───────────────────────────────────────────────────

const KIND_COLORS: Record<
  GraphKind,
  {
    catBg: string;
    itemBg: string;
    avatarBg: string;
    badgeLabel: string;
  }
> = {
  people: {
    catBg: "bg-blue-100 border-blue-400 text-blue-900",
    itemBg:
      "bg-blue-50 border-blue-300 text-blue-800 hover:border-blue-500 hover:bg-blue-100",
    avatarBg: "bg-blue-100 text-blue-700",
    badgeLabel: "Person",
  },
  sponsor: {
    catBg: "bg-emerald-100 border-emerald-400 text-emerald-900",
    itemBg:
      "bg-emerald-50 border-emerald-300 text-emerald-800 hover:border-emerald-500 hover:bg-emerald-100",
    avatarBg: "bg-emerald-100 text-emerald-700",
    badgeLabel: "Sponsor",
  },
  tool: {
    catBg: "bg-amber-100 border-amber-400 text-amber-900",
    itemBg:
      "bg-amber-50 border-amber-300 text-amber-800 hover:border-amber-500 hover:bg-amber-100",
    avatarBg: "bg-amber-100 text-amber-700",
    badgeLabel: "Tool",
  },
  asset: {
    catBg: "bg-fuchsia-100 border-fuchsia-400 text-fuchsia-900",
    itemBg:
      "bg-fuchsia-50 border-fuchsia-300 text-fuchsia-800 hover:border-fuchsia-500 hover:bg-fuchsia-100",
    avatarBg: "bg-fuchsia-100 text-fuchsia-700",
    badgeLabel: "Asset",
  },
  theme: {
    catBg: "bg-violet-100 border-violet-400 text-violet-900",
    itemBg:
      "bg-violet-50 border-violet-300 text-violet-800 hover:border-violet-500 hover:bg-violet-100",
    avatarBg: "bg-violet-100 text-violet-700",
    badgeLabel: "Theme",
  },
};

// ── Layout generator ────────────────────────────────────────────────────────

const MAX_VISIBLE_ITEMS_PER_CATEGORY = 12;

function buildLayout(graph: PlaybookGraphData): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = [];
  const edges: Edge[] = [];

  const centerX = 500;
  const centerY = 400;
  const catRadius = 250;
  const itemRadius = 180;

  nodes.push({
    id: "root",
    type: "rootNode",
    position: { x: centerX - 64, y: centerY - 64 },
    data: { label: graph.root_label || "Event" },
  });

  const n = graph.categories.length;
  if (n === 0) return { nodes, edges };

  // Distribute categories evenly around the root
  graph.categories.forEach((cat, idx) => {
    const angle = (2 * Math.PI * idx) / n - Math.PI / 2; // start at top
    const catX = centerX + catRadius * Math.cos(angle);
    const catY = centerY + catRadius * Math.sin(angle);

    const palette = KIND_COLORS[cat.kind] ?? KIND_COLORS.theme;

    nodes.push({
      id: cat.id,
      type: "categoryNode",
      position: { x: catX - 48, y: catY - 48 },
      data: {
        label: cat.label,
        type: "category",
        catId: cat.id,
        color: palette.catBg,
        count: cat.items.length,
      } satisfies CategoryNodeData,
    });

    edges.push({
      id: `e-root-${cat.id}`,
      type: "floating",
      source: "root",
      target: cat.id,
      style: { stroke: "#a1a1aa", strokeWidth: 2 },
    });

    // Spread items in an arc that points outward from the center
    const visibleItems = cat.items.slice(0, MAX_VISIBLE_ITEMS_PER_CATEGORY);
    const itemCount = visibleItems.length;
    if (itemCount === 0) return;
    const halfSpan = Math.PI / 2;
    const startAngle = angle - halfSpan;
    const step = itemCount === 1 ? 0 : (halfSpan * 2) / (itemCount - 1);

    visibleItems.forEach((item, i) => {
      const itemAngle = startAngle + step * i;
      const itemX = catX + itemRadius * Math.cos(itemAngle);
      const itemY = catY + itemRadius * Math.sin(itemAngle);
      const itemId = `${cat.id}-item-${i}`;

      nodes.push({
        id: itemId,
        type: "itemNode",
        position: { x: itemX - 32, y: itemY - 32 },
        data: {
          label: item.name,
          type: "item",
          itemData: item,
          catId: cat.id,
          itemColor: palette.itemBg,
        } satisfies ItemNodeData,
      });

      edges.push({
        id: `e-${cat.id}-${itemId}`,
        type: "floating",
        source: cat.id,
        target: itemId,
        style: { stroke: "#cbd5e1", strokeWidth: 1.5 },
      });
    });
  });

  return { nodes, edges };
}

// ── Component ───────────────────────────────────────────────────────────────

type SelectedEntity =
  | { kind: "category"; category: GraphCategory }
  | { kind: "item"; item: GraphItem; category: GraphCategory }
  | null;

export interface PlaybookFlowProps {
  graph?: PlaybookGraphData | null;
  loading?: boolean;
}

export function PlaybookFlow({ graph, loading }: PlaybookFlowProps) {
  const layout = useMemo(
    () =>
      graph ? buildLayout(graph) : { nodes: [] as Node[], edges: [] as Edge[] },
    [graph],
  );

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>(layout.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>(layout.edges);

  useEffect(() => {
    setNodes(layout.nodes);
    setEdges(layout.edges);
  }, [layout, setNodes, setEdges]);

  const [selected, setSelected] = useState<SelectedEntity>(null);
  const [sheetOpen, setSheetOpen] = useState(false);

  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      if (node.id === "root" || !graph) return;
      const data = node.data as unknown as CategoryNodeData | ItemNodeData;
      const cat = graph.categories.find((c) => c.id === data.catId);
      if (!cat) return;
      if (data.type === "category") {
        setSelected({ kind: "category", category: cat });
      } else {
        setSelected({ kind: "item", item: data.itemData, category: cat });
      }
      setSheetOpen(true);
    },
    [graph],
  );

  if (loading) {
    return (
      <div
        style={{ width: "100%", height: "700px" }}
        className="border rounded-lg bg-white dark:bg-zinc-950/50 flex items-center justify-center"
      >
        <div className="flex flex-col items-center gap-3 text-zinc-400">
          <div className="h-8 w-8 rounded-full border-2 border-zinc-300 border-t-zinc-900 animate-spin" />
          <p className="text-sm font-medium">Generating knowledge tree…</p>
        </div>
      </div>
    );
  }

  if (!graph || graph.categories.length === 0) {
    return (
      <div
        style={{ width: "100%", height: "700px" }}
        className="border rounded-lg bg-white dark:bg-zinc-950/50 flex items-center justify-center"
      >
        <div className="flex flex-col items-center gap-3 text-zinc-400 text-center max-w-sm px-6">
          <div className="h-14 w-14 rounded-2xl bg-zinc-100 flex items-center justify-center">
            <Network className="h-7 w-7 text-zinc-300" />
          </div>
          <p className="text-sm font-medium text-zinc-500">
            No knowledge tree yet
          </p>
          <p className="text-xs text-zinc-400">
            Add a description, audience, or assets and the AI will draft a contextual graph.
          </p>
        </div>
      </div>
    );
  }

  const selectedPalette =
    selected?.category && (KIND_COLORS[selected.category.kind] ?? KIND_COLORS.theme);

  return (
    <>
      <div
        style={{ width: "100%", height: "100%" }}
        className="relative border rounded-lg bg-white dark:bg-zinc-950/50 overflow-hidden"
      >
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          onNodeClick={onNodeClick}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          minZoom={0.2}
          maxZoom={1.5}
          nodesDraggable={true}
          nodesConnectable={false}
          elementsSelectable={true}
        >
          <Controls />
          <Background gap={24} size={1} color="#f4f4f5" />
        </ReactFlow>
      </div>

      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent className="w-[400px] sm:w-[540px] overflow-y-auto">
          <SheetHeader className="mb-6">
            <SheetTitle className="text-2xl flex items-center gap-2">
              {selected?.kind === "category" && (
                <Users2 className="h-6 w-6 text-zinc-500" />
              )}
              {selected?.kind === "item" && (
                <User className="h-6 w-6 text-zinc-500" />
              )}
              {selected?.kind === "category" && selected.category.label}
              {selected?.kind === "item" && selected.item.name}
            </SheetTitle>
            <SheetDescription>
              {selected?.kind === "category" &&
                `Viewing all ${selected.category.items.length} items in this group.`}
              {selected?.kind === "item" && "Detailed view for this entity."}
            </SheetDescription>
          </SheetHeader>

          {selected?.kind === "item" && (
            <div className="space-y-6">
              <div className="flex items-center gap-4 p-4 border rounded-lg bg-zinc-50 dark:bg-zinc-900/50">
                <Avatar className="h-16 w-16">
                  <AvatarFallback
                    className={`${selectedPalette?.avatarBg ?? "bg-zinc-100 text-zinc-700"} font-bold text-xl`}
                  >
                    {selected.item.name.charAt(0).toUpperCase()}
                  </AvatarFallback>
                </Avatar>
                <div>
                  <h3 className="font-semibold text-lg">{selected.item.name}</h3>
                  {selected.item.role && (
                    <p className="text-sm text-zinc-500">{selected.item.role}</p>
                  )}
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex items-start justify-between gap-4 p-3 border-b border-zinc-100 dark:border-zinc-800">
                  <span className="text-sm font-medium text-zinc-500 flex items-center gap-2 shrink-0">
                    <Building2 className="h-4 w-4" /> Category
                  </span>
                  <span className="text-sm text-right">{selected.category.label}</span>
                </div>
                {selected.item.detail && (
                  <div className="flex items-start justify-between gap-4 p-3 border-b border-zinc-100 dark:border-zinc-800">
                    <span className="text-sm font-medium text-zinc-500 flex items-center gap-2 shrink-0">
                      <Terminal className="h-4 w-4" /> Detail
                    </span>
                    <span className="text-sm text-right">{selected.item.detail}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {selected?.kind === "category" && (
            <div className="space-y-4">
              {selected.category.items.map((item, idx) => (
                <div
                  key={idx}
                  className="flex items-center gap-4 p-3 rounded-lg border bg-white hover:bg-zinc-50 dark:bg-zinc-950 dark:hover:bg-zinc-900 transition-colors"
                >
                  <Avatar className="h-10 w-10">
                    <AvatarFallback
                      className={`${selectedPalette?.avatarBg ?? "bg-zinc-100 text-zinc-700"} text-sm font-semibold`}
                    >
                      {item.name.charAt(0).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1 min-w-0">
                    <h4 className="text-sm font-semibold leading-snug">{item.name}</h4>
                    {item.role && (
                      <p className="text-xs text-zinc-500 leading-snug">{item.role}</p>
                    )}
                    {item.detail && (
                      <p className="text-xs text-zinc-400 leading-snug mt-1">
                        {item.detail}
                      </p>
                    )}
                  </div>
                  <Badge variant="secondary" className="text-[10px] whitespace-nowrap shrink-0">
                    {selectedPalette?.badgeLabel ?? "Item"}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </SheetContent>
      </Sheet>
    </>
  );
}
