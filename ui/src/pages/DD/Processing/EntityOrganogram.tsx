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
import React, { useCallback, useMemo, useState, useEffect, useRef } from "react";
import {
  ReactFlow,
  Node,
  Edge,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  Position,
  MarkerType,
  Handle,
  NodeProps,
  ReactFlowInstance,
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
  id_number?: string;
  address?: string;
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
  isFullscreen?: boolean;
}

// Entity node data interface for React Flow
interface EntityNodeData {
  label: string;
  relationship: string;
  confidence?: number;
  docsCount?: number;
  registrationNumber?: string;
  ownershipPercentage?: number;
  dealStructure?: string;
  hasConflict?: boolean;
  onClick?: () => void;
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
    color: "text-green-700",
    bgColor: "bg-green-50",
    borderColor: "border-green-500",
    icon: Target,
    label: "Target",
  },
  subsidiary: {
    color: "text-yellow-700",
    bgColor: "bg-yellow-50",
    borderColor: "border-yellow-400",
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
  key_individual: {
    color: "text-gray-700",
    bgColor: "bg-white",
    borderColor: "border-gray-800",
    icon: Users,
    label: "Key Individual",
  },
  director: {
    color: "text-gray-700",
    bgColor: "bg-white",
    borderColor: "border-gray-800",
    icon: Users,
    label: "Director",
  },
  officer: {
    color: "text-gray-700",
    bgColor: "bg-white",
    borderColor: "border-gray-800",
    icon: Users,
    label: "Officer",
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
const EntityNode: React.FC<NodeProps> = ({ data: rawData }) => {
  const data = rawData as unknown as EntityNodeData;
  const config = RELATIONSHIP_CONFIG[data.relationship] || RELATIONSHIP_CONFIG.unknown;
  const Icon = config.icon;
  const isTarget = data.relationship === "target";
  const isClient = data.relationship === "client";
  const isShareholder = data.relationship === "shareholder";
  const isCompact = ["counterparty", "financier", "lender", "supplier", "customer", "related_party", "unknown", "key_individual", "director", "officer"].includes(data.relationship);

  // Compact node for counterparties/related parties
  if (isCompact) {
    return (
      <div
        className={cn(
          "relative px-2 py-1.5 rounded border shadow-sm transition-all duration-200",
          "hover:shadow-md cursor-pointer w-[150px]",
          config.bgColor,
          config.borderColor
        )}
        onClick={data.onClick}
      >
        <Handle type="target" position={Position.Top} className="!bg-gray-400 !w-1.5 !h-1.5" />
        <Handle type="source" position={Position.Bottom} className="!bg-gray-400 !w-1.5 !h-1.5" />
        <Handle type="target" position={Position.Left} id="left" className="!bg-gray-400 !w-1.5 !h-1.5" />
        <Handle type="source" position={Position.Right} id="right" className="!bg-gray-400 !w-1.5 !h-1.5" />

        {data.hasConflict && (
          <div className="absolute -top-1.5 -right-1.5 p-0.5 bg-amber-100 rounded-full border border-amber-400">
            <AlertTriangle className="w-2 h-2 text-amber-600" />
          </div>
        )}

        <div className="flex items-center gap-1 mb-0.5">
          <Icon className={cn("w-3 h-3", config.color)} />
          <span className={cn("text-[9px] font-medium", config.color)}>{config.label}</span>
          {data.docsCount > 0 && (
            <span className="text-[8px] text-gray-400 ml-auto">{data.docsCount}d</span>
          )}
        </div>
        <div className="font-medium text-[10px] text-gray-900 leading-tight truncate" title={data.label}>
          {data.label}
        </div>
        {data.confidence !== undefined && data.confidence < 1 && (
          <div className="mt-1 flex items-center gap-1">
            <div className="flex-1 h-1 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={cn(
                  "h-full rounded-full",
                  data.confidence >= 0.8 ? "bg-green-500" : data.confidence >= 0.5 ? "bg-amber-500" : "bg-red-500"
                )}
                style={{ width: `${data.confidence * 100}%` }}
              />
            </div>
            <span className="text-[8px] text-gray-400">{Math.round(data.confidence * 100)}%</span>
          </div>
        )}
      </div>
    );
  }

  // Compact shareholder node - just entity name, fixed size
  if (isShareholder) {
    return (
      <div
        className={cn(
          "relative px-3 py-2 rounded-lg border-2 shadow-sm transition-all duration-200",
          "hover:shadow-md cursor-pointer w-[175px]",
          config.bgColor,
          config.borderColor
        )}
        onClick={data.onClick}
      >
        <Handle type="target" position={Position.Top} className="!bg-gray-400 !w-2 !h-2" />
        <Handle type="source" position={Position.Bottom} className="!bg-gray-400 !w-2 !h-2" />

        <div className="flex items-center gap-1.5 mb-1">
          <Icon className={cn("w-3 h-3", config.color)} />
          <span className={cn("text-[10px] font-medium", config.color)}>{config.label}</span>
        </div>
        <div className="font-semibold text-xs text-gray-900 leading-tight truncate" title={data.label}>
          {data.label}
        </div>
      </div>
    );
  }

  // Standard node for Target and Client
  return (
    <div
      className={cn(
        "relative px-4 py-3 rounded-lg border-2 shadow-sm transition-all duration-200",
        "hover:shadow-md cursor-pointer",
        config.bgColor,
        config.borderColor,
        isTarget && "ring-2 ring-green-500 ring-offset-2 w-[225px]",
        isClient && "border-dashed border-indigo-400 bg-indigo-50/50 w-[200px]"
      )}
      onClick={data.onClick}
    >
      <Handle type="target" position={Position.Top} className="!bg-gray-400 !w-2 !h-2" />
      <Handle type="source" position={Position.Bottom} className="!bg-gray-400 !w-2 !h-2" />
      <Handle type="target" position={Position.Left} id="left" className="!bg-gray-400 !w-2 !h-2" />
      <Handle type="source" position={Position.Right} id="right" className="!bg-gray-400 !w-2 !h-2" />

      {data.hasConflict && (
        <div className="absolute -top-2 -right-2 p-1 bg-amber-100 rounded-full border border-amber-400">
          <AlertTriangle className="w-3 h-3 text-amber-600" />
        </div>
      )}

      {isClient && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-2 py-0.5 bg-indigo-100 border border-indigo-300 rounded text-[10px] font-medium text-indigo-700 whitespace-nowrap">
          Future Owner
        </div>
      )}

      <div className="flex items-center gap-2 mb-1">
        <Icon className={cn("w-4 h-4", config.color)} />
        <span className={cn("text-xs font-medium", config.color)}>{config.label}</span>
      </div>

      <div className="font-semibold text-sm text-gray-900 leading-tight" title={data.label}>
        {data.label}
      </div>

      {data.registrationNumber && (
        <div className="text-xs text-gray-500 truncate mt-0.5">{data.registrationNumber}</div>
      )}

      {data.dealStructure && (
        <div className="mt-1.5 px-2 py-1 bg-indigo-100 rounded text-xs text-indigo-700 font-medium">
          {data.dealStructure}
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
            <div className="mt-1">
              <p className="text-xs text-gray-500 uppercase tracking-wide">Registration Number</p>
              <p className="text-sm text-gray-700">{entity.registration_number}</p>
            </div>
          )}
          {entity.id_number && (
            <div className="mt-1">
              <p className="text-xs text-gray-500 uppercase tracking-wide">ID Number</p>
              <p className="text-sm text-gray-700">{entity.id_number}</p>
            </div>
          )}
          {entity.address && (
            <div className="mt-2">
              <p className="text-xs text-gray-500 uppercase tracking-wide">Address</p>
              <p className="text-sm text-gray-700">{entity.address}</p>
            </div>
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
    <div className="absolute bottom-4 left-4 w-80 bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden z-10">
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
            <div className="p-2 max-h-48 overflow-y-auto">
              <div className="grid grid-cols-3 gap-1">
                {individuals.map((person) => (
                  <button
                    key={person.id}
                    onClick={() => onIndividualClick(person)}
                    className="p-1.5 text-left rounded hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center gap-1">
                      <span className="text-[10px] font-medium text-gray-900 truncate">
                        {person.entity_name}
                      </span>
                      {person.has_conflict && (
                        <AlertTriangle className="w-2 h-2 text-amber-500 flex-shrink-0" />
                      )}
                    </div>
                    <span className="text-[8px] text-gray-500 truncate block">
                      {person.relationship_detail || person.relationship_to_target}
                    </span>
                  </button>
                ))}
              </div>
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
    { key: "client", label: "Transaction Counterparty" },
    { key: "shareholder", label: "Shareholder" },
    { key: "target", label: "Target Entity" },
    { key: "subsidiary", label: "Subsidiary" },
    { key: "key_individual", label: "Key Individual" },
    { key: "counterparty", label: "Related Stakeholder" },
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
  isFullscreen = false,
}) => {
  const [selectedEntity, setSelectedEntity] = useState<OrganogramEntity | null>(null);

  // Separate individuals from other entities
  const { corporateEntities, individuals } = useMemo(() => {
    const corps: OrganogramEntity[] = [];
    const indivs: OrganogramEntity[] = [];

    data.entities.forEach((entity) => {
      // Check if this is an individual by relationship type or name pattern
      const isIndividualByType = entity.is_individual ||
          entity.relationship_to_target === "key_individual" ||
          entity.relationship_to_target === "director" ||
          entity.relationship_to_target === "officer";

      // Check if name looks like a person (has first + last name pattern, or title)
      const nameParts = entity.entity_name.trim().split(/\s+/);
      const hasTitle = /^(Mr|Mrs|Ms|Dr|Prof|Adv)\.?\s/i.test(entity.entity_name);
      const looksLikePersonName = nameParts.length >= 2 &&
        nameParts.length <= 4 &&
        !entity.entity_name.match(/\b(Ltd|Pty|Inc|LLC|Corp|Company|Bank|Trust|Holdings|Group|SA|NPC)\b/i) &&
        nameParts.every(part => part.length > 1 && /^[A-Z][a-z]/.test(part));

      if (isIndividualByType || hasTitle || looksLikePersonName) {
        indivs.push(entity);
      } else {
        corps.push(entity);
      }
    });

    return { corporateEntities: corps, individuals: indivs };
  }, [data.entities]);

  // Convert entities to React Flow nodes and edges using grid-based layout
  const { nodes: initialNodes, edges: initialEdges } = useMemo(() => {
    const nodes: Node[] = [];
    const edges: Edge[] = [];

    // Layout constants - all positions relative to target center
    const nodeWidth = 175;        // 140 * 1.25
    const nodeHeight = 60;
    const horizontalSpacing = 200; // Space between nodes horizontally (increased for wider nodes)
    const verticalSpacing = 120;   // Space between rows
    const smallNodeWidth = 163;    // 130 * 1.25
    const smallNodeHeight = 55;

    // Group entities by their grid position
    // Row 1 (Top): Transaction counterparties (client + financiers, suppliers, customers from wizard)
    const transactionCounterparties = corporateEntities.filter(e =>
      ["financier", "lender", "supplier", "customer"].includes(e.relationship_to_target)
    );

    // Row 2: Shareholders from wizard data
    const shareholders = data.shareholders || [];

    // Row 3 Left: Key individuals (already separated in `individuals`)
    // Row 3 Right: Related stakeholders (counterparties, related parties, unknown)
    const relatedStakeholders = corporateEntities.filter(e =>
      ["counterparty", "related_party", "unknown"].includes(e.relationship_to_target)
    );

    // Row 4 (Bottom): Subsidiaries
    const subsidiaries = corporateEntities.filter(e =>
      e.relationship_to_target === "subsidiary"
    );

    // Calculate dynamic center based on max width needed
    const maxTopRowItems = Math.max(1, (data.client_entity ? 1 : 0) + transactionCounterparties.length);
    const maxShareholderItems = Math.max(1, shareholders.length);
    const maxSubsidiaryItems = Math.max(1, subsidiaries.length);
    const maxMiddleRowSideItems = Math.max(individuals.length, relatedStakeholders.length);

    const maxHorizontalItems = Math.max(maxTopRowItems, maxShareholderItems, maxSubsidiaryItems);
    const totalWidth = maxHorizontalItems * horizontalSpacing;

    // Calculate dynamic center - more room at top for transaction parties and shareholders
    const centerX = Math.max(500, totalWidth / 2 + 150);
    const centerY = 320;

    // === ROW 3: Target Entity (CENTER) ===
    // Create a pseudo-entity for target so it can be clicked for details
    const targetEntity: OrganogramEntity = {
      id: "target",
      entity_name: data.target_entity.name,
      registration_number: data.target_entity.registration_number,
      relationship_to_target: "target",
      confidence: 1,
      documents_appearing_in: [],
    };

    nodes.push({
      id: "target",
      type: "entity",
      position: { x: centerX - nodeWidth / 2, y: centerY - nodeHeight / 2 },
      data: {
        label: data.target_entity.name,
        registrationNumber: data.target_entity.registration_number,
        relationship: "target",
        confidence: 1,
        docsCount: 0,
        onClick: () => {
          setSelectedEntity(targetEntity);
          onEntityClick?.(targetEntity);
        },
      },
    });

    // === ROW 1: Transaction Counterparties (Top, centered) ===
    const row1Y = centerY - verticalSpacing * 2;

    // Build array of transaction parties: client first, then other counterparties
    type TransactionParty = { id: string; name: string; isClient: boolean; dealStructure?: string; entity?: OrganogramEntity };
    const allTransactionParties: TransactionParty[] = [];

    // Create pseudo-entity for client
    let clientEntity: OrganogramEntity | null = null;
    if (data.client_entity) {
      clientEntity = {
        id: "client",
        entity_name: data.client_entity.name,
        relationship_to_target: "client",
        relationship_detail: data.client_entity.role || "Acquirer/Purchaser",
        confidence: 1,
        documents_appearing_in: [],
      };
      allTransactionParties.push({
        id: "client",
        name: data.client_entity.name,
        isClient: true,
        dealStructure: data.client_entity.deal_structure,
      });
    }

    transactionCounterparties.forEach(e => {
      allTransactionParties.push({
        id: e.id,
        name: e.entity_name,
        isClient: false,
        entity: e,
      });
    });

    if (allTransactionParties.length > 0) {
      const totalTopWidth = allTransactionParties.length * horizontalSpacing;
      const startTopX = centerX - totalTopWidth / 2 + horizontalSpacing / 2 - nodeWidth / 2;

      allTransactionParties.forEach((party, idx) => {
        nodes.push({
          id: party.id,
          type: "entity",
          position: { x: startTopX + idx * horizontalSpacing, y: row1Y },
          data: {
            label: party.name,
            relationship: party.isClient ? "client" : party.entity?.relationship_to_target || "counterparty",
            confidence: party.isClient ? 1 : party.entity?.confidence || 0.5,
            docsCount: party.isClient ? 0 : party.entity?.documents_appearing_in.length || 0,
            dealStructure: party.dealStructure,
            hasConflict: party.isClient ? false : party.entity?.has_conflict || false,
            onClick: () => {
              if (party.isClient && clientEntity) {
                setSelectedEntity(clientEntity);
                onEntityClick?.(clientEntity);
              } else if (party.entity) {
                setSelectedEntity(party.entity);
                onEntityClick?.(party.entity);
              }
            },
          },
        });

        // Edge to target
        edges.push({
          id: `${party.id}-target`,
          source: party.id,
          target: "target",
          type: "smoothstep",
          animated: party.isClient,
          style: {
            stroke: party.isClient ? "#6366f1" : "#f59e0b",
            strokeWidth: 2,
            strokeDasharray: party.isClient ? "8,4" : undefined
          },
          markerEnd: { type: MarkerType.ArrowClosed, color: party.isClient ? "#6366f1" : "#f59e0b" },
          label: party.isClient ? (party.dealStructure || "Acquisition") : undefined,
          labelStyle: { fontSize: 10, fill: "#4338ca", fontWeight: 600 },
          labelBgStyle: { fill: "#e0e7ff", fillOpacity: 0.9 },
        });
      });
    }

    // === ROW 2: Shareholders (centered, expand left/right from center) ===
    const row2Y = centerY - verticalSpacing;
    if (shareholders.length > 0) {
      const totalShareholderWidth = shareholders.length * horizontalSpacing;
      const startShareholderX = centerX - totalShareholderWidth / 2 + horizontalSpacing / 2 - nodeWidth / 2;

      shareholders.forEach((sh, idx) => {
        // Create pseudo-entity for shareholder so it can be clicked for details
        const shareholderEntity: OrganogramEntity = {
          id: `shareholder-${idx}`,
          entity_name: sh.name,
          relationship_to_target: "shareholder",
          relationship_detail: sh.ownership_percentage ? `${sh.ownership_percentage}% ownership stake` : "Shareholder",
          ownership_percentage: sh.ownership_percentage,
          confidence: 1,
          documents_appearing_in: [],
        };

        nodes.push({
          id: `shareholder-${idx}`,
          type: "entity",
          position: { x: startShareholderX + idx * horizontalSpacing, y: row2Y },
          data: {
            label: sh.name,
            relationship: "shareholder",
            confidence: 1,
            docsCount: 0,
            onClick: () => {
              setSelectedEntity(shareholderEntity);
              onEntityClick?.(shareholderEntity);
            },
          },
        });

        // Edge from shareholder to target with ownership percentage
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
    }

    // === ROW 3 LEFT: Key Individuals (vertically aligned with target center) ===
    const leftColumnX = centerX - horizontalSpacing * 2.2;
    const verticalItemSpacing = smallNodeHeight + 20; // Space between stacked items
    if (individuals.length > 0) {
      const totalLeftHeight = individuals.length * verticalItemSpacing;
      const startLeftY = centerY - totalLeftHeight / 2 + smallNodeHeight / 2;

      individuals.forEach((person, idx) => {
        nodes.push({
          id: person.id,
          type: "entity",
          position: { x: leftColumnX - smallNodeWidth / 2, y: startLeftY + idx * verticalItemSpacing },
          data: {
            label: person.entity_name,
            relationship: "key_individual",
            confidence: person.confidence,
            docsCount: person.documents_appearing_in.length,
            hasConflict: person.has_conflict,
            onClick: () => {
              setSelectedEntity(person);
              onEntityClick?.(person);
            },
          },
        });

        // Edge from individual to target
        edges.push({
          id: `${person.id}-target`,
          source: person.id,
          sourceHandle: "right",
          target: "target",
          targetHandle: "left",
          type: "smoothstep",
          style: { stroke: "#6b7280", strokeWidth: 1.5 },
        });
      });
    }

    // === ROW 3 RIGHT: Related Stakeholders (vertically aligned with target center) ===
    const rightColumnX = centerX + horizontalSpacing * 2.2;
    if (relatedStakeholders.length > 0) {
      const totalRightHeight = relatedStakeholders.length * verticalItemSpacing;
      const startRightY = centerY - totalRightHeight / 2 + smallNodeHeight / 2;

      relatedStakeholders.forEach((entity, idx) => {
        nodes.push({
          id: entity.id,
          type: "entity",
          position: { x: rightColumnX - smallNodeWidth / 2, y: startRightY + idx * verticalItemSpacing },
          data: {
            label: entity.entity_name,
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

        // Edge from target to stakeholder
        edges.push({
          id: `target-${entity.id}`,
          source: "target",
          sourceHandle: "right",
          target: entity.id,
          targetHandle: "left",
          type: "smoothstep",
          style: { stroke: "#f59e0b", strokeWidth: 1.5 },
        });
      });
    }

    // === ROW 4: Subsidiaries (Bottom, centered) ===
    const row4Y = centerY + verticalSpacing;
    if (subsidiaries.length > 0) {
      const totalSubsidiaryWidth = subsidiaries.length * horizontalSpacing;
      const startSubsidiaryX = centerX - totalSubsidiaryWidth / 2 + horizontalSpacing / 2 - nodeWidth / 2;

      subsidiaries.forEach((entity, idx) => {
        nodes.push({
          id: entity.id,
          type: "entity",
          position: { x: startSubsidiaryX + idx * horizontalSpacing, y: row4Y },
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

        // Edge from target to subsidiary with ownership percentage
        edges.push({
          id: `target-${entity.id}`,
          source: "target",
          target: entity.id,
          type: "smoothstep",
          style: { stroke: "#eab308", strokeWidth: 2 },
          markerEnd: { type: MarkerType.ArrowClosed, color: "#eab308" },
          label: entity.ownership_percentage ? `${entity.ownership_percentage}%` : undefined,
          labelStyle: { fontSize: 11, fontWeight: 500, fill: "#a16207" },
          labelBgStyle: { fill: "white", fillOpacity: 0.8 },
        });
      });
    }

    return { nodes, edges };
  }, [corporateEntities, individuals, data.target_entity, data.client_entity, data.shareholders, onEntityClick]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const reactFlowInstance = useRef<ReactFlowInstance | null>(null);

  // Sync nodes and edges when data changes (e.g., after AI modification)
  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  const handleEntityClick = useCallback((entity: OrganogramEntity) => {
    setSelectedEntity(entity);
    onEntityClick?.(entity);
  }, [onEntityClick]);

  // Re-fit view when fullscreen mode changes
  useEffect(() => {
    if (reactFlowInstance.current) {
      // Small delay to allow container to resize
      setTimeout(() => {
        reactFlowInstance.current?.fitView({
          padding: isFullscreen ? 0.2 : 0.15,
          minZoom: isFullscreen ? 0.9 : 0.5,
          maxZoom: isFullscreen ? 1.2 : 1.5,
          duration: 300,
        });
      }, 100);
    }
  }, [isFullscreen]);

  const onInit = useCallback((instance: ReactFlowInstance) => {
    reactFlowInstance.current = instance;
  }, []);

  return (
    <div
      className={cn("relative w-full bg-gray-50 rounded-lg overflow-hidden", className)}
      style={{ height: isFullscreen ? "100%" : "500px", width: "100%" }}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        onInit={onInit}
        fitView
        fitViewOptions={{
          padding: isFullscreen ? 0.2 : 0.15,
          minZoom: isFullscreen ? 0.9 : 0.5,
          maxZoom: isFullscreen ? 1.2 : 1.5,
        }}
        minZoom={isFullscreen ? 0.5 : 0.3}
        maxZoom={isFullscreen ? 2 : 1.5}
        defaultViewport={{ x: 0, y: 0, zoom: isFullscreen ? 1 : 0.85 }}
      >
        <Background color="#e5e7eb" gap={20} />
        <Controls
          className="!bg-white !border-gray-200 !shadow-md"
          showInteractive={false}
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

      {/* Collapsible Legend - bottom right */}
      <Legend />
    </div>
  );
};

export default EntityOrganogram;
