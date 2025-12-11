import { useEffect, useState } from "react";
import Hierarchy from "./Hierarchy";

import FileLister from "./FileLister";
import QandA from "../QandA";
import FileUploadDialog from "../FileUploadDialog";

export function DocListing({ folders, dd_id }) {
  const [selectedFolder, setSelectedFolder] = useState<{
    folder_id;
    folder_name;
  }>(null);

  const [showFileUploader, setShowFileUploader] = useState<boolean>(false);
  const [fileJustUploaded, setFileJustUploaded] = useState<string>(null);

  const [showQandA, setShowQandA] = useState<boolean>(false);
  const [qandAData, setQandAData] = useState<{
    dd_id: string;
    folder_id?: string;
    doc_id?: string;
    folderName?: string;
    fileName?: string;
  }>(null);

  const addAnotherDoc = () => {
    setShowFileUploader(true);
  };
  const fileUploaderClosing = (didUpload, msg) => {
    didUpload && setFileJustUploaded(msg);
    setShowFileUploader(false);
  };

  useEffect(() => {
    setFileJustUploaded(null);
  }, [selectedFolder]);
  return (
    <>
      <FileUploadDialog
        header={`Add another document to ${selectedFolder?.folder_name}`}
        dd_id={dd_id}
        folder_id={selectedFolder?.folder_id}
        show={showFileUploader}
        onClosing={fileUploaderClosing}
      />
      <div className="pt-4 pl-4">
        <div className="grid grid-cols-[25%_1fr] gap-4">
          <div className="pt-6">
            <Hierarchy
              dd_id={dd_id}
              folders={folders}
              onSelect={(folderIdAndName) => {
                {
                  setSelectedFolder(folderIdAndName);
                }
              }}
            />
          </div>
          <div>
            <FileLister
              dd_id={dd_id}
              subHeader={fileJustUploaded}
              folderId={selectedFolder?.folder_id}
              folderName={selectedFolder?.folder_name}
              files={
                folders?.find((f) => f.folder_id == selectedFolder?.folder_id)
                  ?.documents
              }
              addAnotherDoc={addAnotherDoc}
              chatWithDoc={(data) => {
                setQandAData({
                  dd_id,
                  doc_id: data.doc_id,
                  fileName: data.originalFileName,
                });
                setShowQandA(true);
              }}
              chatWithFolder={(data) => {
                setQandAData({
                  dd_id,
                  folderName: data.folderName,
                  folder_id: data.folderId,
                });
                setShowQandA(true);
              }}
            />
          </div>
          <QandA
            onClosing={() => setShowQandA(false)}
            show={showQandA}
            data={qandAData}
          />
        </div>
      </div>
    </>
  );
}
