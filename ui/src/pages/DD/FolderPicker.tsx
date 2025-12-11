import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
} from "@/components/ui/dialog";
import Hierarchy from "./Files/Hierarchy";
import { useState } from "react";
import { useGetDD } from "@/hooks/useGetDD";

export default function FolderPicker({
  header,
  show,
  onClosing,
  dd_id,
  onSelected,
  selectedFolderId,
  askBefore = false,
}: {
  header: string;
  show: boolean;
  onClosing: any;
  dd_id: string;
  onSelected: ({
    folder_id,
    folder_name,
  }: {
    folder_id: string;
    folder_name: string;
  }) => void;
  selectedFolderId?: string;
  askBefore?: boolean;
}) {
  const [selectedFolder, setSelectedFolder] = useState<{
    folder_id;
    folder_name;
  }>(null);

  const { data: dd } = useGetDD(dd_id);
  const handleClose = (closing) => {
    onClosing();
    setTimeout(() => {
      document.body.style.pointerEvents = "auto";
    }, 500);
  };
  return (
    <>
      <Dialog open={show} onOpenChange={handleClose}>
        <DialogContent className="w-[500px]">
          <DialogHeader>
            {header}
            <DialogDescription></DialogDescription>
          </DialogHeader>

          <div>
            <Hierarchy
              dd_id={dd_id}
              folders={dd?.folders}
              onSelect={(folderIdAndName) => {
                {
                  setSelectedFolder(folderIdAndName);
                  if (!askBefore) {
                    onSelected(folderIdAndName);
                  }
                }
              }}
              selectedFolderId={selectedFolderId}
            />
          </div>
          <DialogFooter className="">
            {askBefore && (
              <Button
                type="button"
                variant="default"
                onClick={() => {
                  onSelected(selectedFolder);
                }}
              >
                OK
              </Button>
            )}
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                handleClose(true);
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
