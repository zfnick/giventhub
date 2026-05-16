"use client";

import { useMemo, useState, useCallback } from 'react';
import { ReactFlow, Controls, Background, Node, Edge, useNodesState, useEdgesState, Handle, Position } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { User, Building2, Terminal, Users2 } from "lucide-react";

// Custom Nodes
function RootNode({ data }: { data: any }) {
  return (
    <div className="bg-zinc-100 border-[3px] border-zinc-300 rounded-full w-32 h-32 flex items-center justify-center shadow-xl hover:bg-zinc-200 transition-colors">
      <div className="font-bold text-center text-sm text-zinc-800 px-2">{data.label}</div>
      <Handle type="source" position={Position.Bottom} className="opacity-0" />
      <Handle type="target" position={Position.Top} className="opacity-0" />
    </div>
  );
}

function CategoryNode({ data }: { data: any }) {
  return (
    <div className={`${data.color} rounded-full w-24 h-24 flex items-center justify-center shadow-lg transition-transform hover:scale-105 border-2 cursor-pointer`}>
      <div className="font-semibold text-center text-xs px-2">{data.label}</div>
      <Handle type="source" position={Position.Bottom} className="opacity-0" />
      <Handle type="target" position={Position.Top} className="opacity-0" />
    </div>
  );
}

function ItemNode({ data }: { data: any }) {
  return (
    <div className={`${data.itemColor} rounded-full w-16 h-16 flex items-center justify-center shadow-md transition-transform hover:scale-110 border border-opacity-50 cursor-pointer`}>
      <div className="text-center text-[10px] font-medium leading-tight px-1 break-words line-clamp-2">{data.label}</div>
      <Handle type="source" position={Position.Bottom} className="opacity-0" />
      <Handle type="target" position={Position.Top} className="opacity-0" />
    </div>
  );
}

const nodeTypes = {
  rootNode: RootNode,
  categoryNode: CategoryNode,
  itemNode: ItemNode,
};

