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
import { FileWarning } from "lucide-react";
import { useState } from "react";

export default function SingleTextPrompt({
  show,
  onClosing,
  header,
  label,
  warning,
}: {
  show: boolean;
  onClosing: (value) => void;
  header: string;
  label: string;
  warning?: string;
}) {
  const handleClose = (closing, value) => {
    onClosing(value);
    setTimeout(() => {
      document.body.style.pointerEvents = "auto";
    }, 500);
  };
  const [inputValue, setInputValue] = useState(null);

  return (
    <>
      <Dialog
        open={show}
        onOpenChange={(closing) => handleClose(closing, null)}
      >
        <DialogContent className="w-[600px]">
          <DialogHeader>
            <DialogTitle>{header}</DialogTitle>
            <DialogDescription></DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-3 items-center gap-4">
              <Label htmlFor="name" className="text-right">
                {label}
              </Label>
              <Input
                value={inputValue}
                onChange={(evt) => setInputValue(evt.target.value)}
                className="col-span-2"
              />
            </div>
          </div>
          {warning && (
            <div className="grid grid-cols-[50px_1fr]">
              <FileWarning />
              <div className="text-red-400 font-bold">{warning}</div>
            </div>
          )}

          <DialogFooter className="">
            <Button
              type="button"
              variant="default"
              onClick={() => handleClose(true, inputValue)}
            >
              Save
            </Button>

            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                handleClose(true, null);
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
