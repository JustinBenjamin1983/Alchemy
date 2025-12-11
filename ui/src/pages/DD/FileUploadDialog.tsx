import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
} from "@/components/ui/dialog";
import { useEffect, useRef, useState } from "react";
import { useMutateDDUploadSingleFile } from "@/hooks/useMutateDDUploadSingleFile";
import { Loader2 } from "lucide-react";

export default function FileUploadDialog({
  header,
  show,
  onClosing,
  dd_id,
  folder_id,
}: {
  header: string;
  show: boolean;
  onClosing: any;
  dd_id: string;
  folder_id: string;
}) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [filePendingUpload, setFilePendingUpload] = useState(null);
  const [isDraggingFile, setIsDraggingFile] = useState<boolean>(false);
  const mutateSingleFileUpload = useMutateDDUploadSingleFile();

  const handleClose = (didUpload, msg) => {
    onClosing(didUpload, msg);
    setTimeout(() => {
      document.body.style.pointerEvents = "auto";
    }, 500);
  };
  const handleButtonClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };
  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { files } = e.target;
    if (files) {
      handleFiles(files, true);
    }
  };
  const handleFiles = async (files: any, fileWasDraggedIn: boolean) => {
    const uploadedFile = Array.from(files)[0] as any;
    setFilePendingUpload(uploadedFile);
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    setIsDraggingFile(true);
    e.preventDefault();
    e.stopPropagation();
  };
  const handleDragExit = (e: React.DragEvent<HTMLDivElement>) => {
    setIsDraggingFile(false);
    e.preventDefault();
    e.stopPropagation();
  };
  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    setIsDraggingFile(false);
    e.preventDefault();
    e.stopPropagation();
    const { files } = e.dataTransfer;
    handleFiles(files, true);
  };
  const doUpload = () => {
    mutateSingleFileUpload.mutate({
      data: {
        dd_id: dd_id,
        folder_id: folder_id,
      },
      file: filePendingUpload,
    });
  };
  useEffect(() => {
    if (!mutateSingleFileUpload.isSuccess) return;

    handleClose(true, `File ${filePendingUpload.name} was uploaded`);
  }, [mutateSingleFileUpload.isSuccess]);

  const handleDialogClose = (opening) => {
    if (opening) return;

    onClosing(false, null);
  };
  const draggingStyle = !isDraggingFile
    ? {}
    : {
        backgroundColor: "#E1E1E1", //bg-alchemySecondaryLightGrey
        transition: "0.5s all ease 0s",
        WebkitTransition: "0.5s all ease 0s",
        MozTransition: "0.5s all ease 0s",
        msTransition: "0.5s all ease 0s",
        borderWidth: "3px",
        borderStyle: "solid",
      };
  return (
    <>
      <Dialog open={show} onOpenChange={handleDialogClose}>
        <DialogContent className="w-[500px]">
          <DialogHeader>
            {header}
            <DialogDescription></DialogDescription>
          </DialogHeader>

          <div>
            <div
              className="border-2 border-dotted shadow-md h-[150px] cursor-pointer border-black rounded-xl"
              onClick={handleButtonClick}
              onDragLeave={handleDragExit}
              onDragOver={handleDragOver}
              onDrop={handleDrop}
              style={draggingStyle}
            >
              <div className="pt-2">
                <div className="w-full text-center inline-block pt-12">
                  <span className="text-black font-bold">
                    <>
                      <span className="underline">Click to upload</span> or drag
                      and drop
                    </>
                  </span>
                  <div className="italic text-sm pt-2">
                    {filePendingUpload?.name}
                  </div>
                </div>
              </div>
            </div>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept={`.pdf`}
            className="hidden"
            onChange={handleFileInputChange}
            multiple
          />
          <DialogFooter className="">
            <Button
              onClick={doUpload}
              disabled={mutateSingleFileUpload.isPending || !filePendingUpload}
            >
              {mutateSingleFileUpload.isPending && (
                <Loader2 className="animate-spin" />
              )}
              Upload
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                onClosing(false, null);
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