// Mock detailed data
const CATEGORIES_DATA = {
  participants: [
    { name: 'Alice W.', role: 'Frontend Eng', company: 'Startup X', email: 'alice@example.com' },
    { name: 'Bob M.', role: 'Backend Eng', company: 'Tech Corp', email: 'bob@example.com' },
    { name: 'Charlie D.', role: 'Designer', company: 'Studio Y', email: 'charlie@example.com' },
    { name: 'David K.', role: 'Fullstack Eng', company: 'Freelance', email: 'david@example.com' },
    { name: 'Emma S.', role: 'Data Scientist', company: 'Analytics Co', email: 'emma@example.com' },
    { name: 'Frank T.', role: 'Product Manager', company: 'Startup Z', email: 'frank@example.com' },
    { name: 'Grace L.', role: 'Mobile Dev', company: 'App Co', email: 'grace@example.com' },
    { name: 'Henry P.', role: 'DevOps', company: 'Cloud Inc', email: 'henry@example.com' },
    { name: 'Ivy C.', role: 'UX Researcher', company: 'Design Agency', email: 'ivy@example.com' },
    { name: 'Jack R.', role: 'AI Engineer', company: 'Research Lab', email: 'jack@example.com' },
    { name: 'Kevin B.', role: 'Security Eng', company: 'CyberSec', email: 'kevin@example.com' },
    { name: 'Liam N.', role: 'Frontend Eng', company: 'Web Devs', email: 'liam@example.com' },
    { name: 'Mia V.', role: 'Backend Eng', company: 'Data Systems', email: 'mia@example.com' },
    { name: 'Noah H.', role: 'System Architect', company: 'Enterprise Inc', email: 'noah@example.com' },
  ],
  sponsors: [
    { name: 'Google Cloud', role: 'Platinum Sponsor', company: 'Credits & APIs', email: 'cloud@google.com' },
    { name: 'Stripe', role: 'Gold Sponsor', company: 'Payments', email: 'events@stripe.com' },
    { name: 'Vercel', role: 'Silver Sponsor', company: 'Hosting', email: 'sponsors@vercel.com' },
    { name: 'Supabase', role: 'Bronze Sponsor', company: 'Database', email: 'hello@supabase.io' },
    { name: 'OpenAI', role: 'API Partner', company: 'AI Models', email: 'partners@openai.com' },
    { name: 'Anthropic', role: 'API Partner', company: 'AI Models', email: 'partners@anthropic.com' },
    { name: 'GitHub', role: 'Community Partner', company: 'Version Control', email: 'events@github.com' },
  ],
  tech: [
    { name: 'Forms', role: 'Registration', company: 'Google Workspace', email: 'Collects emails' },
    { name: 'Sheets', role: 'Database', company: 'Google Workspace', email: 'Stores roster' },
    { name: 'Docs', role: 'Rules/Rubric', company: 'Google Workspace', email: 'Judging criteria' },
    { name: 'Meet', role: 'Video calls', company: 'Google Workspace', email: 'Virtual mentorship' },
    { name: 'Drive', role: 'Storage', company: 'Google Workspace', email: 'Submission assets' },
    { name: 'Calendar', role: 'Scheduling', company: 'Google Workspace', email: 'Event timeline' },
    { name: 'Gmail', role: 'Comms', company: 'Google Workspace', email: 'Broadcasts' },
    { name: 'Looker', role: 'Analytics', company: 'Google Cloud', email: 'Dashboard' },
  ],
  mentors: [
    { name: 'Sarah (UX)', role: 'Design Lead', company: 'Google', email: 'sarah@example.com' },
    { name: 'John (AI)', role: 'ML Researcher', company: 'DeepMind', email: 'john@example.com' },
    { name: 'Mike (VC)', role: 'Partner', company: 'Sequoia', email: 'mike@example.com' },
    { name: 'Lisa (Eng)', role: 'Staff Engineer', company: 'Stripe', email: 'lisa@example.com' },
    { name: 'David (PM)', role: 'Product Lead', company: 'Vercel', email: 'david@example.com' },
    { name: 'Eva (Data)', role: 'Data Scientist', company: 'OpenAI', email: 'eva@example.com' },
    { name: 'Tom (Sec)', role: 'Security Researcher', company: 'GitHub', email: 'tom@example.com' },
  ]
};

