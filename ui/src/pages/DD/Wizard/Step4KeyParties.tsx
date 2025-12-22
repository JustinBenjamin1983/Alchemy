import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { X, Plus, Info } from "lucide-react";
import { useState, KeyboardEvent } from "react";
import {
  DDProjectSetup,
  STEP4_CONFIG,
  Step4FieldDefinition,
  Step4FieldType,
  Shareholder,
} from "./types";

// Format number string as South African Rand currency
function formatCurrency(value: string): string {
  if (!value) return "";
  const cleaned = value.replace(/[^\d.]/g, "");
  if (!cleaned) return "";
  const num = parseFloat(cleaned);
  if (isNaN(num)) return value;
  return `R${Math.round(num).toLocaleString("en-ZA")}`;
}

interface Step4Props {
  data: DDProjectSetup;
  onChange: (updates: Partial<DDProjectSetup>) => void;
}

// =============================================================================
// FIELD STORAGE: Maps field IDs to data storage keys
// =============================================================================

interface FieldData {
  tags?: string[];
  parties?: Array<{ name: string; role: string }>;
  lenders?: Array<{ name: string; description: string; facilityAmount: string }>;
  counterparties?: Array<{ name: string; description: string; exposure: string }>;
  beePartners?: Array<{ name: string; beeOwnership: number | null; beeLevel: string }>;
}

// Get the current value for a field from the data object
function getFieldValue(data: DDProjectSetup, fieldId: string): FieldData {
  // Map field IDs to data properties - some fields share storage, others are unique
  switch (fieldId) {
    // Tag fields
    case "keyIndividuals":
    case "keyExecutives":
    case "keyPersonnel":
    case "management":
      return { tags: data.keyIndividuals };
    case "regulators":
      return { tags: data.keyRegulators };
    case "verificationAgency":
    case "advisors":
    case "technologyProviders":
    case "serviceProviders":
    case "criticalSuppliers":
    case "competitors":
    case "suppliers":
    case "customers":
      return { tags: data.keySuppliers };

    // Party role fields (name + role)
    case "other":
    case "sellers":
    case "beeTrustSPV":
    case "communities":
    case "landowners":
    case "unions":
    case "affectedEmployees":
    case "ipOwners":
    case "mergingParties":
    case "governmentAuthority":
    case "targetInstitution":
    case "potentialInvestors":
    case "borrowerGroup":
    case "seller":
      return { parties: data.keyOther };

    // Lender fields (name + description + amount)
    case "lenders":
    case "financiers":
    case "funders":
    case "existingLenders":
    case "guarantors":
    case "securedCreditors":
    case "unsecuredCreditors":
    case "underwriters":
    case "fundingProviders":
      return { lenders: data.keyLenders };

    // Counterparty fields (name + description + exposure)
    case "contractors":
    case "offtakers":
    case "tenants":
    case "epcContractor":
    case "omProvider":
    case "constructionContractor":
    case "facilitiesManager":
    case "existingShareholders":
    case "cornerstoneInvestors":
    case "coInvestors":
    case "licensees":
    case "keyClients":
      return { counterparties: data.keyCustomers };

    // BEE partner field
    case "beePartners":
      // For now, store as parties with role containing BEE info
      return { parties: data.keyOther };

    default:
      return { tags: [] };
  }
}

// =============================================================================
// TAG INPUT COMPONENT (Simple list of strings)
// =============================================================================

interface TagInputProps {
  field: Step4FieldDefinition;
  tags: string[];
  onChange: (tags: string[]) => void;
}

