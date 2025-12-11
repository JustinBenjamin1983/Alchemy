import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Folder, Folders, MoreHorizontal } from "lucide-react";
import { useEffect, useState } from "react";
import SingleTextPrompt from "../../../components/SingleTextPrompt";
import { useMutateDDFolderAdd } from "@/hooks/useMutateDDFolderAdd";
import { AlertCheckFor } from "@/components/AlertCheckFor";
import { useMutateDDFolderDelete } from "@/hooks/useMutateDDFolderDelete";

export default function Hierarchy({
  dd_id,
  folders,
  onSelect,
  dontAutoSelect,
  selectedFolderId,
}: {
  dd_id: string;
  folders: any;
  onSelect: any;
  dontAutoSelect?: boolean;
  selectedFolderId?: string;
}) {
  const mutateFolderAdd = useMutateDDFolderAdd();
  const mutateFolderDelete = useMutateDDFolderDelete();

  const [selectedFolder, setSelectedFolder] = useState<{
    folder_id;
    folder_name;
  }>(null);
  const [showFolderAdder, setShowFolderAdder] = useState<boolean>(false);
  const [showFolderDeleter, setShowFolderDeleter] = useState<boolean>(false);

  useEffect(() => {
    if (!folders) return;
    if (!dontAutoSelect && !selectedFolderId) {
      setSelectedFolder({
        folder_id: folders[0].folder_id,
        folder_name: folders[0].folder_name,
      });
    } else if (selectedFolderId) {
      const incomingSelectedFolder = folders.find(
        (f) => f.folder_id === selectedFolderId
      );
      setSelectedFolder({
        folder_id: incomingSelectedFolder.folder_id,
        folder_name: incomingSelectedFolder.folder_name,
      });
    }
  }, [folders]);

  useEffect(() => {
    if (selectedFolder) onSelect(selectedFolder);
  }, [selectedFolder]);

  const folderAdderClosing = (value) => {
    setShowFolderAdder(false);
    mutateFolderAdd.mutate({
      dd_id: dd_id,
      folder_name: value,
      parent_folder_id: selectedFolder?.folder_id,
    });
  };

  useEffect(() => {
    if (!mutateFolderDelete.isSuccess) return;

    setShowFolderDeleter(false);
  }, [mutateFolderDelete.isSuccess]);
  const deleteFolder = () => {
    mutateFolderDelete.mutate({ dd_id, folder_id: selectedFolder.folder_id });
  };
  return (
    <div className="[&>div]:pt-2 [&>div]:cursor-pointer text-sm">
      {folders && (
        <>
          <AlertCheckFor
            title="Delete folder"
            blurb={`Are you sure you want to delete ${selectedFolder?.folder_name}`}
            show={showFolderDeleter}
            okText={"Yes, delete it"}
            onOK={deleteFolder}
            cancelText={"No"}
            onCancel={() => setShowFolderDeleter(false)}
          />
          {[...folders]
            .sort((a, b) => {
              const pathA = a.hierarchy.split("/").filter(Boolean);
              const pathB = b.hierarchy.split("/").filter(Boolean);

              for (let i = 0; i < Math.max(pathA.length, pathB.length); i++) {
                if (pathA[i] !== pathB[i]) {
                  return (pathA[i] || "").localeCompare(pathB[i] || "");
                }
              }
              return 0;
            })
            .map((f) => {
              return (
                <div
                  className={`grid grid-cols-2 xl:grid-cols-[30px_1fr] select-none pl-[${
                    f.level * 16
                  }px]`}
                  style={{ paddingLeft: `${f.level * 16}px` }}
                  key={f.folder_id}
                  onClick={() => {
                    setSelectedFolder({
                      folder_id: f.folder_id,
                      folder_name: f.folder_name,
                    });
                  }}
                >
                  <div className="">
                    {f.has_children ? (
                      <Folders
                        className={` ${
                          f.folder_id === selectedFolder?.folder_id
                            ? "text-black"
                            : "text-gray-400"
                        }`}
                      />
                    ) : (
                      <Folder
                        className={` ${
                          f.folder_id === selectedFolder?.folder_id
                            ? "text-black"
                            : "text-gray-400"
                        }`}
                      />
                    )}
                  </div>
                  <div
                    className={`pl-2 ${
                      f.folder_id === selectedFolder?.folder_id
                        ? "font-bold"
                        : ""
                    }`}
                  >
                    {f.folder_name}
                  </div>
                </div>
              );
            })}
          <div>
            <SingleTextPrompt
              show={showFolderAdder}
              header={
                selectedFolder
                  ? `Add a new folder under ${selectedFolder.folder_name}`
                  : "Add a new folder"
              }
              label={"New folder"}
              onClosing={folderAdderClosing}
            />
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button aria-haspopup="true" size="icon" variant="ghost">
                  <MoreHorizontal className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>Actions</DropdownMenuLabel>
                <DropdownMenuItem
                  className="cursor-pointer"
                  onClick={() => {
                    setShowFolderAdder(true);
                  }}
                >
                  Add folder
                </DropdownMenuItem>
                <DropdownMenuItem
                  className="cursor-pointer"
                  onClick={() => {
                    setShowFolderDeleter(true);
                  }}
                >
                  Delete folder
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </>
      )}
    </div>
  );
}
