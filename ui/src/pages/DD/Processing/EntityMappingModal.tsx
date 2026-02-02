/**
 * Entity Mapping Modal
 *
 * Shows:
 * 1. Progress while entity mapping is running
 * 2. Interactive organogram after completion
 * 3. Summary statistics
 * 4. Conflict resolution for entities needing confirmation
 */
import React, { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Network,
  Building2,
  AlertTriangle,
  Loader2,
  List,
  GitBranch,
  CheckCircle2,
  X,
  ChevronRight,
  ChevronDown,
  FileText,
  Maximize2,
  Minimize2,
  Sparkles,
  Send,
  Save,
} from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { EntityOrganogram, OrganogramEntity, OrganogramData } from "./EntityOrganogram";

// Types based on backend response
export interface EntityMapEntry {
  id?: string;
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
}

export interface EntityMappingSummary {
  total_unique_entities: number;
  entities_needing_confirmation: number;
  target_subsidiaries: number;
  counterparties: number;
}

export interface ClientEntityInfo {
  name: string;
  role?: string;
  deal_structure?: string;
}

export interface ShareholderInfo {
  name: string;
  ownership_percentage?: number;
}

export interface EntityMappingResult {
  dd_id: string;
  run_id?: string;
  status: string;
  total_documents_processed: number;
  entity_map: EntityMapEntry[];
  summary: EntityMappingSummary;
  checkpoint_recommended: boolean;
  checkpoint_reason?: string;
  stored_count: number;
  target_entity?: {
    name: string;
    registration_number?: string;
    transaction_type?: string;
    deal_structure?: string;
  };
  client_entity?: ClientEntityInfo;
  shareholders?: ShareholderInfo[];
  cost?: {
    total_cost: number;
    total_tokens: number;
  };
}

interface EntityMappingModalProps {
  isOpen: boolean;
  onClose: () => void;
  isRunning: boolean;
  progress?: number;
  result?: EntityMappingResult | null;
  ddId?: string;
  onConfirmEntities?: (confirmations: Record<string, string>) => void;
  onModifyWithAI?: (instruction: string, currentEntityMap: EntityMapEntry[]) => Promise<{
    success: boolean;
    entity_map: EntityMapEntry[];
    changes_made: Array<{ entity_name: string; change_type: string; description: string }>;
    explanation: string;
    error?: string;
  }>;
  onConfirmEntityMap?: (entityMap: EntityMapEntry[]) => Promise<{
    success: boolean;
    confirmed_count: number;
    message: string;
  }>;
}

// Relationship type options for human confirmation
const RELATIONSHIP_OPTIONS = [
  { value: "subsidiary", label: "Subsidiary", description: "Owned by the target company" },
  { value: "parent", label: "Parent/Holding", description: "Owns shares in the target company" },
  { value: "shareholder", label: "Shareholder", description: "Holds equity in the target" },
  { value: "counterparty", label: "Counterparty", description: "Contractual partner (not related)" },
  { value: "financier", label: "Financier/Lender", description: "Provides financing" },
  { value: "supplier", label: "Supplier", description: "Provides goods/services" },
  { value: "customer", label: "Customer", description: "Purchases goods/services" },
  { value: "related_party", label: "Related Party", description: "Other related entity" },
  { value: "exclude", label: "Exclude", description: "Not relevant, exclude from map" },
];

// Conflict Resolution Dialog
interface ConflictResolutionDialogProps {
  entity: OrganogramEntity | null;
  onClose: () => void;
  onConfirm: (entityId: string, relationship: string, details?: string) => void;
}