function TagInput({ field, tags, onChange }: TagInputProps) {
  const [inputValue, setInputValue] = useState("");

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && inputValue.trim()) {
      e.preventDefault();
      if (!tags.includes(inputValue.trim())) {
        onChange([...tags, inputValue.trim()]);
      }
      setInputValue("");
    }
  };

  const removeTag = (tagToRemove: string) => {
    onChange(tags.filter((tag) => tag !== tagToRemove));
  };

  const addSuggestion = (suggestion: string) => {
    if (!tags.includes(suggestion)) {
      onChange([...tags, suggestion]);
    }
  };

  return (
    <div className="space-y-1">
      <Label className="text-xs font-medium">{field.label}</Label>
      {field.description && (
        <p className="text-xs text-muted-foreground">{field.description}</p>
      )}
      <Input
        className="h-8 text-sm"
        placeholder={field.placeholder}
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyDown={handleKeyDown}
      />
      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pt-1">
          {tags.map((tag) => (
            <Badge
              key={tag}
              variant="secondary"
              className="flex items-center gap-1 text-xs py-0.5"
            >
              {tag}
              <X
                className="h-3 w-3 cursor-pointer hover:text-destructive"
                onClick={() => removeTag(tag)}
              />
            </Badge>
          ))}
        </div>
      )}
      {field.suggestions && field.suggestions.length > 0 && (
        <div className="flex flex-wrap gap-1 pt-1">
          <span className="text-xs text-muted-foreground">Suggestions:</span>
          {field.suggestions
            .filter((s) => !tags.includes(s))
            .map((suggestion) => (
              <Badge
                key={suggestion}
                variant="outline"
                className="cursor-pointer hover:bg-gray-100 text-xs py-0"
                onClick={() => addSuggestion(suggestion)}
              >
                + {suggestion}
              </Badge>
            ))}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// PARTY ROLE INPUT COMPONENT (Name + Role)
// =============================================================================

interface PartyRoleEntry {
  name: string;
  role: string;
}

interface PartyRoleInputProps {
  field: Step4FieldDefinition;
  parties: PartyRoleEntry[];
  onChange: (parties: PartyRoleEntry[]) => void;
}

function PartyRoleInput({ field, parties, onChange }: PartyRoleInputProps) {
  const [nameInput, setNameInput] = useState("");
  const [roleInput, setRoleInput] = useState("");

  const canAdd = nameInput.trim().length > 0;

  const handleAdd = () => {
    if (canAdd) {
      onChange([...parties, { name: nameInput.trim(), role: roleInput.trim() }]);
      setNameInput("");
      setRoleInput("");
    }
  };

  const removeParty = (index: number) => {
    onChange(parties.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-2">
      <Label className="text-xs font-medium">{field.label}</Label>
      {field.description && (
        <p className="text-xs text-muted-foreground">{field.description}</p>
      )}
      <div className="flex gap-2 items-center">
        <div className="flex-1">
          <Input
            className="h-8 text-sm"
            placeholder={field.placeholder}
            value={nameInput}
            onChange={(e) => setNameInput(e.target.value)}
          />
        </div>
        <div className="flex-1">
          <Input
            className="h-8 text-sm"
            placeholder="Role / Description"
            value={roleInput}
            onChange={(e) => setRoleInput(e.target.value)}
          />
        </div>
        <button
          type="button"
          onClick={handleAdd}
          disabled={!canAdd}
          className={`h-8 w-8 flex items-center justify-center rounded border flex-shrink-0 ${
            canAdd
              ? "bg-alchemyPrimaryOrange text-white border-alchemyPrimaryOrange hover:bg-orange-600"
              : "bg-gray-100 text-gray-400 border-gray-200 cursor-not-allowed"
          }`}
        >
          <Plus className="h-4 w-4" />
        </button>
      </div>
      {parties.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pt-1">
          {parties.map((party, index) => (
            <Badge
              key={index}
              variant="secondary"
              className="flex items-center gap-1 text-xs py-0.5"
            >
              <span className="font-medium">{party.name}</span>
              {party.role && (
                <span className="text-muted-foreground">({party.role})</span>
              )}
              <X
                className="h-3 w-3 cursor-pointer hover:text-destructive ml-1"
                onClick={() => removeParty(index)}
              />
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// LENDER INPUT COMPONENT (Name + Description + Amount)
// =============================================================================

interface LenderEntry {
  name: string;
  description: string;
  facilityAmount: string;
}

interface LenderInputProps {
  field: Step4FieldDefinition;
  lenders: LenderEntry[];
  onChange: (lenders: LenderEntry[]) => void;
}

function LenderInput({ field, lenders, onChange }: LenderInputProps) {
  const [nameInput, setNameInput] = useState("");
  const [descriptionInput, setDescriptionInput] = useState("");
  const [amountInput, setAmountInput] = useState("");

  const canAdd = nameInput.trim().length > 0;

  const handleAdd = () => {
    if (canAdd) {
      onChange([
        ...lenders,
        {
          name: nameInput.trim(),
          description: descriptionInput.trim(),
          facilityAmount: formatCurrency(amountInput),
        },
      ]);
      setNameInput("");
      setDescriptionInput("");
      setAmountInput("");
    }
  };

  const handleAmountBlur = () => {
    setAmountInput(formatCurrency(amountInput));
  };

  const removeLender = (index: number) => {
    onChange(lenders.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-2">
      <Label className="text-xs font-medium">{field.label}</Label>
      {field.description && (
        <p className="text-xs text-muted-foreground">{field.description}</p>
      )}
      <div className="flex gap-2 items-center">
        <div className="flex-[2]">
          <Input
            className="h-8 text-sm"
            placeholder={field.placeholder}
            value={nameInput}
            onChange={(e) => setNameInput(e.target.value)}
          />
        </div>
        <div className="flex-[2]">
          <Input
            className="h-8 text-sm"
            placeholder="Description / Role"
            value={descriptionInput}
            onChange={(e) => setDescriptionInput(e.target.value)}
          />
        </div>
        <div className="w-32">
          <Input
            className="h-8 text-sm"
            placeholder={field.amountPlaceholder || "e.g. R500m"}
            value={amountInput}
            onChange={(e) => setAmountInput(e.target.value)}
            onBlur={handleAmountBlur}
          />
        </div>
        <button
          type="button"
          onClick={handleAdd}
          disabled={!canAdd}
          className={`h-8 w-8 flex items-center justify-center rounded border flex-shrink-0 ${
            canAdd
              ? "bg-alchemyPrimaryOrange text-white border-alchemyPrimaryOrange hover:bg-orange-600"
              : "bg-gray-100 text-gray-400 border-gray-200 cursor-not-allowed"
          }`}
        >
          <Plus className="h-4 w-4" />
        </button>
      </div>
      {lenders.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pt-1">
          {lenders.map((lender, index) => (
            <Badge
              key={index}
              variant="secondary"
              className="flex items-center gap-1 text-xs py-0.5"
            >
              <span className="font-medium">{lender.name}</span>
              {lender.description && (
                <span className="text-muted-foreground">- {lender.description}</span>
              )}
              {lender.facilityAmount && (
                <span className="text-muted-foreground">({lender.facilityAmount})</span>
              )}
              <X
                className="h-3 w-3 cursor-pointer hover:text-destructive ml-1"
                onClick={() => removeLender(index)}
              />
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// COUNTERPARTY INPUT COMPONENT (Name + Description + Exposure)
// =============================================================================

interface CounterpartyEntry {
  name: string;
  description: string;
  exposure: string;
}

interface CounterpartyInputProps {
  field: Step4FieldDefinition;
  counterparties: CounterpartyEntry[];
  onChange: (counterparties: CounterpartyEntry[]) => void;
}

function CounterpartyInput({ field, counterparties, onChange }: CounterpartyInputProps) {
  const [nameInput, setNameInput] = useState("");
  const [descriptionInput, setDescriptionInput] = useState("");
  const [exposureInput, setExposureInput] = useState("");

  const canAdd = nameInput.trim().length > 0;

  const handleAdd = () => {
    if (canAdd) {
      onChange([
        ...counterparties,
        {
          name: nameInput.trim(),
          description: descriptionInput.trim(),
          exposure: formatCurrency(exposureInput),
        },
      ]);
      setNameInput("");
      setDescriptionInput("");
      setExposureInput("");
    }
  };

  const handleExposureBlur = () => {
    setExposureInput(formatCurrency(exposureInput));
  };

  const removeCounterparty = (index: number) => {
    onChange(counterparties.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-2">
      <Label className="text-xs font-medium">{field.label}</Label>
      {field.description && (
        <p className="text-xs text-muted-foreground">{field.description}</p>
      )}
      <div className="flex gap-2 items-center">
        <div className="flex-[2]">
          <Input
            className="h-8 text-sm"
            placeholder={field.placeholder}
            value={nameInput}
            onChange={(e) => setNameInput(e.target.value)}
          />
        </div>
        <div className="flex-[2]">
          <Input
            className="h-8 text-sm"
            placeholder="Description / Type"
            value={descriptionInput}
            onChange={(e) => setDescriptionInput(e.target.value)}
          />
        </div>
        <div className="w-32">
          <Input
            className="h-8 text-sm"
            placeholder={field.amountPlaceholder || "e.g. R100m"}
            value={exposureInput}
            onChange={(e) => setExposureInput(e.target.value)}
            onBlur={handleExposureBlur}
          />
        </div>
        <button
          type="button"
          onClick={handleAdd}
          disabled={!canAdd}
          className={`h-8 w-8 flex items-center justify-center rounded border flex-shrink-0 ${
            canAdd
              ? "bg-alchemyPrimaryOrange text-white border-alchemyPrimaryOrange hover:bg-orange-600"
              : "bg-gray-100 text-gray-400 border-gray-200 cursor-not-allowed"
          }`}
        >
          <Plus className="h-4 w-4" />
        </button>
      </div>
      {counterparties.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pt-1">
          {counterparties.map((counterparty, index) => (
            <Badge
              key={index}
              variant="secondary"
              className="flex items-center gap-1 text-xs py-0.5"
            >
              <span className="font-medium">{counterparty.name}</span>
              {counterparty.description && (
                <span className="text-muted-foreground">- {counterparty.description}</span>
              )}
              {counterparty.exposure && (
                <span className="text-muted-foreground">({counterparty.exposure})</span>
              )}
              <X
                className="h-3 w-3 cursor-pointer hover:text-destructive ml-1"
                onClick={() => removeCounterparty(index)}
              />
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// BEE PARTNER INPUT COMPONENT (Name + BEE Ownership % + BEE Level)
// =============================================================================

interface BEEPartnerEntry {
  name: string;
  beeOwnership: number | null;
  beeLevel: string;
}

interface BEEPartnerInputProps {
  field: Step4FieldDefinition;
  partners: BEEPartnerEntry[];
  onChange: (partners: BEEPartnerEntry[]) => void;
}

function BEEPartnerInput({ field, partners, onChange }: BEEPartnerInputProps) {
  const [nameInput, setNameInput] = useState("");
  const [ownershipInput, setOwnershipInput] = useState("");
  const [levelInput, setLevelInput] = useState("");

  const canAdd = nameInput.trim().length > 0;

  const handleAdd = () => {
    if (canAdd) {
      const ownership = ownershipInput.trim()
        ? parseFloat(ownershipInput.replace(/[^0-9.]/g, ""))
        : null;
      onChange([
        ...partners,
        {
          name: nameInput.trim(),
          beeOwnership: isNaN(ownership as number) ? null : ownership,
          beeLevel: levelInput.trim(),
        },
      ]);
      setNameInput("");
      setOwnershipInput("");
      setLevelInput("");
    }
  };

  const removePartner = (index: number) => {
    onChange(partners.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-2">
      <Label className="text-xs font-medium">{field.label}</Label>
      {field.description && (
        <p className="text-xs text-muted-foreground">{field.description}</p>
      )}
      <div className="flex gap-2 items-center">
        <div className="flex-[3]">
          <Input
            className="h-8 text-sm"
            placeholder={field.placeholder}
            value={nameInput}
            onChange={(e) => setNameInput(e.target.value)}
          />
        </div>
        <div className="w-24">
          <div className="relative">
            <Input
              className="h-8 text-sm pr-6"
              placeholder="Black %"
              value={ownershipInput}
              onChange={(e) => setOwnershipInput(e.target.value)}
            />
            <span className="absolute right-2 top-1/2 -translate-y-1/2 text-sm text-muted-foreground pointer-events-none">
              %
            </span>
          </div>
        </div>
        <div className="w-28">
          <Input
            className="h-8 text-sm"
            placeholder="BEE Level"
            value={levelInput}
            onChange={(e) => setLevelInput(e.target.value)}
          />
        </div>
        <button
          type="button"
          onClick={handleAdd}
          disabled={!canAdd}
          className={`h-8 w-8 flex items-center justify-center rounded border flex-shrink-0 ${
            canAdd
              ? "bg-alchemyPrimaryOrange text-white border-alchemyPrimaryOrange hover:bg-orange-600"
              : "bg-gray-100 text-gray-400 border-gray-200 cursor-not-allowed"
          }`}
        >
          <Plus className="h-4 w-4" />
        </button>
      </div>
      {partners.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pt-1">
          {partners.map((partner, index) => (
            <Badge
              key={index}
              variant="secondary"
              className="flex items-center gap-1 text-xs py-0.5"
            >
              <span className="font-medium">{partner.name}</span>
              {partner.beeOwnership !== null && (
                <span className="text-green-600">{partner.beeOwnership}% black</span>
              )}
              {partner.beeLevel && (
                <span className="text-muted-foreground">(Level {partner.beeLevel})</span>
              )}
              <X
                className="h-3 w-3 cursor-pointer hover:text-destructive ml-1"
                onClick={() => removePartner(index)}
              />
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// SHAREHOLDER SECTION COMPONENT
// =============================================================================

interface ShareholderInputProps {
  entityName: string;
  shareholders: Shareholder[];
  onEntityNameChange: (name: string) => void;
  onShareholdersChange: (shareholders: Shareholder[]) => void;
  config: {
    title: string;
    description: string;
    entityLabel: string;
    entityPlaceholder: string;
    showBEECalculation?: boolean;
    showPrePost?: boolean;
  };
}

function ShareholderInput({
  entityName,
  shareholders,
  onEntityNameChange,
  onShareholdersChange,
  config,
}: ShareholderInputProps) {
  // Ensure we always have at least 3 slots
  const displayShareholders =
    shareholders.length < 3
      ? [...shareholders, ...Array(3 - shareholders.length).fill({ name: "", percentage: null })]
      : shareholders;

  const updateShareholder = (index: number, field: "name" | "percentage", value: string) => {
    const updated = [...displayShareholders];
    if (field === "name") {
      updated[index] = { ...updated[index], name: value };
    } else {
      const numValue = value.trim() ? parseFloat(value.replace(/[^0-9.]/g, "")) : null;
      updated[index] = {
        ...updated[index],
        percentage: isNaN(numValue as number) ? null : numValue,
      };
    }
    onShareholdersChange(updated.filter((s) => s.name.trim() || s.percentage !== null));
  };

  const addShareholder = () => {
    onShareholdersChange([...displayShareholders, { name: "", percentage: null }]);
  };

  const removeShareholder = (index: number) => {
    const updated = displayShareholders.filter((_, i) => i !== index);
    onShareholdersChange(updated.filter((s) => s.name.trim() || s.percentage !== null));
  };

  const filledShareholders = displayShareholders.filter(
    (s) => s.name.trim() || s.percentage !== null
  );
  const totalPercentage = filledShareholders.reduce((sum, s) => sum + (s.percentage || 0), 0);

  // Calculate BEE ownership if enabled (simplified - would need more data in real implementation)
  const beeOwnership = config.showBEECalculation
    ? filledShareholders
        .filter((s) => s.name.toLowerCase().includes("bee") || s.name.toLowerCase().includes("black"))
        .reduce((sum, s) => sum + (s.percentage || 0), 0)
    : null;

  // Group shareholders into rows of 3
  const rows: Shareholder[][] = [];
  for (let i = 0; i < displayShareholders.length; i += 3) {
    rows.push(displayShareholders.slice(i, i + 3));
  }

  return (
    <div className="space-y-3">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-1">{config.title}</h3>
          <p className="text-xs text-muted-foreground">{config.description}</p>
        </div>
        <div className="text-right text-xs">
          {filledShareholders.length > 0 && totalPercentage > 0 && (
            <div className="text-muted-foreground">
              Total:{" "}
              <span className={`font-medium ${totalPercentage > 100 ? "text-red-500" : "text-green-600"}`}>
                {totalPercentage.toFixed(1)}%
              </span>
            </div>
          )}
          {config.showBEECalculation && beeOwnership !== null && beeOwnership > 0 && (
            <div className="text-green-600">
              BEE Ownership: <span className="font-medium">{beeOwnership.toFixed(1)}%</span>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div>
          <Label className="text-xs">{config.entityLabel}</Label>
          <div className="flex gap-1.5 mt-1">
            <Input
              className="h-8 text-sm flex-[2]"
              placeholder={config.entityPlaceholder}
              value={entityName}
              onChange={(e) => onEntityNameChange(e.target.value)}
            />
            <div className="w-16" />
          </div>
        </div>
      </div>

      <div className="space-y-2">
        {rows.map((row, rowIndex) => (
          <div key={rowIndex} className="grid grid-cols-3 gap-3">
            {row.map((shareholder, colIndex) => {
              const globalIndex = rowIndex * 3 + colIndex;
              const hasContent = shareholder.name.trim() || shareholder.percentage !== null;
              return (
                <div key={globalIndex} className="relative">
                  <div className="flex gap-1.5">
                    <Input
                      className="h-8 text-sm flex-[2]"
                      placeholder="Shareholder name"
                      value={shareholder.name}
                      onChange={(e) => updateShareholder(globalIndex, "name", e.target.value)}
                    />
                    <div className="relative w-16">
                      <Input
                        className="h-8 text-sm w-full pr-6 text-right"
                        placeholder="0"
                        value={shareholder.percentage !== null ? shareholder.percentage.toString() : ""}
                        onChange={(e) => updateShareholder(globalIndex, "percentage", e.target.value)}
                      />
                      <span className="absolute right-2 top-1/2 -translate-y-1/2 text-sm text-muted-foreground pointer-events-none">
                        %
                      </span>
                    </div>
                    {hasContent && displayShareholders.length > 3 && (
                      <button
                        type="button"
                        className="absolute -top-1 -right-1 h-4 w-4 rounded-full bg-gray-200 hover:bg-red-100 flex items-center justify-center"
                        onClick={() => removeShareholder(globalIndex)}
                      >
                        <X className="h-2.5 w-2.5 text-gray-500 hover:text-red-500" />
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ))}
      </div>

      <button
        type="button"
        className="text-xs text-alchemyPrimaryOrange hover:text-orange-600 font-medium flex items-center gap-1"
        onClick={addShareholder}
      >
        + Add Shareholder
      </button>
    </div>
  );
}

// =============================================================================
// DYNAMIC FIELD RENDERER
// =============================================================================

interface DynamicFieldProps {
  field: Step4FieldDefinition;
  data: DDProjectSetup;
  onChange: (updates: Partial<DDProjectSetup>) => void;
}

function DynamicField({ field, data, onChange }: DynamicFieldProps) {
  // Determine the correct onChange handler based on field type and ID
  const handleTagsChange = (tags: string[]) => {
    switch (field.id) {
      case "keyIndividuals":
      case "keyExecutives":
      case "keyPersonnel":
      case "management":
        onChange({ keyIndividuals: tags });
        break;
      case "regulators":
        onChange({ keyRegulators: tags });
        break;
      default:
        onChange({ keySuppliers: tags });
    }
  };

  const handlePartiesChange = (parties: Array<{ name: string; role: string }>) => {
    onChange({ keyOther: parties });
  };

  const handleLendersChange = (lenders: Array<{ name: string; description: string; facilityAmount: string }>) => {
    onChange({ keyLenders: lenders });
  };

  const handleCounterpartiesChange = (
    counterparties: Array<{ name: string; description: string; exposure: string }>
  ) => {
    onChange({ keyCustomers: counterparties });
  };

  const handleBEEPartnersChange = (partners: BEEPartnerEntry[]) => {
    // Convert BEE partners to party_role format for storage
    const converted = partners.map((p) => ({
      name: p.name,
      role: `${p.beeOwnership !== null ? `${p.beeOwnership}% black` : ""} ${p.beeLevel ? `Level ${p.beeLevel}` : ""}`.trim(),
    }));
    onChange({ keyOther: converted });
  };

  switch (field.type) {
    case "tags":
      return (
        <TagInput
          field={field}
          tags={
            field.id === "regulators"
              ? data.keyRegulators
              : ["keyIndividuals", "keyExecutives", "keyPersonnel", "management"].includes(field.id)
              ? data.keyIndividuals
              : data.keySuppliers
          }
          onChange={handleTagsChange}
        />
      );

    case "party_role":
      return (
        <PartyRoleInput
          field={field}
          parties={data.keyOther}
          onChange={handlePartiesChange}
        />
      );

    case "lender":
      return (
        <LenderInput
          field={field}
          lenders={data.keyLenders}
          onChange={handleLendersChange}
        />
      );

    case "counterparty":
      return (
        <CounterpartyInput
          field={field}
          counterparties={data.keyCustomers}
          onChange={handleCounterpartiesChange}
        />
      );

    case "bee_partner":
      // Convert stored parties back to BEE partner format for display
      const beePartners: BEEPartnerEntry[] = data.keyOther.map((p) => {
        const ownershipMatch = p.role.match(/(\d+(?:\.\d+)?)%\s*black/i);
        const levelMatch = p.role.match(/Level\s*(\d+)/i);
        return {
          name: p.name,
          beeOwnership: ownershipMatch ? parseFloat(ownershipMatch[1]) : null,
          beeLevel: levelMatch ? levelMatch[1] : "",
        };
      });
      return (
        <BEEPartnerInput
          field={field}
          partners={beePartners}
          onChange={handleBEEPartnersChange}
        />
      );

    default:
      return null;
  }
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export function Step4KeyParties({ data, onChange }: Step4Props) {
  // Get the configuration for the selected transaction type
  const config = data.transactionType ? STEP4_CONFIG[data.transactionType] : null;

  if (!config) {
    return (
      <div className="flex items-center justify-center h-48 text-muted-foreground bg-slate-50 rounded-lg border border-gray-200">
        <div className="text-center">
          <Info className="h-8 w-8 mx-auto mb-2 opacity-50" />
          <p>Please select a transaction type first</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Key Parties Section */}
      <div className="bg-slate-50 rounded-lg border border-gray-200 shadow-sm p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-1">{config.title}</h3>
        <p className="text-xs text-muted-foreground">{config.subtitle}</p>
        <p className="text-xs text-gray-400 mt-1 mb-4">
          Type a name and press Enter to add. Click × to remove.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {config.fields.map((field) => (
            <div
              key={field.id}
              className={`bg-white rounded-lg border border-gray-100 p-3 ${
                field.type === "lender" || field.type === "counterparty"
                  ? "md:col-span-2"
                  : ""
              }`}
            >
              <DynamicField field={field} data={data} onChange={onChange} />
            </div>
          ))}
        </div>
      </div>

      {/* Shareholder Section */}
      {config.shareholderSection.visible && (
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4">
          <ShareholderInput
            entityName={data.shareholderEntityName}
            shareholders={data.shareholders}
            onEntityNameChange={(name) => onChange({ shareholderEntityName: name })}
            onShareholdersChange={(shareholders) => onChange({ shareholders })}
            config={config.shareholderSection}
          />
        </div>
      )}
    </div>
  );
}
