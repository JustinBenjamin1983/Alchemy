/**
 * Entity Mapping Modal
 *
 * Shows:
 * 1. Progress while entity mapping is running
 * 2. Results after completion (entity map, relationships, summary)
 * 3. Human confirmation section for unknown entities (Checkpoint A.5)
 */
import React, { useState } from "react";
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
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Network,
  Building2,
  Users,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  ChevronDown,
  ChevronRight,
  FileText,
  HelpCircle,
  X,
  Building,
  Briefcase,
  UserCheck,
  Link2,
} from "lucide-react";
import { cn } from "@/lib/utils";

// Types based on backend response
export interface EntityMapEntry {
  entity_name: string;
  registration_number?: string;
  relationship_to_target: string;
  relationship_detail?: string;
  confidence: number;
  documents_appearing_in: string[];
  evidence?: string;
  requires_human_confirmation?: boolean;
}

export interface EntityMappingSummary {
  total_unique_entities: number;
  entities_needing_confirmation: number;
  target_subsidiaries: number;
  counterparties: number;
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
  };
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
  onConfirmEntities?: (confirmations: Record<string, string>) => void;
}

// Relationship type options for human confirmation
const RELATIONSHIP_OPTIONS = [
  { value: "related_party", label: "Related Party", description: "Supplier, customer, or other related entity" },
  { value: "subsidiary", label: "Subsidiary", description: "Owned by the target company" },
  { value: "parent", label: "Parent/Holding", description: "Owns shares in the target company" },
  { value: "counterparty", label: "Counterparty", description: "Contractual partner (not related)" },
  { value: "exclude", label: "Exclude", description: "Documents uploaded in error" },
];

// Get icon for relationship type
function getRelationshipIcon(relationship: string) {
  switch (relationship) {
    case "target":
      return <Building2 className="w-4 h-4 text-blue-600" />;
    case "parent":
      return <Building className="w-4 h-4 text-purple-600" />;
    case "subsidiary":
      return <Briefcase className="w-4 h-4 text-green-600" />;
    case "related_party":
      return <Link2 className="w-4 h-4 text-amber-600" />;
    case "counterparty":
      return <Users className="w-4 h-4 text-cyan-600" />;
    case "shareholder":
      return <UserCheck className="w-4 h-4 text-indigo-600" />;
    case "unknown":
      return <HelpCircle className="w-4 h-4 text-red-500" />;
    default:
      return <Building2 className="w-4 h-4 text-gray-500" />;
  }
}

// Get badge color for relationship type
function getRelationshipBadgeClass(relationship: string): string {
  switch (relationship) {
    case "target":
      return "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300";
    case "parent":
      return "bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300";
    case "subsidiary":
      return "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300";
    case "related_party":
      return "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300";
    case "counterparty":
      return "bg-cyan-100 text-cyan-800 dark:bg-cyan-900/40 dark:text-cyan-300";
    case "shareholder":
      return "bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-300";
    case "unknown":
      return "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300";
    default:
      return "bg-gray-100 text-gray-800 dark:bg-gray-900/40 dark:text-gray-300";
  }
}

