// File: ui/src/pages/DD/RiskManager.tsx

import { useRef, useState, useEffect } from "react"; // Add useEffect import
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Check, ChevronsUpDown, Folder } from "lucide-react";
import { cn } from "@/lib/utils";
import { RISK_CATEGORIES } from "@/lib/utils";
import * as XLSX from "xlsx";

/* ---------- types ---------- */
type Risk = {
  category: string;
  description: string;
  folder: string; // single value now
};

type Props = {
  folders: { folder_id: string; folder_name: string }[];
  onRisksChange: (r: Risk[]) => void;
};

/* ---------- Enhanced Category Combobox Component ---------- */
interface CategoryComboboxProps {
  value: string;
  onValueChange: (value: string) => void;
  categories: string[];
}

function CategoryCombobox({
  value,
  onValueChange,
  categories,
}: CategoryComboboxProps) {
  const [open, setOpen] = useState(false);
  const [searchValue, setSearchValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null); // Add ref for input

  // Add useEffect to handle focus
  useEffect(() => {
    if (open) {
      // Use setTimeout to ensure the popover is fully rendered
      const timer = setTimeout(() => {
        inputRef.current?.focus();
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [open]);

  const handleSelect = (selectedValue: string) => {
    onValueChange(selectedValue);
    setOpen(false);
    setSearchValue("");
  };

  const filteredCategories = categories.filter((category) =>
    category.toLowerCase().includes(searchValue.toLowerCase())
  );

  return (
    <Popover open={open} onOpenChange={setOpen} modal={true}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-full justify-between font-normal"
        >
          {value || "Select or type category..."}
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent
        className="w-[300px] p-0 z-[9999]"
        align="start"
        sideOffset={4}
        onOpenAutoFocus={(e) => {
          e.preventDefault();
          // Also focus here as a fallback
          setTimeout(() => inputRef.current?.focus(), 0);
        }}
      >
        <Command shouldFilter={false}>
          <CommandInput
            ref={inputRef} // Add ref
            placeholder="Search or create category..."
            value={searchValue}
            onValueChange={setSearchValue}
          />
          <CommandList className="max-h-[200px] overflow-y-auto">
            <CommandEmpty>No categories found.</CommandEmpty>
            {searchValue && !categories.includes(searchValue) && (
              <CommandGroup>
                <CommandItem
                  onSelect={() => handleSelect(searchValue)}
                  className="font-medium"
                >
                  <Check className="mr-2 h-4 w-4 opacity-0" />
                  Create "{searchValue}"
                </CommandItem>
              </CommandGroup>
            )}
            {filteredCategories.length > 0 && (
              <CommandGroup>
                {filteredCategories.map((category) => (
                  <CommandItem
                    key={category}
                    value={category}
                    onSelect={() => handleSelect(category)}
                  >
                    <Check
                      className={cn(
                        "mr-2 h-4 w-4",
                        value === category ? "opacity-100" : "opacity-0"
                      )}
                    />
                    {category}
                  </CommandItem>
                ))}
              </CommandGroup>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}

/* ---------- Enhanced Folder Autocomplete Component ---------- */
interface FolderAutocompleteProps {
  value: string;
  onValueChange: (value: string) => void;
  folders: { folder_id: string; folder_name: string }[];
}

function FolderAutocomplete({
  value,
  onValueChange,
  folders,
}: FolderAutocompleteProps) {
  const [open, setOpen] = useState(false);
  const [searchValue, setSearchValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null); // Add ref for input

  // Add useEffect to handle focus
  useEffect(() => {
    if (open) {
      // Use setTimeout to ensure the popover is fully rendered
      const timer = setTimeout(() => {
        inputRef.current?.focus();
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [open]);

  const folderOptions = [
    { folder_id: "all", folder_name: "All Folders" },
    ...folders,
  ];

  const handleSelect = (folderId: string) => {
    const selectedFolder = folderOptions.find((f) => f.folder_id === folderId);
    onValueChange(selectedFolder?.folder_name || "");
    setOpen(false);
    setSearchValue("");
  };

  const filteredFolders = folderOptions.filter((folder) =>
    folder.folder_name.toLowerCase().includes(searchValue.toLowerCase())
  );

  return (
    <Popover open={open} onOpenChange={setOpen} modal={true}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-full justify-between font-normal"
        >
          <div className="flex items-center gap-2 truncate">
            <Folder className="h-4 w-4" />
            {value || "Select folder..."}
          </div>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent
        className="w-[300px] p-0 z-[9999]"
        align="start"
        sideOffset={4}
        onOpenAutoFocus={(e) => {
          e.preventDefault();
          // Also focus here as a fallback
          setTimeout(() => inputRef.current?.focus(), 0);
        }}
      >
        <Command shouldFilter={false}>
          <CommandInput
            ref={inputRef} // Add ref
            placeholder="Search folders..."
            value={searchValue}
            onValueChange={setSearchValue}
          />
          <CommandList className="max-h-[200px] overflow-y-auto">
            <CommandEmpty>No folders found.</CommandEmpty>
            <CommandGroup>
              {filteredFolders.map((folder) => (
                <CommandItem
                  key={folder.folder_id}
                  value={folder.folder_id}
                  onSelect={() => handleSelect(folder.folder_id)}
                >
                  <Check
                    className={cn(
                      "mr-2 h-4 w-4",
                      value === folder.folder_name ? "opacity-100" : "opacity-0"
                    )}
                  />
                  <Folder className="mr-2 h-4 w-4" />
                  {folder.folder_name}
                  {folder.folder_id === "all" && (
                    <span className="ml-2 text-xs text-muted-foreground">
                      (Search all folders)
                    </span>
                  )}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}

/* ---------- Main RiskManager Component ---------- */
export default function RiskManager({ folders, onRisksChange }: Props) {
  /* --------------- state ---------------- */
  const [risks, setRisks] = useState<Risk[]>([]);
  const [description, setDescription] = useState("");
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  /* --------------- helpers -------------- */
  const updateRisk = (idx: number, patch: Partial<Risk>) =>
    setRisks((prev) => {
      const next = [...prev];
      next[idx] = { ...next[idx], ...patch };
      onRisksChange(next);
      return next;
    });

  const pushRisks = (newOnes: Risk[]) => {
    const merged = [...risks, ...newOnes];
    setRisks(merged);
    onRisksChange(merged);
  };

  const addRisk = () => {
    if (!description.trim()) return;
    pushRisks([{ description: description.trim(), category: "", folder: "" }]);
    setDescription("");
    setIsAddDialogOpen(false);
  };

  const removeRisk = (idx: number) => {
    const newRisks = risks.filter((_, i) => i !== idx);
    setRisks(newRisks);
    onRisksChange(newRisks);
  };

  const handleBatchFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (evt) => {
      try {
        const wb = XLSX.read(
          new Uint8Array(evt.target!.result as ArrayBuffer),
          {
            type: "array",
          }
        );
        const rows: any[][] = XLSX.utils.sheet_to_json(
          wb.Sheets[wb.SheetNames[0]],
          { header: 1 }
        );

        // Skip header row and filter valid rows
        const validRows = rows.slice(1).filter((r) => r[0] && r[1]);
        const newRisks = validRows.map((r) => ({
          category: String(r[0]).trim(),
          description: String(r[1]).trim(),
          folder: r[2] ? String(r[2]).trim() : "",
        }));

        pushRisks(newRisks);
      } catch (error) {
        console.error("Error parsing Excel file:", error);
        // You could add a toast notification here
      }
    };
    reader.readAsArrayBuffer(file);
    e.target.value = "";
  };

  /* --------------- render --------------- */
  return (
    <div className="space-y-4">
      {/* ---------- Add-risk dialog ---------- */}
      <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Add New Risk</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label htmlFor="risk-description" className="text-sm font-medium">
                Risk Description
              </label>
              <Input
                id="risk-description"
                placeholder="Enter risk description..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    addRisk();
                  }
                }}
              />
            </div>
            <div className="flex gap-2 justify-end">
              <Button
                variant="outline"
                onClick={() => setIsAddDialogOpen(false)}
              >
                Cancel
              </Button>
              <Button onClick={addRisk} disabled={!description.trim()}>
                Add Risk
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* ---------- top buttons ------------- */}
      <div className="flex gap-2 items-center">
        <Button onClick={() => setIsAddDialogOpen(true)}>Add Risk</Button>
        <Button variant="outline" onClick={() => fileInputRef.current?.click()}>
          Import from Excel
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".xlsx,.xls"
          className="hidden"
          onChange={handleBatchFile}
        />
        {risks.length > 0 && (
          <span className="text-sm text-muted-foreground ml-2">
            {risks.length} risk{risks.length !== 1 ? "s" : ""} defined
          </span>
        )}
      </div>

      {/* ---------- risk table -------------- */}
      <div className="border rounded-lg overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[200px]">Category</TableHead>
              <TableHead className="min-w-[250px]">Description</TableHead>
              <TableHead className="w-[200px]">Folder Scope</TableHead>
              <TableHead className="w-[100px]">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {risks.map((risk, idx) => (
              <TableRow key={idx}>
                {/* Enhanced Category Combobox */}
                <TableCell>
                  <CategoryCombobox
                    value={risk.category}
                    onValueChange={(v) => updateRisk(idx, { category: v })}
                    categories={RISK_CATEGORIES}
                  />
                </TableCell>
                {/* Description */}
                <TableCell>
                  <div className="font-medium text-sm">
                    <div className="line-clamp-2" title={risk.description}>
                      {risk.description}
                    </div>
                  </div>
                </TableCell>
                {/* Enhanced Folder Autocomplete */}
                <TableCell>
                  <FolderAutocomplete
                    value={risk.folder}
                    onValueChange={(v) => updateRisk(idx, { folder: v })}
                    folders={folders}
                  />
                </TableCell>
                {/* Actions */}
                <TableCell>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => removeRisk(idx)}
                    className="text-red-600 hover:text-red-700 hover:bg-red-50"
                  >
                    Remove
                  </Button>
                </TableCell>
              </TableRow>
            ))}
            {risks.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} className="h-24 text-center">
                  <div className="flex flex-col items-center justify-center text-muted-foreground">
                    <div className="text-lg font-medium">
                      No risks defined yet
                    </div>
                    <div className="text-sm mt-1">
                      Add risks manually or import from Excel
                    </div>
                  </div>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {/* Excel format hint */}
      {risks.length === 0 && (
        <div className="text-xs text-muted-foreground">
          Excel Import Format: Column A = Category, Column B = Description,
          Column C = Folder (optional)
        </div>
      )}
    </div>
  );
}
