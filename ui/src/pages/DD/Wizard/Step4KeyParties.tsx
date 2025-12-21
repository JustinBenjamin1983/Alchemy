import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { X, Plus } from "lucide-react";
import { useState, KeyboardEvent } from "react";
import { DDProjectSetup, REGULATOR_SUGGESTIONS, KEY_STAKEHOLDER_CONFIG, OtherStakeholder, Shareholder, LenderStakeholder, CounterpartyStakeholder } from "./types";

// Format number string as South African Rand currency
function formatCurrency(value: string): string {
  if (!value) return "";
  // Remove all non-numeric characters except decimal point
  const cleaned = value.replace(/[^\d.]/g, "");
  if (!cleaned) return "";

  // Parse as number and format
  const num = parseFloat(cleaned);
  if (isNaN(num)) return value;

  // Format with R prefix and thousand separators
  return `R${Math.round(num).toLocaleString("en-ZA")}`;
}

interface Step4Props {
  data: DDProjectSetup;
  onChange: (updates: Partial<DDProjectSetup>) => void;
}

interface TagInputProps {
  label: string;
  description?: string;
  placeholder: string;
  tags: string[];
  onChange: (tags: string[]) => void;
  suggestions?: string[];
}

function TagInput({
  label,
  description,
  placeholder,
  tags,
  onChange,
  suggestions = [],
}: TagInputProps) {
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
      <Label className="text-xs">{label}</Label>
      {description && (
        <p className="text-xs text-muted-foreground">{description}</p>
      )}
      <Input
        className="h-8 text-sm"
        placeholder={placeholder}
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
      {suggestions.length > 0 && (
        <div className="flex flex-wrap gap-1 pt-1">
          <span className="text-xs text-muted-foreground">Suggestions:</span>
          {suggestions
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

interface OtherStakeholderInputProps {
  stakeholders: OtherStakeholder[];
  onChange: (stakeholders: OtherStakeholder[]) => void;
  namePlaceholder: string;
}

function OtherStakeholderInput({
  stakeholders,
  onChange,
  namePlaceholder,
}: OtherStakeholderInputProps) {
  const [nameInput, setNameInput] = useState("");
  const [roleInput, setRoleInput] = useState("");

  const canAdd = nameInput.trim() && roleInput.trim();

  const handleAdd = () => {
    if (canAdd) {
      onChange([...stakeholders, { name: nameInput.trim(), role: roleInput.trim() }]);
      setNameInput("");
      setRoleInput("");
    }
  };

  const removeStakeholder = (index: number) => {
    onChange(stakeholders.filter((_, i) => i !== index));
  };

  return (
    <div className="col-span-full space-y-2">
      <Label className="text-xs">Other</Label>
      <div className="flex gap-2 items-center">
        <div className="flex-1">
          <Input
            className="h-8 text-sm"
            placeholder="Party Name"
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
          className={`h-8 w-8 flex items-center justify-center rounded border ${
            canAdd
              ? "bg-alchemyPrimaryOrange text-white border-alchemyPrimaryOrange hover:bg-orange-600"
              : "bg-gray-100 text-gray-400 border-gray-200 cursor-not-allowed"
          }`}
        >
          <Plus className="h-4 w-4" />
        </button>
      </div>
      {stakeholders.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pt-1">
          {stakeholders.map((stakeholder, index) => (
            <Badge
              key={index}
              variant="secondary"
              className="flex items-center gap-1 text-xs py-0.5"
            >
              <span className="font-medium">{stakeholder.name}</span>
              <span className="text-muted-foreground">({stakeholder.role})</span>
              <X
                className="h-3 w-3 cursor-pointer hover:text-destructive ml-1"
                onClick={() => removeStakeholder(index)}
              />
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}

interface LenderInputProps {
  label: string;
  placeholder: string;
  lenders: LenderStakeholder[];
  onChange: (lenders: LenderStakeholder[]) => void;
}

function LenderInput({
  label,
  placeholder,
  lenders,
  onChange,
}: LenderInputProps) {
  const [nameInput, setNameInput] = useState("");
  const [descriptionInput, setDescriptionInput] = useState("");
  const [amountInput, setAmountInput] = useState("");

  const canAdd = nameInput.trim().length > 0;

  const handleAdd = () => {
    if (canAdd) {
      onChange([...lenders, {
        name: nameInput.trim(),
        description: descriptionInput.trim(),
        facilityAmount: formatCurrency(amountInput)
      }]);
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
    <div className="col-span-full space-y-2">
      <Label className="text-xs">{label}</Label>
      <div className="flex gap-2 items-center">
        <div className="flex-[2]">
          <Input
            className="h-8 text-sm"
            placeholder={placeholder}
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
            placeholder="e.g. R500m"
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

interface CounterpartyInputProps {
  label: string;
  placeholder: string;
  counterparties: CounterpartyStakeholder[];
  onChange: (counterparties: CounterpartyStakeholder[]) => void;
}

function CounterpartyInput({
  label,
  placeholder,
  counterparties,
  onChange,
}: CounterpartyInputProps) {
  const [nameInput, setNameInput] = useState("");
  const [descriptionInput, setDescriptionInput] = useState("");
  const [exposureInput, setExposureInput] = useState("");

  const canAdd = nameInput.trim().length > 0;

  const handleAdd = () => {
    if (canAdd) {
      onChange([...counterparties, {
        name: nameInput.trim(),
        description: descriptionInput.trim(),
        exposure: formatCurrency(exposureInput)
      }]);
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
    <div className="col-span-full space-y-2">
      <Label className="text-xs">{label}</Label>
      <div className="flex gap-2 items-center">
        <div className="flex-[2]">
          <Input
            className="h-8 text-sm"
            placeholder={placeholder}
            value={nameInput}
            onChange={(e) => setNameInput(e.target.value)}
          />
        </div>
        <div className="flex-[2]">
          <Input
            className="h-8 text-sm"
            placeholder="Description / Security Type"
            value={descriptionInput}
            onChange={(e) => setDescriptionInput(e.target.value)}
          />
        </div>
        <div className="w-32">
          <Input
            className="h-8 text-sm"
            placeholder="e.g. R100m"
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

interface ShareholderInputProps {
  entityName: string;
  shareholders: Shareholder[];
  onEntityNameChange: (name: string) => void;
  onShareholdersChange: (shareholders: Shareholder[]) => void;
}

function ShareholderInput({
  entityName,
  shareholders,
  onEntityNameChange,
  onShareholdersChange,
}: ShareholderInputProps) {
  // Ensure we always have at least 3 slots
  const displayShareholders = shareholders.length < 3
    ? [...shareholders, ...Array(3 - shareholders.length).fill({ name: "", percentage: null })]
    : shareholders;

  const updateShareholder = (index: number, field: 'name' | 'percentage', value: string) => {
    const updated = [...displayShareholders];
    if (field === 'name') {
      updated[index] = { ...updated[index], name: value };
    } else {
      const numValue = value.trim() ? parseFloat(value.replace(/[^0-9.]/g, '')) : null;
      updated[index] = { ...updated[index], percentage: isNaN(numValue as number) ? null : numValue };
    }
    // Filter out empty entries for storage, but keep structure
    onShareholdersChange(updated.filter(s => s.name.trim() || s.percentage !== null));
  };

  const addShareholder = () => {
    onShareholdersChange([...displayShareholders, { name: "", percentage: null }]);
  };

  const removeShareholder = (index: number) => {
    const updated = displayShareholders.filter((_, i) => i !== index);
    onShareholdersChange(updated.filter(s => s.name.trim() || s.percentage !== null));
  };

  const filledShareholders = displayShareholders.filter(s => s.name.trim() || s.percentage !== null);
  const totalPercentage = filledShareholders.reduce((sum, s) => sum + (s.percentage || 0), 0);

  // Group shareholders into rows of 3
  const rows: Shareholder[][] = [];
  for (let i = 0; i < displayShareholders.length; i += 3) {
    rows.push(displayShareholders.slice(i, i + 3));
  }

  return (
    <div className="space-y-3 pt-4 border-t border-gray-200">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-sm font-medium mb-1">Shareholders</h3>
          <p className="text-xs text-muted-foreground">
            Add details of the shareholding structure for the relevant entity.
          </p>
        </div>
        {filledShareholders.length > 0 && totalPercentage > 0 && (
          <div className="text-xs text-muted-foreground">
            Total: <span className={`font-medium ${totalPercentage > 100 ? 'text-red-500' : 'text-green-600'}`}>
              {totalPercentage.toFixed(1)}%
            </span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div>
          <Label className="text-xs">Entity Name</Label>
          <div className="flex gap-1.5 mt-1">
            <Input
              className="h-8 text-sm flex-[2]"
              placeholder="e.g., Target Company (Pty) Ltd"
              value={entityName}
              onChange={(e) => onEntityNameChange(e.target.value)}
            />
            <div className="w-16" /> {/* Spacer to match percentage column */}
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
                      onChange={(e) => updateShareholder(globalIndex, 'name', e.target.value)}
                    />
                    <div className="relative w-16">
                      <Input
                        className="h-8 text-sm w-full pr-6 text-right"
                        placeholder="0"
                        value={shareholder.percentage !== null ? shareholder.percentage.toString() : ""}
                        onChange={(e) => updateShareholder(globalIndex, 'percentage', e.target.value)}
                      />
                      <span className="absolute right-2 top-1/2 -translate-y-1/2 text-sm text-muted-foreground pointer-events-none">%</span>
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

export function Step4KeyParties({ data, onChange }: Step4Props) {
  const regulatorSuggestions = data.transactionType
    ? REGULATOR_SUGGESTIONS[data.transactionType] || []
    : [];

  // Get dynamic stakeholder labels based on transaction type
  const stakeholderConfig = data.transactionType
    ? KEY_STAKEHOLDER_CONFIG[data.transactionType]
    : {
        individuals: { label: "Key Individuals", placeholder: "e.g., Key executives..." },
        suppliers: { label: "Key Suppliers", placeholder: "e.g., Key suppliers..." },
        customers: { label: "Key Customers/Clients", placeholder: "e.g., Key customers..." },
        lenders: { label: "Key Lenders/Financiers", placeholder: "e.g., Key lenders..." },
        regulators: { label: "Key Regulators", placeholder: "e.g., Key regulators..." },
        other: { label: "Other", placeholder: "e.g., Other stakeholders..." },
      };

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold mb-1">Key Stakeholders</h2>
        <p className="text-sm text-muted-foreground">
          Identifying key stakeholders helps flag related findings and contracts.
        </p>
        <p className="text-xs text-gray-400 mt-1">
          Type a name and press Enter to add. Click × to remove.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        <TagInput
          label={stakeholderConfig.individuals.label}
          placeholder={stakeholderConfig.individuals.placeholder}
          tags={data.keyIndividuals}
          onChange={(individuals) => onChange({ keyIndividuals: individuals })}
        />

        <TagInput
          label={stakeholderConfig.suppliers.label}
          placeholder={stakeholderConfig.suppliers.placeholder}
          tags={data.keySuppliers}
          onChange={(suppliers) => onChange({ keySuppliers: suppliers })}
        />

        <TagInput
          label={stakeholderConfig.regulators.label}
          placeholder={stakeholderConfig.regulators.placeholder}
          tags={data.keyRegulators}
          onChange={(regulators) => onChange({ keyRegulators: regulators })}
          suggestions={regulatorSuggestions}
        />

        <CounterpartyInput
          label={stakeholderConfig.customers.label}
          placeholder={stakeholderConfig.customers.placeholder}
          counterparties={data.keyCustomers}
          onChange={(customers) => onChange({ keyCustomers: customers })}
        />

        <LenderInput
          label={stakeholderConfig.lenders.label}
          placeholder={stakeholderConfig.lenders.placeholder}
          lenders={data.keyLenders}
          onChange={(lenders) => onChange({ keyLenders: lenders })}
        />

        <OtherStakeholderInput
          stakeholders={data.keyOther}
          onChange={(other) => onChange({ keyOther: other })}
          namePlaceholder={stakeholderConfig.other.placeholder}
        />
      </div>

      <ShareholderInput
        entityName={data.shareholderEntityName}
        shareholders={data.shareholders}
        onEntityNameChange={(name) => onChange({ shareholderEntityName: name })}
        onShareholdersChange={(shareholders) => onChange({ shareholders })}
      />
    </div>
  );
}