// Format relationship type for display
function formatRelationship(relationship: string): string {
  return relationship
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

// Entity card component for results
function EntityCard({
  entity,
  isExpanded,
  onToggle,
  needsConfirmation,
  selectedRelationship,
  onRelationshipChange,
  customRelationship,
  onCustomRelationshipChange,
}: {
  entity: EntityMapEntry;
  isExpanded: boolean;
  onToggle: () => void;
  needsConfirmation?: boolean;
  selectedRelationship?: string;
  onRelationshipChange?: (value: string) => void;
  customRelationship?: string;
  onCustomRelationshipChange?: (value: string) => void;
}) {
  const confidenceColor =
    entity.confidence >= 0.8
      ? "text-green-600"
      : entity.confidence >= 0.5
      ? "text-amber-600"
      : "text-red-600";

  return (
    <div
      className={cn(
        "border rounded-lg overflow-hidden transition-all",
        needsConfirmation
          ? "border-amber-300 bg-amber-50/50 dark:border-amber-700 dark:bg-amber-900/10"
          : "border-gray-200 dark:border-gray-700"
      )}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between p-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50"
        onClick={onToggle}
      >
        <div className="flex items-center gap-3">
          {getRelationshipIcon(entity.relationship_to_target)}
          <div>
            <div className="font-medium text-sm">{entity.entity_name}</div>
            {entity.registration_number && (
              <div className="text-xs text-gray-500">{entity.registration_number}</div>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge className={cn("text-xs", getRelationshipBadgeClass(entity.relationship_to_target))}>
            {formatRelationship(entity.relationship_to_target)}
          </Badge>
          <span className={cn("text-xs font-medium", confidenceColor)}>
            {Math.round(entity.confidence * 100)}%
          </span>
          <Badge variant="secondary" className="text-xs">
            {entity.documents_appearing_in.length} docs
          </Badge>
          {isExpanded ? (
            <ChevronDown className="w-4 h-4 text-gray-400" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-400" />
          )}
        </div>
      </div>

      {/* Expanded content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="border-t border-gray-200 dark:border-gray-700"
          >
            <div className="p-3 space-y-3">
              {/* Relationship detail */}
              {entity.relationship_detail && (
                <div>
                  <div className="text-xs font-medium text-gray-500 mb-1">Relationship Detail</div>
                  <div className="text-sm">{entity.relationship_detail}</div>
                </div>
              )}

              {/* Evidence */}
              {entity.evidence && (
                <div>
                  <div className="text-xs font-medium text-gray-500 mb-1">Evidence</div>
                  <div className="text-sm text-gray-600 dark:text-gray-400 italic">
                    "{entity.evidence}"
                  </div>
                </div>
              )}

              {/* Documents */}
              <div>
                <div className="text-xs font-medium text-gray-500 mb-1">
                  Appears in {entity.documents_appearing_in.length} document(s)
                </div>
                <div className="flex flex-wrap gap-1">
                  {entity.documents_appearing_in.slice(0, 5).map((doc, i) => (
                    <Badge key={i} variant="outline" className="text-xs">
                      <FileText className="w-3 h-3 mr-1" />
                      {doc.length > 30 ? doc.slice(0, 30) + "..." : doc}
                    </Badge>
                  ))}
                  {entity.documents_appearing_in.length > 5 && (
                    <Badge variant="outline" className="text-xs">
                      +{entity.documents_appearing_in.length - 5} more
                    </Badge>
                  )}
                </div>
              </div>

              {/* Human confirmation section */}
              {needsConfirmation && onRelationshipChange && (
                <div className="pt-3 border-t border-amber-200 dark:border-amber-800">
                  <div className="text-xs font-medium text-amber-700 dark:text-amber-300 mb-2">
                    Please confirm the relationship:
                  </div>
                  <RadioGroup
                    value={selectedRelationship}
                    onValueChange={onRelationshipChange}
                    className="space-y-2"
                  >
                    {RELATIONSHIP_OPTIONS.map((option) => (
                      <div key={option.value} className="flex items-center space-x-2">
                        <RadioGroupItem value={option.value} id={`${entity.entity_name}-${option.value}`} />
                        <Label
                          htmlFor={`${entity.entity_name}-${option.value}`}
                          className="text-sm cursor-pointer"
                        >
                          {option.label}
                          <span className="text-xs text-gray-500 ml-1">({option.description})</span>
                        </Label>
                      </div>
                    ))}
                    <div className="flex items-center space-x-2">
                      <RadioGroupItem value="other" id={`${entity.entity_name}-other`} />
                      <Label htmlFor={`${entity.entity_name}-other`} className="text-sm cursor-pointer">
                        Other:
                      </Label>
                      <Input
                        placeholder="Specify relationship..."
                        value={customRelationship}
                        onChange={(e) => onCustomRelationshipChange?.(e.target.value)}
                        className="h-7 text-sm flex-1"
                        onClick={(e) => e.stopPropagation()}
                      />
                    </div>
                  </RadioGroup>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function EntityMappingModal({
  isOpen,
  onClose,
  isRunning,
  progress = 0,
  result,
  onConfirmEntities,
}: EntityMappingModalProps) {
  const [expandedEntities, setExpandedEntities] = useState<Set<string>>(new Set());
  const [confirmations, setConfirmations] = useState<Record<string, string>>({});
  const [customRelationships, setCustomRelationships] = useState<Record<string, string>>({});
  const [showAllEntities, setShowAllEntities] = useState(false);

  // Get entities needing confirmation
  const entitiesNeedingConfirmation = result?.entity_map.filter(
    (e) => e.requires_human_confirmation || e.relationship_to_target === "unknown"
  ) || [];

  // Get confirmed entities
  const confirmedEntities = result?.entity_map.filter(
    (e) => !e.requires_human_confirmation && e.relationship_to_target !== "unknown"
  ) || [];

  const toggleEntity = (entityName: string) => {
    const newExpanded = new Set(expandedEntities);
    if (newExpanded.has(entityName)) {
      newExpanded.delete(entityName);
    } else {
      newExpanded.add(entityName);
    }
    setExpandedEntities(newExpanded);
  };

  const handleConfirmationChange = (entityName: string, value: string) => {
    setConfirmations((prev) => ({ ...prev, [entityName]: value }));
  };

  const handleCustomRelationshipChange = (entityName: string, value: string) => {
    setCustomRelationships((prev) => ({ ...prev, [entityName]: value }));
  };

  const handleConfirmAll = () => {
    if (onConfirmEntities) {
      const finalConfirmations: Record<string, string> = {};
      for (const entity of entitiesNeedingConfirmation) {
        const selected = confirmations[entity.entity_name];
        if (selected === "other") {
          finalConfirmations[entity.entity_name] = customRelationships[entity.entity_name] || "unknown";
        } else if (selected) {
          finalConfirmations[entity.entity_name] = selected;
        }
      }
      onConfirmEntities(finalConfirmations);
    }
    onClose();
  };

  const allConfirmed = entitiesNeedingConfirmation.every(
    (e) => confirmations[e.entity_name] && confirmations[e.entity_name] !== ""
  );

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-3xl max-h-[85vh] overflow-hidden flex flex-col">
        <DialogHeader>
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

        <div className="flex-1 overflow-y-auto py-4 space-y-4">
          {/* Progress state */}
          {isRunning && (
            <div className="space-y-4">
              <div className="flex items-center justify-center py-8">
                <div className="text-center">
                  <Loader2 className="w-12 h-12 animate-spin text-indigo-600 mx-auto mb-4" />
                  <div className="text-lg font-medium mb-2">Mapping Entities...</div>
                  <div className="text-sm text-gray-500">
                    Extracting and matching entities across documents
                  </div>
                </div>
              </div>
              {progress > 0 && (
                <div className="px-4">
                  <Progress value={progress} className="h-2" />
                  <div className="text-xs text-gray-500 text-center mt-1">{progress}% complete</div>
                </div>
              )}
            </div>
          )}

          {/* Results state */}
          {!isRunning && result && (
            <>
              {/* Summary cards */}
              <div className="grid grid-cols-4 gap-3">
                <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-blue-600">{result.summary.total_unique_entities}</div>
                  <div className="text-xs text-blue-600/80">Total Entities</div>
                </div>
                <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-green-600">{result.summary.target_subsidiaries}</div>
                  <div className="text-xs text-green-600/80">Subsidiaries</div>
                </div>
                <div className="bg-cyan-50 dark:bg-cyan-900/20 rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-cyan-600">{result.summary.counterparties}</div>
                  <div className="text-xs text-cyan-600/80">Counterparties</div>
                </div>
                <div className="bg-amber-50 dark:bg-amber-900/20 rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-amber-600">{result.summary.entities_needing_confirmation}</div>
                  <div className="text-xs text-amber-600/80">Need Review</div>
                </div>
              </div>

              {/* Target entity info */}
              {result.target_entity && (
                <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
                  <div className="flex items-center gap-2 mb-1">
                    <Building2 className="w-4 h-4 text-blue-600" />
                    <span className="text-sm font-medium text-blue-800 dark:text-blue-200">Target Entity</span>
                  </div>
                  <div className="text-lg font-semibold">{result.target_entity.name}</div>
                  {result.target_entity.registration_number && (
                    <div className="text-sm text-gray-600">Reg: {result.target_entity.registration_number}</div>
                  )}
                </div>
              )}

              {/* Checkpoint warning */}
              {result.checkpoint_recommended && (
                <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-300 dark:border-amber-700 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <div className="font-medium text-amber-800 dark:text-amber-200">
                        Human Confirmation Required
                      </div>
                      <div className="text-sm text-amber-700 dark:text-amber-300 mt-1">
                        {result.checkpoint_reason ||
                          `${entitiesNeedingConfirmation.length} entities couldn't be confidently linked to the target company. Please review and confirm their relationships.`}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Entities needing confirmation */}
              {entitiesNeedingConfirmation.length > 0 && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-medium text-amber-700 dark:text-amber-300 flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4" />
                      Entities Requiring Review ({entitiesNeedingConfirmation.length})
                    </h3>
                  </div>
                  <div className="space-y-2">
                    {entitiesNeedingConfirmation.map((entity) => (
                      <EntityCard
                        key={entity.entity_name}
                        entity={entity}
                        isExpanded={expandedEntities.has(entity.entity_name)}
                        onToggle={() => toggleEntity(entity.entity_name)}
                        needsConfirmation
                        selectedRelationship={confirmations[entity.entity_name]}
                        onRelationshipChange={(value) => handleConfirmationChange(entity.entity_name, value)}
                        customRelationship={customRelationships[entity.entity_name]}
                        onCustomRelationshipChange={(value) => handleCustomRelationshipChange(entity.entity_name, value)}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Confirmed entities */}
              {confirmedEntities.length > 0 && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-medium text-green-700 dark:text-green-300 flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4" />
                      Confirmed Entities ({confirmedEntities.length})
                    </h3>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setShowAllEntities(!showAllEntities)}
                      className="text-xs"
                    >
                      {showAllEntities ? "Hide" : "Show All"}
                    </Button>
                  </div>
                  {showAllEntities && (
                    <div className="space-y-2">
                      {confirmedEntities.map((entity) => (
                        <EntityCard
                          key={entity.entity_name}
                          entity={entity}
                          isExpanded={expandedEntities.has(entity.entity_name)}
                          onToggle={() => toggleEntity(entity.entity_name)}
                        />
                      ))}
                    </div>
                  )}
                  {!showAllEntities && (
                    <div className="text-sm text-gray-500 italic">
                      {confirmedEntities.length} entities automatically mapped. Click "Show All" to view.
                    </div>
                  )}
                </div>
              )}

              {/* Cost info */}
              {result.cost && (
                <div className="text-xs text-gray-500 text-right">
                  Cost: R{result.cost.total_cost.toFixed(2)} | {result.cost.total_tokens.toLocaleString()} tokens
                </div>
              )}
            </>
          )}
        </div>

        <DialogFooter className="border-t pt-4">
          {isRunning ? (
            <Button variant="outline" onClick={onClose}>
              Run in Background
            </Button>
          ) : result && entitiesNeedingConfirmation.length > 0 ? (
            <>
              <Button variant="outline" onClick={onClose}>
                Skip Review
              </Button>
              <Button
                onClick={handleConfirmAll}
                disabled={!allConfirmed}
                className="bg-indigo-600 hover:bg-indigo-700"
              >
                <CheckCircle2 className="w-4 h-4 mr-2" />
                Confirm & Continue
              </Button>
            </>
          ) : (
            <Button onClick={onClose}>
              <CheckCircle2 className="w-4 h-4 mr-2" />
              Done
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
