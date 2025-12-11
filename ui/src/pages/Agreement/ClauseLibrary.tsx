import { useRef, useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loader2, Download, Trash2 } from "lucide-react";

export function ClauseLibrary() {
  const [clauses, setClauses] = useState<
    { id: string; name: string; url: string }[]
  >([]);
  const [selectedClauseUrl, setSelectedClauseUrl] = useState<string | null>(
    null
  );
  const [fileToUpload, setFileToUpload] = useState<File | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const API_BASE = import.meta.env.VITE_API_BASE_URL;

  useEffect(() => {
    fetchClauses();
  }, []);

  const fetchClauses = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/clauses`);
      const data = await response.json();
      setClauses(data.clauses);
    } catch (error) {
      console.error("Failed to fetch clauses", error);
    }
  };

  const uploadClause = async () => {
    if (!fileToUpload) return;
    const formData = new FormData();
    formData.append("file", fileToUpload);

    setUploading(true);
    try {
      const res = await fetch(`${API_BASE}/api/upload_clause`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      console.log(data);
      fetchClauses();
      setFileToUpload(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = ""; // clear file input
      }
    } catch (err) {
      console.error("Upload failed", err);
    } finally {
      setUploading(false);
    }
  };

  const deleteClause = async (id: string) => {
    setDeletingId(id);
    try {
      await fetch(`${API_BASE}/api/clauses/${id}`, {
        method: "DELETE",
      });
      fetchClauses();
    } catch (err) {
      console.error("Failed to delete clause", err);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="p-8 grid grid-cols-[400px_1fr] gap-4">
      <div>
        <h2 className="text-2xl font-bold mb-4">Clause Library</h2>

        <div className="flex items-center gap-2 mb-4">
          <Input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            onChange={(e) => {
              if (e.target.files?.[0]) setFileToUpload(e.target.files[0]);
            }}
          />
          <Button
            onClick={uploadClause}
            disabled={!fileToUpload || uploading}
            className="px-4 py-2"
          >
            {uploading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <span className="text-2xl">+</span>
            )}
          </Button>
        </div>

        <table className="w-full border">
          <thead>
            <tr className="bg-gray-100">
              <th className="text-left p-2">Name</th>
              <th className="p-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {clauses.map((clause) => (
              <tr key={clause.id} className="border-t">
                <td
                  className="p-2 cursor-pointer hover:underline"
                  onClick={() => setSelectedClauseUrl(clause.url)}
                >
                  {clause.name}
                </td>
                <td className="p-2 flex gap-2 justify-center">
                  <Button
                    size="icon"
                    variant="ghost"
                    className="bg-primary"
                    onClick={() => window.open(clause.url, "_blank")}
                  >
                    <Download className="w-4 h-4 " />
                  </Button>
                  <Button
                    size="icon"
                    variant="destructive"
                    onClick={() => deleteClause(clause.id)}
                    disabled={deletingId === clause.id}
                  >
                    {deletingId === clause.id ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Trash2 className="w-4 h-4" />
                    )}
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div>
        {selectedClauseUrl ? (
          <iframe
            src={selectedClauseUrl}
            className="w-full h-[80vh] border rounded"
            title="Clause PDF"
          />
        ) : (
          <p>Select a clause to preview the PDF</p>
        )}
      </div>
    </div>
  );
}