// Helper to generate the radial graph data
function generateGraphData() {
  const nodes: Node[] = [];
  const edges: Edge[] = [];

  const centerX = 500;
  const centerY = 400;
  const catRadius = 250;
  const itemRadius = 180;

  // Root Node
  nodes.push({
    id: 'root',
    type: 'rootNode',
    position: { x: centerX - 64, y: centerY - 64 }, 
    data: { label: 'Hackathon Ecosystem' },
  });

  const categories = [
    { 
      id: 'cat-participants', 
      label: 'Participants', 
      color: 'bg-blue-100 border-blue-400 text-blue-900', 
      itemColor: 'bg-blue-50 border-blue-300 text-blue-800 hover:border-blue-500 hover:bg-blue-100',
      items: CATEGORIES_DATA.participants, 
      angle: -Math.PI / 4 // Top Right
    },
    { 
      id: 'cat-sponsors', 
      label: 'Sponsors', 
      color: 'bg-emerald-100 border-emerald-400 text-emerald-900', 
      itemColor: 'bg-emerald-50 border-emerald-300 text-emerald-800 hover:border-emerald-500 hover:bg-emerald-100',
      items: CATEGORIES_DATA.sponsors, 
      angle: Math.PI / 4 // Bottom Right
    },
    { 
      id: 'cat-tech', 
      label: 'Tech Stack', 
      color: 'bg-amber-100 border-amber-400 text-amber-900', 
      itemColor: 'bg-amber-50 border-amber-300 text-amber-800 hover:border-amber-500 hover:bg-amber-100',
      items: CATEGORIES_DATA.tech, 
      angle: 3 * Math.PI / 4 // Bottom Left
    },
    { 
      id: 'cat-mentors', 
      label: 'Mentors', 
      color: 'bg-fuchsia-100 border-fuchsia-400 text-fuchsia-900', 
      itemColor: 'bg-fuchsia-50 border-fuchsia-300 text-fuchsia-800 hover:border-fuchsia-500 hover:bg-fuchsia-100',
      items: CATEGORIES_DATA.mentors, 
      angle: -3 * Math.PI / 4 // Top Left
    },
  ];

  categories.forEach((cat) => {
    const catX = centerX + catRadius * Math.cos(cat.angle);
    const catY = centerY + catRadius * Math.sin(cat.angle);

    // Add category node
    nodes.push({
      id: cat.id,
      type: 'categoryNode',
      position: { x: catX - 48, y: catY - 48 },
      data: { label: cat.label, type: 'category', catId: cat.id.replace('cat-', ''), color: cat.color },
    });

    // Add edge from root to category
    edges.push({
      id: `e-root-${cat.id}`,
      source: 'root',
      target: cat.id,
      animated: true,
      style: { stroke: '#a1a1aa', strokeWidth: 2 },
    });

    // Generate items forming a semi-circle pointing outwards
    const startAngle = cat.angle - Math.PI / 2;
    const endAngle = cat.angle + Math.PI / 2;
    const angleStep = (endAngle - startAngle) / (cat.items.length - 1 || 1);

    cat.items.forEach((item, i) => {
      const itemAngle = startAngle + angleStep * i;
      const itemX = catX + itemRadius * Math.cos(itemAngle);
      const itemY = catY + itemRadius * Math.sin(itemAngle);
      const itemId = `${cat.id}-item-${i}`;

      nodes.push({
        id: itemId,
        type: 'itemNode',
        position: { x: itemX - 32, y: itemY - 32 },
        data: { label: item.name, type: 'item', itemData: item, catId: cat.id.replace('cat-', ''), itemColor: cat.itemColor },
      });

      edges.push({
        id: `e-${cat.id}-${itemId}`,
        source: cat.id,
        target: itemId,
        style: { stroke: '#cbd5e1', strokeWidth: 1 },
      });
      
      if (Math.random() > 0.85) {
        const randomCat = categories[Math.floor(Math.random() * categories.length)];
        if (randomCat.id !== cat.id) {
          edges.push({
            id: `e-cross-${itemId}-${randomCat.id}`,
            source: itemId,
            target: randomCat.id,
            animated: true,
            style: { stroke: '#e2e8f0', strokeWidth: 1, opacity: 0.5 },
          });
        }
      }
    });
  });

  return { initialNodes: nodes, initialEdges: edges };
}

