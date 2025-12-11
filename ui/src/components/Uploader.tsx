import { useMutateUploadFile } from "@/hooks/useMutateUploadFile";
import { useEffect, useRef, useState } from "react";
import { UploadCloud } from "./UploadCloud";
import { CircleCheckBig } from "lucide-react";
import { Button } from "./ui/button";
import { opinionDocumentTypes } from "@/lib/utils";

export function Uploader({ data, onUploadedSuccessfully }) {
  const [isDraggingFile, setIsDraggingFile] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [currentFileName, setCurrentFileName] = useState<string>(null);
  const [newDocumentId, setNewDocumentId] = useState<string>(null);
  const [uploadError, setUploadError] = useState<string>(null);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const toggleItem = (item: string) => {
    setSelectedTags(
      (prev) =>
        prev.includes(item)
          ? prev.filter((i) => i !== item) // remove if already selected
          : [...prev, item] // add if not selected
    );
  };

  const uploadFile = useMutateUploadFile();
  const draggingStyle = !isDraggingFile
    ? {}
    : {
        backgroundColor: "#0c1942",
        transition: "0.5s all ease 0s",
        WebkitTransition: "0.5s all ease 0s",
        MozTransition: "0.5s all ease 0s",
        msTransition: "0.5s all ease 0s",
        borderWidth: "3px",
        borderStyle: "solid",
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
  // Function to handle drop event
  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    setIsDraggingFile(false);

    e.preventDefault();
    e.stopPropagation();
    const { files } = e.dataTransfer;
    handleFiles(files, true);
  };

  const handleButtonClick = () => {
    setUploadError(null);
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
  const reset = () => {
    setUploadError(null);
    setNewDocumentId(null);
    setCurrentFileName(null);
  };
  const handleFiles = async (files: any, fileWasDraggedIn: boolean) => {
    reset();
    if (Array.from(files).length > 1) {
      setUploadError("Please only upload a single file at a time.");
      return;
    }

    const uploadedFile = Array.from(files)[0] as any;

    // const fileSizeInKB = Math.round(uploadedFile.size / 1024 / 1024); // Convert to MB
    // if (fileSizeInKB > 4) {
    //   setError(`Uploaded documents need to be below 4 Megabytes.`);
    //   return;
    // }
    setCurrentFileName(uploadedFile.name);

    uploadFile.mutate({
      file: uploadedFile,
      data: {
        ...data,
        tags: selectedTags,
      },
    });
    // setError(null); // Reset error state
  };
  useEffect(() => {
    if (uploadFile.isError) {
      console.log(uploadFile.error);
      setUploadError("There was a problem uploading your document");
    }
  }, [uploadFile.isError]);

  useEffect(() => {
    if (uploadFile.isSuccess) {
      const docId = (uploadFile.data.data as any).doc_id;
      setNewDocumentId(docId);
      onUploadedSuccessfully(docId);
    }
  }, [uploadFile.isSuccess]);
  return (
    <div>
      <div
        onDragLeave={handleDragExit}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        <div
          className="border-2 border-dotted shadow-md h-[150px] cursor-pointer border-black rounded-xl grid place-items-center"
          style={draggingStyle}
          onClick={handleButtonClick}
        >
          {uploadError && <div className="text-black">{uploadError}</div>}
          {uploadFile.isPending && (
            <span className="text-sx bg-gradient-to-r from-black via-gray-100 to-black bg-clip-text text-transparent animate-shimmerText bg-[length:200%_100%]">
              Busy uploading and indexing {currentFileName}
            </span>
          )}
          {!uploadFile.isPending && !uploadError && (
            <div className="flex flex-col items-center gap-3">
              <div>
                <UploadCloud />
              </div>
              <div>Click here or drag a file to add it</div>
            </div>
          )}
          {uploadFile.isSuccess && (
            <div className="flex items-center gap-3">
              <div>
                <CircleCheckBig className="text-green-600" />
              </div>
              <div className="pt-2">
                <div className="text-xs">Uploaded {currentFileName}</div>
                {!uploadFile?.data.data.was_indexed && (
                  <div className="text-xs italic text-center">
                    The file is busy being indexed
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept={`.pdf,.docx`}
          onChange={handleFileInputChange}
          className="hidden"
          multiple
        />
      </div>
      <div>
        <div className="pt-2 text-lg font-bold">
          Select how to categorise new documents
        </div>
        <div className="flex flex-wrap gap-2 py-4">
          {opinionDocumentTypes.map((tag) => {
            const isSelected = selectedTags.includes(tag.value);

            return (
              <Button
                key={tag.value}
                className={`px-4 py-2 text-black rounded border ${
                  isSelected ? `${tag.colour}` : `bg-gray-100`
                }`}
                onClick={() => {
                  toggleItem(tag.value);
                }}
              >
                {tag.label}
              </Button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
