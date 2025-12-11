import { useState } from "react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { Check, ChevronDown } from "lucide-react";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { cn } from "@/lib/utils";

export function CountryDropDown() {
  const [countryOpen, setCountryOpen] = useState(false);
  const [selectedCountry, setSelectedCountry] = useState<string | undefined>(
    ""
  );

  const countries = [
    { value: "1", id: "1", name: "South Africa" },
    { value: "2", id: "2", name: "United States" },
    { value: "3", id: "3", name: "United Kingdom" },
  ];

  return (
    <Popover open={countryOpen} onOpenChange={setCountryOpen} modal>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={countryOpen}
          className="justify-between"
        >
          {selectedCountry
            ? countries?.find((c) => c.id === selectedCountry)?.name
            : "Select country"}
          <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="p-0">
        <Command>
          <CommandInput placeholder="Search country..." />
          <CommandEmpty>No country found.</CommandEmpty>
          <CommandGroup>
            <CommandList>
              {countries?.map((country) => (
                <CommandItem
                  key={country.id}
                  value={country.id}
                  onSelect={() => {
                    setSelectedCountry(country.id);
                    setCountryOpen(false);
                  }}
                >
                  <Check
                    className={cn(
                      "mr-2 h-4 w-4",
                      selectedCountry === country.id
                        ? "opacity-100"
                        : "opacity-0"
                    )}
                  />
                  {country.name}
                </CommandItem>
              ))}
            </CommandList>
          </CommandGroup>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
