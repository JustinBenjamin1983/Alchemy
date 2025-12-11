// File: ui/src/pages/DD/EnhancedRiskManager.tsx

import { useRef, useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
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
import { Check, ChevronsUpDown, Folder, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { RISK_CATEGORIES } from "@/lib/utils";
import * as XLSX from "xlsx";

/* ---------- types ---------- */
type Risk = {
  category: string;
  detail: string; // Changed from 'description' to 'detail' to match backend
  folder_scope: string; // Changed from 'folder' to 'folder_scope' to match backend
};

type Props = {
  folders: { folder_id: string; folder_name: string }[];
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (risks: Risk[]) => void;
  isSubmitting?: boolean;
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
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
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
          setTimeout(() => inputRef.current?.focus(), 0);
        }}
      >
        <Command shouldFilter={false}>
          <CommandInput
            ref={inputRef}
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
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
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
          setTimeout(() => inputRef.current?.focus(), 0);
        }}
      >
        <Command shouldFilter={false}>
          <CommandInput
            ref={inputRef}
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

/* ---------- Main EnhancedRiskManager Component ---------- */
export default function EnhancedRiskManager({
  folders,
  isOpen,
  onClose,
  onSubmit,
  isSubmitting = false,
}: Props) {
  /* --------------- state ---------------- */
  const [risks, setRisks] = useState<Risk[]>([]);
  const [newRiskDetail, setNewRiskDetail] = useState("");
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  /* --------------- helpers -------------- */
  const updateRisk = (idx: number, patch: Partial<Risk>) =>
    setRisks((prev) => {
      const next = [...prev];
      next[idx] = { ...next[idx], ...patch };
      return next;
    });

  const addRisk = () => {
    if (!newRiskDetail.trim()) return;
    setRisks((prev) => [
      ...prev,
      {
        detail: newRiskDetail.trim(),
        category: "",
        folder_scope: "All Folders",
      },
    ]);
    setNewRiskDetail("");
    setIsAddDialogOpen(false);
  };

  const removeRisk = (idx: number) => {
    setRisks((prev) => prev.filter((_, i) => i !== idx));
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
        const validRows = rows.filter((r) => r[0] && r[1]);
        const newRisks = validRows.map((r) => ({
          category: String(r[0]).trim(),
          detail: String(r[1]).trim(),
          folder_scope: r[2] ? String(r[2]).trim() : "All Folders",
        }));

        setRisks((prev) => [...prev, ...newRisks]);
      } catch (error) {
        console.error("Error parsing Excel file:", error);
      }
    };
    reader.readAsArrayBuffer(file);
    e.target.value = "";
  };

  const handleSubmit = () => {
    // Filter out incomplete risks
    const validRisks = risks.filter(
      (risk) => risk.category.trim() && risk.detail.trim()
    );

    if (validRisks.length === 0) return;

    onSubmit(validRisks);
  };

  const handleClose = () => {
    setRisks([]);
    setNewRiskDetail("");
    setIsAddDialogOpen(false);
    onClose();
  };

  // Count valid risks
  const validRisksCount = risks.filter(
    (risk) => risk.category.trim() && risk.detail.trim()
  ).length;

  /* --------------- render --------------- */
  return (
    <>
      {/* Main Dialog */}
      <Dialog open={isOpen} onOpenChange={handleClose}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Add New Risks</DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            {/* Control buttons */}
            <div className="flex gap-2 items-center">
              <Button onClick={() => setIsAddDialogOpen(true)}>Add Risk</Button>
              <Button
                variant="outline"
                onClick={() => fileInputRef.current?.click()}
              >
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
                  {validRisksCount < risks.length && (
                    <span className="text-amber-600 ml-1">
                      ({validRisksCount} complete)
                    </span>
                  )}
                </span>
              )}
            </div>

            {/* Risk table */}
            <div className="border rounded-lg overflow-x-auto max-h-[400px] overflow-y-auto">
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
                      {/* Category */}
                      <TableCell>
                        <CategoryCombobox
                          value={risk.category}
                          onValueChange={(v) =>
                            updateRisk(idx, { category: v })
                          }
                          categories={RISK_CATEGORIES}
                        />
                      </TableCell>
                      {/* Description */}
                      <TableCell>
                        <Input
                          value={risk.detail}
                          onChange={(e) =>
                            updateRisk(idx, { detail: e.target.value })
                          }
                          placeholder="Enter risk description..."
                        />
                      </TableCell>
                      {/* Folder Scope */}
                      <TableCell>
                        <FolderAutocomplete
                          value={risk.folder_scope}
                          onValueChange={(v) =>
                            updateRisk(idx, { folder_scope: v })
                          }
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
                Excel Import Format: Column A = Category, Column B =
                Description, Column C = Folder (optional)
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={handleClose}>
              Cancel
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={validRisksCount === 0 || isSubmitting}
            >
              {isSubmitting && <Loader2 className="animate-spin mr-2" />}
              Add {validRisksCount} Risk{validRisksCount !== 1 ? "s" : ""}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Quick Add Dialog */}
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
                value={newRiskDetail}
                onChange={(e) => setNewRiskDetail(e.target.value)}
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
              <Button onClick={addRisk} disabled={!newRiskDetail.trim()}>
                Add Risk
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
