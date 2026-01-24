// File: ui/src/hooks/useDevFileUpload.ts
// Hook for uploading files to local storage in dev mode

import { useMutation } from "@tanstack/react-query";
import { useAxiosWithAuth } from "./useAxiosWithAuth";

interface DevFileUploadResult {
  success: boolean;
  localPath: string;
  filename: string;
  size: number;
}

export function useDevFileUpload() {
  const axios = useAxiosWithAuth();

  async function uploadFile({
    file,
    targetPath,
  }: {
    file: File;
    targetPath: string;
  }): Promise<DevFileUploadResult> {
    // Read file as ArrayBuffer
    const arrayBuffer = await file.arrayBuffer();

    // Send raw binary data with headers for path/filename
    const response = await axios.put("/dd-file-upload-dev", arrayBuffer, {
      headers: {
        "Content-Type": "application/octet-stream",
        "X-Local-Path": targetPath,
        "X-Filename": file.name,
      },
    });

    return response.data;
  }

  return useMutation({
    mutationFn: uploadFile,
  });
}