export function PlaybookFlow() {
  const { initialNodes, initialEdges } = useMemo(() => generateGraphData(), []);
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  
  const [selectedEntity, setSelectedEntity] = useState<any | null>(null);
  const [isSheetOpen, setIsSheetOpen] = useState(false);

  const onNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    if (node.id === 'root') return;
    
    const type = node.data.type;
    const catId = node.data.catId as string;
    
    if (type === 'category') {
      setSelectedEntity({
        type: 'category',
        title: node.data.label,
        catId: catId,
        list: CATEGORIES_DATA[catId as keyof typeof CATEGORIES_DATA]
      });
      setIsSheetOpen(true);
    } else if (type === 'item') {
      setSelectedEntity({
        type: 'item',
        title: node.data.label,
        itemData: node.data.itemData,
        catId: catId
      });
      setIsSheetOpen(true);
    }
  }, []);

  return (
    <>
      <div style={{ width: '100%', height: '700px' }} className="border rounded-lg bg-white dark:bg-zinc-950/50">
        <ReactFlow 
          nodes={nodes} 
          edges={edges} 
          nodeTypes={nodeTypes}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          fitView 
          fitViewOptions={{ padding: 0.1 }}
          attributionPosition="bottom-right" 
          minZoom={0.1}
          nodesConnectable={false}
          nodesDraggable={true}
          elementsSelectable={true}
        >
          <Controls />
          <Background gap={24} size={1} color="#f4f4f5" />
        </ReactFlow>
      </div>

      <Sheet open={isSheetOpen} onOpenChange={setIsSheetOpen}>
        <SheetContent className="w-[400px] sm:w-[540px] overflow-y-auto">
          <SheetHeader className="mb-6">
            <SheetTitle className="text-2xl flex items-center gap-2">
              {selectedEntity?.type === 'category' && <Users2 className="h-6 w-6 text-zinc-500" />}
              {selectedEntity?.type === 'item' && <User className="h-6 w-6 text-zinc-500" />}
              {selectedEntity?.title}
            </SheetTitle>
            <SheetDescription>
              {selectedEntity?.type === 'category' 
                ? `Viewing all ${selectedEntity.list?.length} items in this group.`
                : `Detailed view for this specific entity.`}
            </SheetDescription>
          </SheetHeader>

          {/* Render Individual Item Detail */}
          {selectedEntity?.type === 'item' && selectedEntity.itemData && (
            <div className="space-y-6">
              <div className="flex items-center gap-4 p-4 border rounded-lg bg-zinc-50 dark:bg-zinc-900/50">
                <Avatar className="h-16 w-16">
                  <AvatarFallback className="bg-indigo-100 text-indigo-700 font-bold text-xl">
                    {selectedEntity.itemData.name.charAt(0)}
                  </AvatarFallback>
                </Avatar>
                <div>
                  <h3 className="font-semibold text-lg">{selectedEntity.itemData.name}</h3>
                  <p className="text-sm text-zinc-500">{selectedEntity.itemData.role}</p>
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 border-b border-zinc-100 dark:border-zinc-800">
                  <span className="text-sm font-medium text-zinc-500 flex items-center gap-2">
                    <Building2 className="h-4 w-4" /> Organization
                  </span>
                  <span className="text-sm">{selectedEntity.itemData.company}</span>
                </div>
                <div className="flex items-center justify-between p-3 border-b border-zinc-100 dark:border-zinc-800">
                  <span className="text-sm font-medium text-zinc-500 flex items-center gap-2">
                    <Terminal className="h-4 w-4" /> Description/Contact
                  </span>
                  <span className="text-sm">{selectedEntity.itemData.email}</span>
                </div>
              </div>
            </div>
          )}

          {/* Render Category List */}
          {selectedEntity?.type === 'category' && selectedEntity.list && (
            <div className="space-y-4">
              {selectedEntity.list.map((item: any, idx: number) => (
                <div key={idx} className="flex items-center gap-4 p-3 rounded-lg border bg-white hover:bg-zinc-50 dark:bg-zinc-950 dark:hover:bg-zinc-900 transition-colors">
                  <Avatar className="h-10 w-10">
                    <AvatarFallback className={`text-sm font-semibold 
                      ${selectedEntity.catId === 'participants' ? 'bg-blue-100 text-blue-700' : ''}
                      ${selectedEntity.catId === 'sponsors' ? 'bg-emerald-100 text-emerald-700' : ''}
                      ${selectedEntity.catId === 'tech' ? 'bg-amber-100 text-amber-700' : ''}
                      ${selectedEntity.catId === 'mentors' ? 'bg-fuchsia-100 text-fuchsia-700' : ''}
                    `}>
                      {item.name.charAt(0)}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1 min-w-0">
                    <h4 className="text-sm font-semibold truncate">{item.name}</h4>
                    <p className="text-xs text-zinc-500 truncate">{item.role} @ {item.company}</p>
                  </div>
                  <Badge variant="secondary" className="text-[10px] whitespace-nowrap">
                    {selectedEntity.catId === 'tech' ? 'Tool' : 'Active'}
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

