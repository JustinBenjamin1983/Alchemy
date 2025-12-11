import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RISK_CATEGORIES } from "@/lib/utils";
import { useState } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";

export default function AddNewRiskPrompt({
  show,
  onClosing,
}: {
  show: boolean;
  onClosing: (category, detail) => void;
}) {
  const handleClose = (closing, category, detail) => {
    onClosing(category, detail);
    setTimeout(() => {
      document.body.style.pointerEvents = "auto";
    }, 500);
  };
  const [inputValue, setInputValue] = useState(null);
  const [category, setCategory] = useState("");
  return (
    <>
      <Dialog
        open={show}
        onOpenChange={(closing) => handleClose(closing, null, null)}
      >
        <DialogContent className="w-[600px]">
          <DialogHeader>
            <DialogTitle>Add a new risk</DialogTitle>
            <DialogDescription></DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-[100px_1fr] gap-4">
              <label className="text-sm font-medium">Category</label>
              <Select value={category} onValueChange={setCategory}>
                <SelectTrigger>
                  <SelectValue placeholder="Select category" />
                </SelectTrigger>
                <SelectContent>
                  {RISK_CATEGORIES.map((cat) => (
                    <SelectItem key={cat} value={cat}>
                      {cat}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-[100px_1fr] gap-4">
              <Label htmlFor="name" className="">
                Detail
              </Label>
              <Input
                value={inputValue}
                onChange={(evt) => setInputValue(evt.target.value)}
              />
            </div>
          </div>

          <DialogFooter className="">
            <Button
              type="button"
              variant="default"
              onClick={() => handleClose(true, category, inputValue)}
            >
              Save
            </Button>

            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                handleClose(true, null, null);
              }}
            >
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