const ConflictResolutionDialog: React.FC<ConflictResolutionDialogProps> = ({
  entity,
  onClose,
  onConfirm,
}) => {
  const [selectedRelationship, setSelectedRelationship] = useState<string>("");
  const [customDetails, setCustomDetails] = useState<string>("");

  if (!entity) return null;

  const handleConfirm = () => {
    if (selectedRelationship) {
      onConfirm(entity.id, selectedRelationship, customDetails);
      onClose();
    }
  };

  return (
    <Dialog open={!!entity} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-500" />
            Resolve Conflict
          </DialogTitle>
          <DialogDescription>
            Please confirm the relationship for this entity
          </DialogDescription>
        </DialogHeader>

        <div className="py-4 space-y-4">
          {/* Entity info */}
          <div className="p-3 bg-gray-50 rounded-lg">
            <div className="font-semibold text-gray-900">{entity.entity_name}</div>
            {entity.registration_number && (
              <div className="text-sm text-gray-500">{entity.registration_number}</div>
            )}
            {entity.conflict_details && (
              <div className="mt-2 text-sm text-amber-700 bg-amber-50 p-2 rounded">
                {entity.conflict_details}
              </div>
            )}
          </div>

          {/* Relationship options */}
          <RadioGroup value={selectedRelationship} onValueChange={setSelectedRelationship}>
            <div className="space-y-2">
              {RELATIONSHIP_OPTIONS.map((option) => (
                <div
                  key={option.value}
                  className={cn(
                    "flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors",
                    selectedRelationship === option.value
                      ? "border-indigo-300 bg-indigo-50"
                      : "border-gray-200 hover:bg-gray-50"
                  )}
                  onClick={() => setSelectedRelationship(option.value)}
                >
                  <RadioGroupItem value={option.value} id={option.value} className="mt-0.5" />
                  <div>
                    <Label htmlFor={option.value} className="font-medium cursor-pointer">
                      {option.label}
                    </Label>
                    <p className="text-xs text-gray-500">{option.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </RadioGroup>

          {/* Additional details */}
          <div>
            <Label htmlFor="details" className="text-sm">
              Additional Details (optional)
            </Label>
            <Input
              id="details"
              placeholder="e.g., ownership percentage, specific relationship..."
              value={customDetails}
              onChange={(e) => setCustomDetails(e.target.value)}
              className="mt-1"
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleConfirm} disabled={!selectedRelationship}>
            Confirm Relationship
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

// List view component for entities
interface EntityListViewProps {
  entities: EntityMapEntry[];
  onEntityClick: (entity: EntityMapEntry) => void;
}

const EntityListView: React.FC<EntityListViewProps> = ({ entities, onEntityClick }) => {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const groupedEntities = useMemo(() => {
    const groups: Record<string, EntityMapEntry[]> = {};
    entities.forEach((entity) => {
      const key = entity.relationship_to_target || "unknown";
      if (!groups[key]) groups[key] = [];
      groups[key].push(entity);
    });
    return groups;
  }, [entities]);

  const relationshipLabels: Record<string, string> = {
    parent: "Parent/Holding Companies",
    holding_company: "Holding Companies",
    subsidiary: "Subsidiaries",
    shareholder: "Shareholders",
    counterparty: "Counterparties",
    financier: "Financiers/Lenders",
    lender: "Lenders",
    supplier: "Suppliers",
    customer: "Customers",
    related_party: "Related Parties",
    unknown: "Unclassified",
  };

  return (
    <div className="space-y-4 max-h-[400px] overflow-y-auto pr-2">
      {Object.entries(groupedEntities).map(([relationship, groupEntities]) => (
        <div key={relationship}>
          <h4 className="text-sm font-medium text-gray-700 mb-2 sticky top-0 bg-white py-1">
            {relationshipLabels[relationship] || relationship} ({groupEntities.length})
          </h4>
          <div className="space-y-1">
            {groupEntities.map((entity, idx) => (
              <div
                key={entity.id || `${entity.entity_name}-${idx}`}
                className={cn(
                  "p-3 rounded-lg border cursor-pointer transition-all",
                  entity.requires_human_confirmation
                    ? "border-amber-200 bg-amber-50/50 hover:bg-amber-50"
                    : "border-gray-200 hover:bg-gray-50",
                  expandedId === (entity.id || entity.entity_name) && "ring-2 ring-indigo-300"
                )}
                onClick={() => {
                  setExpandedId(expandedId === (entity.id || entity.entity_name) ? null : (entity.id || entity.entity_name));
                  onEntityClick(entity);
                }}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {entity.requires_human_confirmation && (
                      <AlertTriangle className="w-4 h-4 text-amber-500" />
                    )}
                    <span className="font-medium text-sm">{entity.entity_name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={cn(
                      "text-xs font-medium",
                      entity.confidence >= 0.8 ? "text-green-600" :
                      entity.confidence >= 0.5 ? "text-amber-600" : "text-red-600"
                    )}>
                      {Math.round(entity.confidence * 100)}%
                    </span>
                    <Badge variant="secondary" className="text-xs">
                      {entity.documents_appearing_in?.length || 0} docs
                    </Badge>
                    {expandedId === (entity.id || entity.entity_name) ? (
                      <ChevronDown className="w-4 h-4 text-gray-400" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-gray-400" />
                    )}
                  </div>
                </div>

                {expandedId === (entity.id || entity.entity_name) && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    className="mt-3 pt-3 border-t border-gray-200 space-y-2"
                  >
                    {entity.registration_number && (
                      <div className="text-xs">
                        <span className="text-gray-500">Registration:</span>{" "}
                        <span className="font-medium">{entity.registration_number}</span>
                      </div>
                    )}
                    {entity.ownership_percentage && (
                      <div className="text-xs">
                        <span className="text-gray-500">Ownership:</span>{" "}
                        <span className="font-medium">{entity.ownership_percentage}%</span>
                      </div>
                    )}
                    {entity.evidence && (
                      <div className="text-xs">
                        <span className="text-gray-500">Evidence:</span>{" "}
                        <span className="text-gray-700">{entity.evidence}</span>
                      </div>
                    )}
                    {entity.documents_appearing_in && entity.documents_appearing_in.length > 0 && (
                      <div className="text-xs">
                        <span className="text-gray-500">Documents:</span>
                        <div className="mt-1 flex flex-wrap gap-1">
                          {entity.documents_appearing_in.slice(0, 3).map((doc, i) => (
                            <Badge key={i} variant="outline" className="text-[10px]">
                              <FileText className="w-3 h-3 mr-1" />
                              {typeof doc === 'string' ? doc.slice(0, 20) : 'doc'}...
                            </Badge>
                          ))}
                          {entity.documents_appearing_in.length > 3 && (
                            <Badge variant="outline" className="text-[10px]">
                              +{entity.documents_appearing_in.length - 3} more
                            </Badge>
                          )}
                        </div>
                      </div>
                    )}
                  </motion.div>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};

// Main modal component
export function EntityMappingModal({
  isOpen,
  onClose,
  isRunning,
  progress = 0,
  result,
  ddId,
  onConfirmEntities,
  onModifyWithAI,
  onConfirmEntityMap,
}: EntityMappingModalProps) {
  const [activeTab, setActiveTab] = useState<"organogram" | "list">("organogram");
  const [conflictEntity, setConflictEntity] = useState<OrganogramEntity | null>(null);
  const [confirmations, setConfirmations] = useState<Record<string, string>>({});
  const [isFullscreen, setIsFullscreen] = useState(false);

  // AI modification state
  const [aiInstruction, setAiInstruction] = useState("");
  const [isModifying, setIsModifying] = useState(false);
  const [modificationResult, setModificationResult] = useState<{
    explanation: string;
    changes_made: Array<{ entity_name: string; change_type: string; description: string }>;
  } | null>(null);
  const [workingEntityMap, setWorkingEntityMap] = useState<EntityMapEntry[] | null>(null);
  const [isConfirming, setIsConfirming] = useState(false);
  const [isConfirmed, setIsConfirmed] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Initialize working entity map from result
  React.useEffect(() => {
    if (result?.entity_map && !workingEntityMap) {
      setWorkingEntityMap(result.entity_map);
    }
  }, [result?.entity_map]);

  // Get the entity map to display (working copy or original)
  const displayEntityMap = workingEntityMap || result?.entity_map || [];

  // Convert result to organogram data
  const organogramData: OrganogramData | null = useMemo(() => {
    if (!result) return null;

    // Use working entity map if available
    const entityMapToUse = displayEntityMap;

    // Convert EntityMapEntry to OrganogramEntity
    const entities: OrganogramEntity[] = entityMapToUse.map((entry, idx) => ({
      id: entry.id || `entity-${idx}`,
      entity_name: entry.entity_name,
      registration_number: entry.registration_number,
      relationship_to_target: entry.relationship_to_target,
      relationship_detail: entry.relationship_detail,
      ownership_percentage: entry.ownership_percentage,
      confidence: entry.confidence,
      documents_appearing_in: entry.documents_appearing_in || [],
      evidence: entry.evidence,
      requires_human_confirmation: entry.requires_human_confirmation,
      human_confirmed: entry.human_confirmed,
      has_conflict: entry.has_conflict || entry.requires_human_confirmation,
      conflict_details: entry.conflict_details,
      is_individual: entry.relationship_to_target === "key_individual" ||
                     entry.relationship_to_target === "director" ||
                     entry.relationship_to_target === "officer",
    }));

    return {
      target_entity: {
        name: result.target_entity?.name || "Target Entity",
        registration_number: result.target_entity?.registration_number,
        transaction_type: result.target_entity?.transaction_type,
        deal_structure: result.target_entity?.deal_structure,
      },
      client_entity: result.client_entity,
      shareholders: result.shareholders,
      entities,
    };
  }, [result, displayEntityMap]);

  // Handle AI modification request
  const handleAIModify = async () => {
    if (!aiInstruction.trim() || !onModifyWithAI || isModifying) return;

    setIsModifying(true);
    setModificationResult(null);

    try {
      const response = await onModifyWithAI(aiInstruction, displayEntityMap);

      if (response.success) {
        setWorkingEntityMap(response.entity_map);
        setModificationResult({
          explanation: response.explanation,
          changes_made: response.changes_made,
        });
        setAiInstruction("");
        setHasUnsavedChanges(true);
        setIsConfirmed(false);
      } else {
        setModificationResult({
          explanation: response.error || "Failed to apply changes",
          changes_made: [],
        });
      }
    } catch (error) {
      console.error("AI modification failed:", error);
      setModificationResult({
        explanation: `Error: ${error instanceof Error ? error.message : "Unknown error"}`,
        changes_made: [],
      });
    } finally {
      setIsModifying(false);
    }
  };

  // Handle confirm and save
  const handleConfirmAndSave = async () => {
    if (!onConfirmEntityMap || isConfirming || !displayEntityMap.length) return;

    setIsConfirming(true);

    try {
      const response = await onConfirmEntityMap(displayEntityMap);

      if (response.success) {
        setIsConfirmed(true);
        setHasUnsavedChanges(false);
        setModificationResult({
          explanation: `Entity map confirmed and saved (${response.confirmed_count} entities)`,
          changes_made: [],
        });
      } else {
        setModificationResult({
          explanation: "Failed to save entity map",
          changes_made: [],
        });
      }
    } catch (error) {
      console.error("Confirm failed:", error);
      setModificationResult({
        explanation: `Error saving: ${error instanceof Error ? error.message : "Unknown error"}`,
        changes_made: [],
      });
    } finally {
      setIsConfirming(false);
    }
  };

  const handleResolveConflict = (entityId: string) => {
    const entity = organogramData?.entities.find(e => e.id === entityId);
    if (entity) {
      setConflictEntity(entity);
    }
  };

  const handleConfirmConflict = (entityId: string, relationship: string, details?: string) => {
    setConfirmations(prev => ({
      ...prev,
      [entityId]: relationship,
    }));
    // TODO: Send confirmation to backend
  };

  const handleDone = () => {
    if (Object.keys(confirmations).length > 0 && onConfirmEntities) {
      onConfirmEntities(confirmations);
    }
    onClose();
  };

  // Count entities needing confirmation
  const needsConfirmationCount = result?.entity_map.filter(
    e => e.requires_human_confirmation && !confirmations[e.id || e.entity_name]
  ).length || 0;

  return (
    <>
      <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
        <DialogContent
          className={cn(
            "overflow-hidden flex flex-col p-0 transition-all duration-200",
            isFullscreen
              ? "!max-w-[100vw] !w-[100vw] !h-[100vh] !max-h-[100vh] !rounded-none !top-0 !left-0 !translate-x-0 !translate-y-0"
              : "max-w-5xl max-h-[90vh]"
          )}
        >
          {/* Header */}
          <div className="px-6 py-4 border-b flex items-center justify-between">
            <DialogHeader className="flex-1">
              <DialogTitle className="flex items-center gap-2">
                <Network className="w-5 h-5 text-indigo-600" />
                Entity Mapping
              </DialogTitle>
              <DialogDescription>
                {isRunning
                  ? "Analyzing documents to map entities and their relationships..."
                  : result
                  ? `Found ${result.entity_map.length} entities across ${result.total_documents_processed} documents`
                  : "Map entities across documents to identify relationships"}
              </DialogDescription>
            </DialogHeader>
            {/* Fullscreen toggle */}
            <button
              onClick={() => setIsFullscreen(!isFullscreen)}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors mr-8"
              title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
            >
              {isFullscreen ? (
                <Minimize2 className="w-5 h-5 text-gray-500" />
              ) : (
                <Maximize2 className="w-5 h-5 text-gray-500" />
              )}
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-hidden">
            {/* Progress state */}
            {isRunning && (
              <div className="h-full flex items-center justify-center p-8">
                <div className="text-center">
                  <Loader2 className="w-12 h-12 animate-spin text-indigo-600 mx-auto mb-4" />
                  <div className="text-lg font-medium mb-2">Mapping Entities...</div>
                  <div className="text-sm text-gray-500 mb-4">
                    Extracting and matching entities across documents
                  </div>
                  {progress > 0 && (
                    <div className="w-64 mx-auto">
                      <Progress value={progress} className="h-2" />
                      <div className="text-xs text-gray-500 text-center mt-1">{progress}% complete</div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Results state */}
            {!isRunning && result && organogramData && (
              <div className="h-full flex flex-col">
                {/* Summary bar */}
                <div className="px-6 py-3 bg-gray-50 border-b flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
                        <span className="text-sm font-bold text-blue-600">{result.summary?.total_unique_entities ?? 0}</span>
                      </div>
                      <span className="text-sm text-gray-600">Entities</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center">
                        <span className="text-sm font-bold text-green-600">{result.summary?.target_subsidiaries ?? 0}</span>
                      </div>
                      <span className="text-sm text-gray-600">Subsidiaries</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-full bg-amber-100 flex items-center justify-center">
                        <span className="text-sm font-bold text-amber-600">{result.summary?.counterparties ?? 0}</span>
                      </div>
                      <span className="text-sm text-gray-600">Counterparties</span>
                    </div>
                    {needsConfirmationCount > 0 && (
                      <div className="flex items-center gap-2 ml-4 pl-4 border-l">
                        <AlertTriangle className="w-4 h-4 text-amber-500" />
                        <span className="text-sm text-amber-600 font-medium">
                          {needsConfirmationCount} need review
                        </span>
                      </div>
                    )}
                  </div>

                  {/* View toggle */}
                  <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as "organogram" | "list")}>
                    <TabsList className="h-8">
                      <TabsTrigger value="organogram" className="text-xs px-3 h-7">
                        <GitBranch className="w-3 h-3 mr-1" />
                        Organogram
                      </TabsTrigger>
                      <TabsTrigger value="list" className="text-xs px-3 h-7">
                        <List className="w-3 h-3 mr-1" />
                        List
                      </TabsTrigger>
                    </TabsList>
                  </Tabs>
                </div>

                {/* Main content area */}
                <div
                  className="flex-1 overflow-hidden"
                  style={{ minHeight: isFullscreen ? "calc(100vh - 200px)" : "500px" }}
                >
                  {activeTab === "organogram" ? (
                    <EntityOrganogram
                      data={organogramData}
                      onEntityClick={(entity) => {
                        if (entity.has_conflict) {
                          setConflictEntity(entity);
                        }
                      }}
                      onResolveConflict={handleResolveConflict}
                      className="h-full w-full"
                      isFullscreen={isFullscreen}
                    />
                  ) : (
                    <div className="p-6 h-full overflow-auto">
                      <EntityListView
                        entities={result.entity_map}
                        onEntityClick={(entity) => {
                          if (entity.requires_human_confirmation) {
                            const orgEntity = organogramData.entities.find(e => e.entity_name === entity.entity_name);
                            if (orgEntity) setConflictEntity(orgEntity);
                          }
                        }}
                      />
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* AI Modification Panel & Footer */}
          {!isRunning && result && (
            <div className="border-t bg-gray-50">
              {/* AI Modification Result */}
              <AnimatePresence>
                {modificationResult && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden"
                  >
                    <div className={cn(
                      "px-6 py-3 border-b",
                      modificationResult.changes_made.length > 0 ? "bg-green-50" : "bg-blue-50"
                    )}>
                      <div className="flex items-start gap-2">
                        <Sparkles className={cn(
                          "w-4 h-4 mt-0.5",
                          modificationResult.changes_made.length > 0 ? "text-green-600" : "text-blue-600"
                        )} />
                        <div className="flex-1">
                          <p className="text-sm text-gray-700">{modificationResult.explanation}</p>
                          {modificationResult.changes_made.length > 0 && (
                            <div className="mt-2 space-y-1">
                              {modificationResult.changes_made.map((change, idx) => (
                                <div key={idx} className="flex items-center gap-2 text-xs">
                                  <Badge variant="outline" className={cn(
                                    "text-[10px]",
                                    change.change_type === "removed" ? "border-red-300 text-red-700" :
                                    change.change_type === "added" ? "border-green-300 text-green-700" :
                                    "border-blue-300 text-blue-700"
                                  )}>
                                    {change.change_type}
                                  </Badge>
                                  <span className="font-medium">{change.entity_name}</span>
                                  <span className="text-gray-500">- {change.description}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                        <button
                          onClick={() => setModificationResult(null)}
                          className="p-1 hover:bg-white/50 rounded"
                        >
                          <X className="w-3 h-3 text-gray-400" />
                        </button>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* AI Instruction Input */}
              {onModifyWithAI && (
                <div className="px-6 py-3 border-b">
                  <div className="flex items-start gap-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <Sparkles className="w-4 h-4 text-indigo-600" />
                        <span className="text-sm font-medium text-gray-700">Ask AI to modify the entity map</span>
                      </div>
                      <div className="flex gap-2">
                        <Textarea
                          placeholder="E.g., 'Remove G. Pietersen - they are just a signatory, not a counterparty' or 'Change Standard Bank relationship to lender'"
                          value={aiInstruction}
                          onChange={(e) => setAiInstruction(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" && !e.shiftKey) {
                              e.preventDefault();
                              handleAIModify();
                            }
                          }}
                          className="flex-1 min-h-[60px] text-sm resize-none"
                          disabled={isModifying}
                        />
                        <Button
                          onClick={handleAIModify}
                          disabled={!aiInstruction.trim() || isModifying}
                          className="self-end bg-indigo-600 hover:bg-indigo-700"
                        >
                          {isModifying ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Send className="w-4 h-4" />
                          )}
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Footer with status and actions */}
              <DialogFooter className="px-6 py-4">
                <div className="flex items-center justify-between w-full">
                  <div className="flex items-center gap-4">
                    <div className="text-xs text-gray-500">
                      {displayEntityMap.length} entities • {result.total_documents_processed} documents
                    </div>
                    {hasUnsavedChanges && !isConfirmed && (
                      <Badge variant="outline" className="text-amber-600 border-amber-300">
                        Unsaved changes
                      </Badge>
                    )}
                    {isConfirmed && (
                      <Badge className="bg-green-100 text-green-700 border-green-300">
                        <CheckCircle2 className="w-3 h-3 mr-1" />
                        Confirmed
                      </Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {needsConfirmationCount > 0 && (
                      <span className="text-sm text-amber-600">
                        {needsConfirmationCount} need review
                      </span>
                    )}
                    <Button variant="outline" onClick={onClose}>
                      Close
                    </Button>
                    {onConfirmEntityMap && (
                      <Button
                        onClick={handleConfirmAndSave}
                        disabled={isConfirming || isConfirmed}
                        className={cn(
                          isConfirmed
                            ? "bg-green-600 hover:bg-green-700"
                            : "bg-indigo-600 hover:bg-indigo-700"
                        )}
                      >
                        {isConfirming ? (
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        ) : isConfirmed ? (
                          <CheckCircle2 className="w-4 h-4 mr-2" />
                        ) : (
                          <Save className="w-4 h-4 mr-2" />
                        )}
                        {isConfirmed ? "Saved" : "Confirm & Save"}
                      </Button>
                    )}
                  </div>
                </div>
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Conflict resolution dialog */}
      <ConflictResolutionDialog
        entity={conflictEntity}
        onClose={() => setConflictEntity(null)}
        onConfirm={handleConfirmConflict}
      />
    </>
  );
}

export default EntityMappingModal;
