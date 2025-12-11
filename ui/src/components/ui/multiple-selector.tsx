/* Based on shadcn-ui expansions: https://shadcnui-expansions.typeart.cc/docs/multiple-selector */
import * as React from "react";
import {
  Command,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Badge } from "@/components/ui/badge";
import { Check, Plus } from "lucide-react";
import { cn } from "@/lib/utils";

type Option = { label: string; value: string };

interface MultipleSelectorProps {
  value: string[];
  onChange: (value: string[]) => void;
  defaultOptions: Option[];
  placeholder?: string;
  emptyIndicator?: string;
  renderValue?: (v: string) => string; // helper to show labels from ids
}

export function MultipleSelector({
  value,
  onChange,
  defaultOptions,
  placeholder = "Select…",
  emptyIndicator = "Nothing found.",
  renderValue,
}: MultipleSelectorProps) {
  const [open, setOpen] = React.useState(false);
  const [search, setSearch] = React.useState("");
  const filtered = defaultOptions.filter((opt) =>
    opt.label.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          className={cn(
            "w-full min-h-[2.25rem] border rounded-md flex items-center gap-1 px-2 text-left",
            "hover:bg-accent/50"
          )}
        >
          {value.length === 0 && (
            <span className="text-muted-foreground">{placeholder}</span>
          )}
          {value.map((val) => (
            <Badge
              key={val}
              onClick={(e) => {
                e.stopPropagation();
                onChange(value.filter((v) => v !== val));
              }}
              className="gap-1 cursor-pointer"
            >
              {renderValue ? renderValue(val) : val}
              <Plus className="w-3 h-3 rotate-45" />
            </Badge>
          ))}
        </button>
      </PopoverTrigger>
      <PopoverContent className="p-0 w-[220px]" side="bottom">
        <Command shouldFilter={false}>
          <CommandInput
            placeholder="Search…"
            value={search}
            onValueChange={setSearch}
          />
          <CommandList className="max-h-40 overflow-y-auto">
            {filtered.length === 0 && (
              <p className="px-2 py-3 text-sm text-muted-foreground">
                {emptyIndicator}
              </p>
            )}
            {filtered.map((opt) => {
              const selected = value.includes(opt.value);
              return (
                <CommandItem
                  key={opt.value}
                  onSelect={() =>
                    onChange(
                      selected
                        ? value.filter((v) => v !== opt.value)
                        : [...value, opt.value]
                    )
                  }
                >
                  <Check
                    className={cn(
                      "mr-2 h-4 w-4",
                      selected ? "opacity-100" : "opacity-0"
                    )}
                  />
                  {opt.label}
                </CommandItem>
              );
            })}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
