/**
 * Entity Organogram - Interactive corporate structure visualization
 *
 * Layout:
 * - Center: Corporate structure (parent → target → subsidiaries)
 * - Target entity highlighted with transaction type
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
  Target,
  Link2,
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

export interface OrganogramData {
  target_entity: {
    name: string;
    registration_number?: string;
    transaction_type?: string;
    transaction_counterparty?: string;
  };
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
  position: "top" | "bottom" | "left" | "right";
}> = {
  parent: {
    color: "text-blue-700",
    bgColor: "bg-blue-50",
    borderColor: "border-blue-300",
    icon: Building2,
    label: "Parent",
    position: "top"
  },
  holding_company: {
    color: "text-blue-700",
    bgColor: "bg-blue-50",
    borderColor: "border-blue-300",
    icon: Building2,
    label: "Holding",
    position: "top"
  },
  target: {
    color: "text-orange-700",
    bgColor: "bg-orange-50",
    borderColor: "border-orange-400",
    icon: Target,
    label: "Target",
    position: "top"
  },
  subsidiary: {
    color: "text-green-700",
    bgColor: "bg-green-50",
    borderColor: "border-green-300",
    icon: Building,
    label: "Subsidiary",
    position: "bottom"
  },
  shareholder: {
    color: "text-purple-700",
    bgColor: "bg-purple-50",
    borderColor: "border-purple-300",
    icon: Users,
    label: "Shareholder",
    position: "top"
  },
  counterparty: {
    color: "text-amber-700",
    bgColor: "bg-amber-50",
    borderColor: "border-amber-300",
    icon: Briefcase,
    label: "Counterparty",
    position: "right"
  },
  financier: {
    color: "text-emerald-700",
    bgColor: "bg-emerald-50",
    borderColor: "border-emerald-300",
    icon: Landmark,
    label: "Financier",
    position: "right"
  },
  lender: {
    color: "text-emerald-700",
    bgColor: "bg-emerald-50",
    borderColor: "border-emerald-300",
    icon: Landmark,
    label: "Lender",
    position: "right"
  },
  supplier: {
    color: "text-cyan-700",
    bgColor: "bg-cyan-50",
    borderColor: "border-cyan-300",
    icon: Truck,
    label: "Supplier",
    position: "left"
  },
  customer: {
    color: "text-pink-700",
    bgColor: "bg-pink-50",
    borderColor: "border-pink-300",
    icon: ShoppingCart,
    label: "Customer",
    position: "left"
  },
  related_party: {
    color: "text-gray-700",
    bgColor: "bg-gray-50",
    borderColor: "border-gray-300",
    icon: Link2,
    label: "Related",
    position: "left"
  },
  unknown: {
    color: "text-gray-500",
    bgColor: "bg-gray-50",
    borderColor: "border-gray-200",
    icon: Building,
    label: "Unknown",
    position: "right"
  },
};

// Custom node component for entities
const EntityNode: React.FC<NodeProps> = ({ data }) => {
  const config = RELATIONSHIP_CONFIG[data.relationship] || RELATIONSHIP_CONFIG.unknown;
  const Icon = config.icon;
  const isTarget = data.relationship === "target";

  return (
    <div
      className={cn(
        "relative px-4 py-3 rounded-lg border-2 shadow-sm transition-all duration-200",
        "hover:shadow-md hover:scale-105 cursor-pointer min-w-[180px] max-w-[220px]",
        config.bgColor,
        config.borderColor,
        isTarget && "ring-2 ring-orange-400 ring-offset-2"
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
      <div className="font-semibold text-sm text-gray-900 truncate" title={data.label}>
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

      {/* Transaction type for counterparties linked to target */}
      {data.transactionType && (
        <div className="mt-1.5 px-2 py-1 bg-orange-100 rounded text-xs text-orange-700 font-medium">
          {data.transactionType}
        </div>
      )}

      {/* Confidence indicator */}
      <div className="mt-2 flex items-center gap-1">
        <div className="flex-1 h-1 bg-gray-200 rounded-full overflow-hidden">
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
            {entity.documents_appearing_in.slice(0, 5).map((docId, idx) => (
              <div key={idx} className="flex items-center gap-2 text-sm text-gray-600">
                <FileText className="w-3 h-3" />
                <span className="truncate">{docId}</span>
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
    const centerX = 400;
    const centerY = 300;
    const verticalGap = 120;
    const horizontalGap = 250;

    // Group entities by relationship type
    const parents = corporateEntities.filter(e =>
      e.relationship_to_target === "parent" || e.relationship_to_target === "holding_company"
    );
    const subsidiaries = corporateEntities.filter(e =>
      e.relationship_to_target === "subsidiary"
    );
    const shareholders = corporateEntities.filter(e =>
      e.relationship_to_target === "shareholder"
    );
    const leftEntities = corporateEntities.filter(e =>
      ["supplier", "customer", "related_party"].includes(e.relationship_to_target)
    );
    const rightEntities = corporateEntities.filter(e =>
      ["counterparty", "financier", "lender", "unknown"].includes(e.relationship_to_target)
    );

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
        transactionType: data.target_entity.transaction_type,
        onClick: () => {},
      },
    };
    nodes.push(targetNode);

    // Add parent/holding company nodes (above target)
    parents.forEach((entity, idx) => {
      const xOffset = (idx - (parents.length - 1) / 2) * horizontalGap;
      nodes.push({
        id: entity.id,
        type: "entity",
        position: { x: centerX + xOffset, y: centerY - verticalGap },
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

      // Edge from parent to target
      edges.push({
        id: `${entity.id}-target`,
        source: entity.id,
        target: "target",
        type: "smoothstep",
        animated: false,
        style: { stroke: "#9ca3af", strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: "#9ca3af" },
        label: entity.ownership_percentage ? `${entity.ownership_percentage}%` : undefined,
        labelStyle: { fontSize: 11, fontWeight: 500 },
        labelBgStyle: { fill: "white", fillOpacity: 0.8 },
      });
    });

    // Add shareholder nodes (above and to sides)
    shareholders.forEach((entity, idx) => {
      const angle = (idx / shareholders.length) * Math.PI - Math.PI / 2;
      const radius = 180;
      const xPos = centerX + Math.cos(angle) * radius * 1.5;
      const yPos = centerY - verticalGap - 40 + Math.sin(angle) * 60;

      nodes.push({
        id: entity.id,
        type: "entity",
        position: { x: xPos, y: yPos },
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

      // Edge from shareholder to target (or to parent if parent exists)
      const targetId = parents.length > 0 ? parents[0].id : "target";
      edges.push({
        id: `${entity.id}-${targetId}`,
        source: entity.id,
        target: targetId,
        type: "smoothstep",
        style: { stroke: "#a855f7", strokeWidth: 1.5, strokeDasharray: "5,5" },
        label: entity.ownership_percentage ? `${entity.ownership_percentage}%` : undefined,
        labelStyle: { fontSize: 10, fill: "#7c3aed" },
        labelBgStyle: { fill: "white", fillOpacity: 0.8 },
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
        position: { x: centerX - horizontalGap * 1.5, y: centerY - 60 + idx * 100 },
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
      const isCounterparty = entity.relationship_to_target === "counterparty";
      nodes.push({
        id: entity.id,
        type: "entity",
        position: { x: centerX + horizontalGap * 1.5, y: centerY - 60 + idx * 100 },
        data: {
          label: entity.entity_name,
          registrationNumber: entity.registration_number,
          relationship: entity.relationship_to_target,
          confidence: entity.confidence,
          docsCount: entity.documents_appearing_in.length,
          hasConflict: entity.has_conflict,
          transactionType: isCounterparty ? data.target_entity.transaction_type : undefined,
          onClick: () => {
            setSelectedEntity(entity);
            onEntityClick?.(entity);
          },
        },
      });

      // Edge to target with transaction type
      edges.push({
        id: `target-${entity.id}`,
        source: "target",
        sourceHandle: "right",
        target: entity.id,
        targetHandle: "left",
        type: "smoothstep",
        style: {
          stroke: isCounterparty ? "#f59e0b" : "#9ca3af",
          strokeWidth: isCounterparty ? 2 : 1,
        },
        markerEnd: isCounterparty ? { type: MarkerType.ArrowClosed, color: "#f59e0b" } : undefined,
        label: isCounterparty && data.target_entity.transaction_type
          ? data.target_entity.transaction_type
          : undefined,
        labelStyle: { fontSize: 10, fill: "#b45309", fontWeight: 500 },
        labelBgStyle: { fill: "#fef3c7", fillOpacity: 0.9 },
      });
    });

    return { nodes, edges };
  }, [corporateEntities, data.target_entity, onEntityClick]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const handleEntityClick = useCallback((entity: OrganogramEntity) => {
    setSelectedEntity(entity);
    onEntityClick?.(entity);
  }, [onEntityClick]);

  return (
    <div className={cn("relative w-full h-[600px] bg-gray-50 rounded-lg overflow-hidden", className)}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.3}
        maxZoom={1.5}
        defaultViewport={{ x: 0, y: 0, zoom: 0.8 }}
      >
        <Background color="#e5e7eb" gap={20} />
        <Controls
          className="!bg-white !border-gray-200 !shadow-md"
          showInteractive={false}
        />
        <MiniMap
          className="!bg-white !border-gray-200"
          nodeColor={(node) => {
            const config = RELATIONSHIP_CONFIG[node.data?.relationship] || RELATIONSHIP_CONFIG.unknown;
            return config.borderColor.replace("border-", "").replace("-300", "-400").replace("-400", "-500");
          }}
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

      {/* Legend */}
      <div className="absolute top-4 left-4 bg-white rounded-lg shadow-md border border-gray-200 p-3 z-10">
        <p className="text-xs font-medium text-gray-500 mb-2">Legend</p>
        <div className="space-y-1">
          {[
            { key: "parent", label: "Parent/Holding" },
            { key: "target", label: "Target Entity" },
            { key: "subsidiary", label: "Subsidiary" },
            { key: "counterparty", label: "Counterparty" },
            { key: "financier", label: "Financier" },
          ].map(({ key, label }) => {
            const config = RELATIONSHIP_CONFIG[key];
            const Icon = config.icon;
            return (
              <div key={key} className="flex items-center gap-2">
                <div className={cn("w-3 h-3 rounded", config.bgColor, config.borderColor, "border")} />
                <span className="text-xs text-gray-600">{label}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default EntityOrganogram;
