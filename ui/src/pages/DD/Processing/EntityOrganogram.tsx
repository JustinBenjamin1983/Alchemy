/**
 * Entity Organogram - Interactive corporate structure visualization
 *
 * Layout:
 * - Top level: Shareholders (current owners) + Client/Acquirer (future owner in dotted container)
 * - Center: Target entity (highlighted)
 * - Bottom: Subsidiaries
 * - Around edges: Counterparties, suppliers, customers, financiers
 * - Separate "Key Individuals" section
 *
 * Features:
 * - Interactive nodes (click for details)
 * - Conflict flags for user resolution
 * - Ownership percentages on edges
 * - Minimalist, professional design
 */
import React, { useCallback, useMemo, useState } from "react";
import {
  ReactFlow,
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  Position,
  MarkerType,
  Handle,
  NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { motion, AnimatePresence } from "framer-motion";
import {
  Building2,
  Building,
  Users,
  Briefcase,
  Landmark,
  Truck,
  ShoppingCart,
  AlertTriangle,
  FileText,
  X,
  ChevronRight,
  ChevronDown,
  Target,
  Link2,
  UserPlus,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

// Types
export interface OrganogramEntity {
  id: string;
  entity_name: string;
  registration_number?: string;
  relationship_to_target: string;
  relationship_detail?: string;
  ownership_percentage?: number;
  confidence: number;
  documents_appearing_in: string[];
  evidence?: string;
  requires_human_confirmation?: boolean;
  human_confirmed?: boolean;
  has_conflict?: boolean;
  conflict_details?: string;
  is_individual?: boolean;
}

export interface ShareholderInfo {
  name: string;
  ownership_percentage?: number;
}

export interface ClientEntityInfo {
  name: string;
  role?: string;
  deal_structure?: string;
}

export interface OrganogramData {
  target_entity: {
    name: string;
    registration_number?: string;
    transaction_type?: string;
    deal_structure?: string;
  };
  client_entity?: ClientEntityInfo;
  shareholders?: ShareholderInfo[];
  entities: OrganogramEntity[];
}

interface EntityOrganogramProps {
  data: OrganogramData;
  onEntityClick?: (entity: OrganogramEntity) => void;
  onResolveConflict?: (entityId: string) => void;
  className?: string;
}

// Relationship type to visual config mapping
const RELATIONSHIP_CONFIG: Record<string, {
  color: string;
  bgColor: string;
  borderColor: string;
  icon: React.ElementType;
  label: string;
}> = {
  parent: {
    color: "text-blue-700",
    bgColor: "bg-blue-50",
    borderColor: "border-blue-300",
    icon: Building2,
    label: "Parent",
  },
  holding_company: {
    color: "text-blue-700",
    bgColor: "bg-blue-50",
    borderColor: "border-blue-300",
    icon: Building2,
    label: "Holding",
  },
  target: {
    color: "text-orange-700",
    bgColor: "bg-orange-50",
    borderColor: "border-orange-400",
    icon: Target,
    label: "Target",
  },
  subsidiary: {
    color: "text-green-700",
    bgColor: "bg-green-50",
    borderColor: "border-green-300",
    icon: Building,
    label: "Subsidiary",
  },
  shareholder: {
    color: "text-purple-700",
    bgColor: "bg-purple-50",
    borderColor: "border-purple-300",
    icon: Users,
    label: "Shareholder",
  },
  client: {
    color: "text-indigo-700",
    bgColor: "bg-indigo-50",
    borderColor: "border-indigo-400",
    icon: UserPlus,
    label: "Acquirer",
  },
  counterparty: {
    color: "text-amber-700",
    bgColor: "bg-amber-50",
    borderColor: "border-amber-300",
    icon: Briefcase,
    label: "Counterparty",
  },
  financier: {
    color: "text-emerald-700",
    bgColor: "bg-emerald-50",
    borderColor: "border-emerald-300",
    icon: Landmark,
    label: "Financier",
  },
  lender: {
    color: "text-emerald-700",
    bgColor: "bg-emerald-50",
    borderColor: "border-emerald-300",
    icon: Landmark,
    label: "Lender",
  },
  supplier: {
    color: "text-cyan-700",
    bgColor: "bg-cyan-50",
    borderColor: "border-cyan-300",
    icon: Truck,
    label: "Supplier",
  },
  customer: {
    color: "text-pink-700",
    bgColor: "bg-pink-50",
    borderColor: "border-pink-300",
    icon: ShoppingCart,
    label: "Customer",
  },
  related_party: {
    color: "text-gray-700",
    bgColor: "bg-gray-50",
    borderColor: "border-gray-300",
    icon: Link2,
    label: "Related",
  },
  unknown: {
    color: "text-gray-500",
    bgColor: "bg-gray-50",
    borderColor: "border-gray-200",
    icon: Building,
    label: "Unknown",
  },
};

// Custom node component for entities
const EntityNode: React.FC<NodeProps> = ({ data }) => {
  const config = RELATIONSHIP_CONFIG[data.relationship] || RELATIONSHIP_CONFIG.unknown;
  const Icon = config.icon;
  const isTarget = data.relationship === "target";
  const isClient = data.relationship === "client";

  return (
    <div
      className={cn(
        "relative px-4 py-3 rounded-lg border-2 shadow-sm transition-all duration-200",
        "hover:shadow-md cursor-pointer min-w-[160px] max-w-[200px]",
        config.bgColor,
        config.borderColor,
        isTarget && "ring-2 ring-orange-400 ring-offset-2 min-w-[200px]",
        isClient && "border-dashed border-indigo-400 bg-indigo-50/50"
      )}
      onClick={data.onClick}
    >
      {/* Handles for connections */}
      <Handle type="target" position={Position.Top} className="!bg-gray-400 !w-2 !h-2" />
      <Handle type="source" position={Position.Bottom} className="!bg-gray-400 !w-2 !h-2" />
      <Handle type="target" position={Position.Left} id="left" className="!bg-gray-400 !w-2 !h-2" />
      <Handle type="source" position={Position.Right} id="right" className="!bg-gray-400 !w-2 !h-2" />

      {/* Conflict indicator */}
      {data.hasConflict && (
        <div className="absolute -top-2 -right-2 p-1 bg-amber-100 rounded-full border border-amber-400">
          <AlertTriangle className="w-3 h-3 text-amber-600" />
        </div>
      )}

      {/* Future owner badge for client */}
      {isClient && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-2 py-0.5 bg-indigo-100 border border-indigo-300 rounded text-[10px] font-medium text-indigo-700 whitespace-nowrap">
          Future Owner
        </div>
      )}

      {/* Header with icon and type */}
      <div className="flex items-center gap-2 mb-1">
        <Icon className={cn("w-4 h-4", config.color)} />
        <span className={cn("text-xs font-medium", config.color)}>
          {config.label}
        </span>
        {data.docsCount > 0 && (
          <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4 ml-auto">
            {data.docsCount} docs
          </Badge>
        )}
      </div>

      {/* Entity name */}
      <div className="font-semibold text-sm text-gray-900 leading-tight" title={data.label}>
        {data.label}
      </div>

      {/* Registration number */}
      {data.registrationNumber && (
        <div className="text-xs text-gray-500 truncate mt-0.5">
          {data.registrationNumber}
        </div>
      )}

      {/* Ownership percentage */}
      {data.ownershipPercentage && (
        <div className="mt-1.5 text-xs font-medium text-gray-600">
          {data.ownershipPercentage}% ownership
        </div>
      )}

      {/* Transaction type for client */}
      {data.dealStructure && (
        <div className="mt-1.5 px-2 py-1 bg-indigo-100 rounded text-xs text-indigo-700 font-medium">
          {data.dealStructure}
        </div>
      )}

      {/* Confidence indicator - only for non-target/non-shareholder/non-client */}
      {data.confidence !== undefined && data.confidence < 1 && (
        <div className="mt-2">
          <div className="flex items-center gap-1">
            <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={cn(
                  "h-full rounded-full",
                  data.confidence >= 0.8 ? "bg-green-500" :
                  data.confidence >= 0.5 ? "bg-amber-500" : "bg-red-500"
                )}
                style={{ width: `${data.confidence * 100}%` }}
              />
            </div>
            <span className="text-[10px] text-gray-500">{Math.round(data.confidence * 100)}%</span>
          </div>
          <div className="text-[9px] text-gray-400 mt-0.5">Confidence</div>
        </div>
      )}
    </div>
  );
};

// Custom node types
const nodeTypes = {
  entity: EntityNode,
};

// Entity details panel
interface EntityDetailsPanelProps {
  entity: OrganogramEntity | null;
  onClose: () => void;
  onResolveConflict?: (entityId: string) => void;
}

const EntityDetailsPanel: React.FC<EntityDetailsPanelProps> = ({
  entity,
  onClose,
  onResolveConflict
}) => {
  if (!entity) return null;

  const config = RELATIONSHIP_CONFIG[entity.relationship_to_target] || RELATIONSHIP_CONFIG.unknown;
  const Icon = config.icon;

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      className="absolute top-4 right-4 w-80 bg-white rounded-xl shadow-xl border border-gray-200 overflow-hidden z-10"
    >
      {/* Header */}
      <div className={cn("px-4 py-3 border-b", config.bgColor)}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Icon className={cn("w-5 h-5", config.color)} />
            <span className={cn("font-medium", config.color)}>{config.label}</span>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-white/50 rounded transition-colors"
          >
            <X className="w-4 h-4 text-gray-500" />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="p-4 space-y-4">
        <div>
          <h3 className="font-semibold text-gray-900 text-lg">{entity.entity_name}</h3>
          {entity.registration_number && (
            <p className="text-sm text-gray-500">{entity.registration_number}</p>
          )}
        </div>

        {/* Conflict warning */}
        {entity.has_conflict && (
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
            <div className="flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-amber-800">Conflict Detected</p>
                <p className="text-xs text-amber-700 mt-1">{entity.conflict_details}</p>
                {onResolveConflict && (
                  <Button
                    size="sm"
                    variant="outline"
                    className="mt-2 text-amber-700 border-amber-300 hover:bg-amber-100"
                    onClick={() => onResolveConflict(entity.id)}
                  >
                    Resolve Conflict
                  </Button>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Ownership */}
        {entity.ownership_percentage && (
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide">Ownership</p>
            <p className="text-sm font-medium text-gray-900">{entity.ownership_percentage}%</p>
          </div>
        )}

        {/* Relationship detail */}
        {entity.relationship_detail && (
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide">Relationship</p>
            <p className="text-sm text-gray-700">{entity.relationship_detail}</p>
          </div>
        )}

        {/* Evidence */}
        {entity.evidence && (
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide">Evidence</p>
            <p className="text-sm text-gray-700 line-clamp-3">{entity.evidence}</p>
          </div>
        )}

        {/* Documents */}
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">
            Found in {entity.documents_appearing_in.length} document(s)
          </p>
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {entity.documents_appearing_in.slice(0, 5).map((docName, idx) => (
              <div key={idx} className="flex items-center gap-2 text-sm text-gray-600">
                <FileText className="w-3 h-3 flex-shrink-0" />
                <span className="truncate">{docName}</span>
              </div>
            ))}
            {entity.documents_appearing_in.length > 5 && (
              <p className="text-xs text-gray-400">
                +{entity.documents_appearing_in.length - 5} more
              </p>
            )}
          </div>
        </div>

        {/* Confidence */}
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wide">Confidence</p>
          <div className="flex items-center gap-2 mt-1">
            <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={cn(
                  "h-full rounded-full",
                  entity.confidence >= 0.8 ? "bg-green-500" :
                  entity.confidence >= 0.5 ? "bg-amber-500" : "bg-red-500"
                )}
                style={{ width: `${entity.confidence * 100}%` }}
              />
            </div>
            <span className="text-sm font-medium">{Math.round(entity.confidence * 100)}%</span>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

// Key Individuals section
interface KeyIndividualsSectionProps {
  individuals: OrganogramEntity[];
  onIndividualClick: (entity: OrganogramEntity) => void;
}

const KeyIndividualsSection: React.FC<KeyIndividualsSectionProps> = ({
  individuals,
  onIndividualClick,
}) => {
  const [isExpanded, setIsExpanded] = useState(true);

  if (individuals.length === 0) return null;

  return (
    <div className="absolute bottom-4 left-4 w-64 bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden z-10">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between bg-gray-50 border-b hover:bg-gray-100 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Users className="w-4 h-4 text-gray-600" />
          <span className="font-medium text-sm text-gray-700">Key Individuals</span>
          <Badge variant="secondary" className="text-xs">{individuals.length}</Badge>
        </div>
        <ChevronRight className={cn(
          "w-4 h-4 text-gray-400 transition-transform",
          isExpanded && "rotate-90"
        )} />
      </button>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: "auto" }}
            exit={{ height: 0 }}
            className="overflow-hidden"
          >
            <div className="p-2 space-y-1 max-h-48 overflow-y-auto">
              {individuals.map((person) => (
                <button
                  key={person.id}
                  onClick={() => onIndividualClick(person)}
                  className="w-full p-2 text-left rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-900 truncate">
                      {person.entity_name}
                    </span>
                    {person.has_conflict && (
                      <AlertTriangle className="w-3 h-3 text-amber-500 flex-shrink-0" />
                    )}
                  </div>
                  <span className="text-xs text-gray-500">
                    {person.relationship_detail || person.relationship_to_target}
                  </span>
                </button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

// Collapsible Legend
const Legend: React.FC = () => {
  const [isExpanded, setIsExpanded] = useState(false);

  const legendItems = [
    { key: "shareholder", label: "Shareholder" },
    { key: "client", label: "Acquirer (Future)" },
    { key: "target", label: "Target Entity" },
    { key: "subsidiary", label: "Subsidiary" },
    { key: "counterparty", label: "Counterparty" },
    { key: "financier", label: "Financier" },
  ];

  return (
    <div className="absolute bottom-4 right-4 bg-white rounded-lg shadow-md border border-gray-200 overflow-hidden z-10">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-3 py-2 flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <span className="text-xs font-medium text-gray-500">Legend</span>
        {isExpanded ? (
          <ChevronDown className="w-3 h-3 text-gray-400" />
        ) : (
          <ChevronRight className="w-3 h-3 text-gray-400" />
        )}
      </button>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: "auto" }}
            exit={{ height: 0 }}
            className="overflow-hidden border-t"
          >
            <div className="p-2 space-y-1">
              {legendItems.map(({ key, label }) => {
                const config = RELATIONSHIP_CONFIG[key];
                if (!config) return null;
                return (
                  <div key={key} className="flex items-center gap-2">
                    <div className={cn(
                      "w-4 h-3 rounded border",
                      config.bgColor,
                      config.borderColor,
                      key === "client" && "border-dashed"
                    )} />
                    <span className="text-xs text-gray-600">{label}</span>
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

// Main component
export const EntityOrganogram: React.FC<EntityOrganogramProps> = ({
  data,
  onEntityClick,
  onResolveConflict,
  className,
}) => {
  const [selectedEntity, setSelectedEntity] = useState<OrganogramEntity | null>(null);

  // Separate individuals from other entities
  const { corporateEntities, individuals } = useMemo(() => {
    const corps: OrganogramEntity[] = [];
    const indivs: OrganogramEntity[] = [];

    data.entities.forEach((entity) => {
      if (entity.is_individual ||
          entity.relationship_to_target === "key_individual" ||
          entity.relationship_to_target === "director" ||
          entity.relationship_to_target === "officer") {
        indivs.push(entity);
      } else {
        corps.push(entity);
      }
    });

    return { corporateEntities: corps, individuals: indivs };
  }, [data.entities]);

  // Convert entities to React Flow nodes and edges
  const { nodes: initialNodes, edges: initialEdges } = useMemo(() => {
    const nodes: Node[] = [];
    const edges: Edge[] = [];

    // Layout constants
    const centerX = 450;
    const centerY = 280;
    const verticalGap = 140;
    const horizontalGap = 220;

    // Group entities by relationship type
    const subsidiaries = corporateEntities.filter(e =>
      e.relationship_to_target === "subsidiary"
    );
    const leftEntities = corporateEntities.filter(e =>
      ["supplier", "customer", "related_party"].includes(e.relationship_to_target)
    );
    const rightEntities = corporateEntities.filter(e =>
      ["counterparty", "financier", "lender", "unknown"].includes(e.relationship_to_target)
    );

    // Use shareholders from wizard data
    const shareholders = data.shareholders || [];

    // Add target entity node (center)
    const targetNode: Node = {
      id: "target",
      type: "entity",
      position: { x: centerX, y: centerY },
      data: {
        label: data.target_entity.name,
        registrationNumber: data.target_entity.registration_number,
        relationship: "target",
        confidence: 1,
        docsCount: 0,
        onClick: () => {},
      },
    };
    nodes.push(targetNode);

    // Add client/acquirer node (future owner - top left, dotted)
    if (data.client_entity) {
      const clientNode: Node = {
        id: "client",
        type: "entity",
        position: { x: centerX - horizontalGap * 1.2, y: centerY - verticalGap },
        data: {
          label: data.client_entity.name,
          relationship: "client",
          confidence: 1,
          docsCount: 0,
          dealStructure: data.client_entity.deal_structure,
          onClick: () => {},
        },
      };
      nodes.push(clientNode);

      // Edge from client to target (dashed, showing future acquisition)
      edges.push({
        id: "client-target",
        source: "client",
        target: "target",
        type: "smoothstep",
        animated: true,
        style: { stroke: "#6366f1", strokeWidth: 2, strokeDasharray: "8,4" },
        markerEnd: { type: MarkerType.ArrowClosed, color: "#6366f1" },
        label: data.client_entity.deal_structure || "Acquisition",
        labelStyle: { fontSize: 10, fill: "#4338ca", fontWeight: 600 },
        labelBgStyle: { fill: "#e0e7ff", fillOpacity: 0.9 },
      });
    }

    // Add shareholder nodes (above target)
    shareholders.forEach((sh, idx) => {
      const totalShareholders = shareholders.length + (data.client_entity ? 0 : 0);
      const startX = centerX - ((totalShareholders - 1) * horizontalGap * 0.5) / 2;
      const xOffset = data.client_entity ? horizontalGap * 0.6 : 0; // Shift right if client exists

      nodes.push({
        id: `shareholder-${idx}`,
        type: "entity",
        position: {
          x: startX + idx * horizontalGap * 0.9 + xOffset,
          y: centerY - verticalGap
        },
        data: {
          label: sh.name,
          relationship: "shareholder",
          confidence: 1,
          docsCount: 0,
          ownershipPercentage: sh.ownership_percentage,
          onClick: () => {},
        },
      });

      // Edge from shareholder to target
      edges.push({
        id: `shareholder-${idx}-target`,
        source: `shareholder-${idx}`,
        target: "target",
        type: "smoothstep",
        style: { stroke: "#a855f7", strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: "#a855f7" },
        label: sh.ownership_percentage ? `${sh.ownership_percentage}%` : undefined,
        labelStyle: { fontSize: 11, fontWeight: 600, fill: "#7c3aed" },
        labelBgStyle: { fill: "white", fillOpacity: 0.9 },
      });
    });

    // Add subsidiary nodes (below target)
    subsidiaries.forEach((entity, idx) => {
      const xOffset = (idx - (subsidiaries.length - 1) / 2) * (horizontalGap * 0.8);
      nodes.push({
        id: entity.id,
        type: "entity",
        position: { x: centerX + xOffset, y: centerY + verticalGap },
        data: {
          label: entity.entity_name,
          registrationNumber: entity.registration_number,
          relationship: entity.relationship_to_target,
          confidence: entity.confidence,
          docsCount: entity.documents_appearing_in.length,
          ownershipPercentage: entity.ownership_percentage,
          hasConflict: entity.has_conflict,
          onClick: () => {
            setSelectedEntity(entity);
            onEntityClick?.(entity);
          },
        },
      });

      // Edge from target to subsidiary
      edges.push({
        id: `target-${entity.id}`,
        source: "target",
        target: entity.id,
        type: "smoothstep",
        style: { stroke: "#22c55e", strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: "#22c55e" },
        label: entity.ownership_percentage ? `${entity.ownership_percentage}%` : undefined,
        labelStyle: { fontSize: 11, fontWeight: 500 },
        labelBgStyle: { fill: "white", fillOpacity: 0.8 },
      });
    });

    // Add left side entities (suppliers, customers, related)
    leftEntities.forEach((entity, idx) => {
      nodes.push({
        id: entity.id,
        type: "entity",
        position: { x: centerX - horizontalGap * 1.6, y: centerY + (idx - (leftEntities.length - 1) / 2) * 90 },
        data: {
          label: entity.entity_name,
          registrationNumber: entity.registration_number,
          relationship: entity.relationship_to_target,
          confidence: entity.confidence,
          docsCount: entity.documents_appearing_in.length,
          hasConflict: entity.has_conflict,
          onClick: () => {
            setSelectedEntity(entity);
            onEntityClick?.(entity);
          },
        },
      });

      // Edge to target
      edges.push({
        id: `${entity.id}-target`,
        source: entity.id,
        sourceHandle: "right",
        target: "target",
        targetHandle: "left",
        type: "smoothstep",
        style: { stroke: "#9ca3af", strokeWidth: 1, strokeDasharray: "3,3" },
      });
    });

    // Add right side entities (counterparties, financiers)
    rightEntities.forEach((entity, idx) => {
      nodes.push({
        id: entity.id,
        type: "entity",
        position: { x: centerX + horizontalGap * 1.6, y: centerY + (idx - (rightEntities.length - 1) / 2) * 90 },
        data: {
          label: entity.entity_name,
          registrationNumber: entity.registration_number,
          relationship: entity.relationship_to_target,
          confidence: entity.confidence,
          docsCount: entity.documents_appearing_in.length,
          hasConflict: entity.has_conflict,
          onClick: () => {
            setSelectedEntity(entity);
            onEntityClick?.(entity);
          },
        },
      });

      // Edge to target
      edges.push({
        id: `target-${entity.id}`,
        source: "target",
        sourceHandle: "right",
        target: entity.id,
        targetHandle: "left",
        type: "smoothstep",
        style: {
          stroke: entity.relationship_to_target === "financier" || entity.relationship_to_target === "lender"
            ? "#10b981" : "#f59e0b",
          strokeWidth: 1.5,
        },
      });
    });

    return { nodes, edges };
  }, [corporateEntities, data.target_entity, data.client_entity, data.shareholders, onEntityClick]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const handleEntityClick = useCallback((entity: OrganogramEntity) => {
    setSelectedEntity(entity);
    onEntityClick?.(entity);
  }, [onEntityClick]);

  return (
    <div className={cn("relative w-full bg-gray-50 rounded-lg overflow-hidden", className)} style={{ height: "500px", minHeight: "500px" }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.15 }}
        minZoom={0.3}
        maxZoom={1.5}
        defaultViewport={{ x: 0, y: 0, zoom: 0.85 }}
      >
        <Background color="#e5e7eb" gap={20} />
        <Controls
          className="!bg-white !border-gray-200 !shadow-md"
          showInteractive={false}
        />
        <MiniMap
          className="!bg-white !border-gray-200"
          nodeColor={(node) => {
            const rel = node.data?.relationship;
            if (rel === "target") return "#fb923c";
            if (rel === "client") return "#818cf8";
            if (rel === "shareholder") return "#c084fc";
            if (rel === "subsidiary") return "#4ade80";
            if (rel === "counterparty") return "#fbbf24";
            if (rel === "financier" || rel === "lender") return "#34d399";
            return "#9ca3af";
          }}
          maskColor="rgba(0,0,0,0.1)"
        />
      </ReactFlow>

      {/* Entity details panel */}
      <AnimatePresence>
        {selectedEntity && (
          <EntityDetailsPanel
            entity={selectedEntity}
            onClose={() => setSelectedEntity(null)}
            onResolveConflict={onResolveConflict}
          />
        )}
      </AnimatePresence>

      {/* Key Individuals section */}
      <KeyIndividualsSection
        individuals={individuals}
        onIndividualClick={handleEntityClick}
      />

      {/* Collapsible Legend - bottom right */}
      <Legend />
    </div>
  );
};

export default EntityOrganogram;
