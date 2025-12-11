import React, { useEffect, useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { CheckCircle2Icon, MoreHorizontal } from "lucide-react";
import { useMutateGetLink } from "@/hooks/useMutateGetLink";
import QandA from "./QandA";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

export function SearchResults({
  dd_id,
  results,
  keyword_only_search,
  keyword,
}) {
  const [expandedRow, setExpandedRow] = useState<number | null>(null);
  const mutateGetLink = useMutateGetLink();
  const [showQandA, setShowQandA] = useState<boolean>(false);
  const [qandAData, setQandAData] = useState<{
    dd_id: string;
    folder_id?: string;
    doc_id?: string;
    folderName?: string;
    fileName?: string;
  }>(null);
  useEffect(() => {
    if (!mutateGetLink.isSuccess) return;
    window.open(mutateGetLink.data.data.url, "_blank", "noopener,noreferrer");
  }, [mutateGetLink.isSuccess]);

  const viewFile = (doc_id) => {
    mutateGetLink.mutate({ doc_id: doc_id, is_dd: true });
  };
  const toggleRow = (id: number) => {
    setExpandedRow(expandedRow === id ? null : id);
  };
  const askAQuestion = (doc_id) => {
    setQandAData({ dd_id, doc_id });
    setShowQandA(true);
  };
  const copyInfo = (result) => {
    navigator.clipboard.writeText(
      `Document name: ${result.filename}\nFolder: ${result.folder_path}\nPage: ${result.page_number}\nContent found:${result.content}`
    );
  };
  return (
    <div className="w-full">
      {results?.length != 0 && (
        <>
          <Alert className="w-[50%] border-none">
            <CheckCircle2Icon />
            <AlertTitle className="[&>svg~*]:pl-[20px]">
              Search Hints
            </AlertTitle>
            <AlertDescription>
              <ul className="list-inside list-disc text-sm">
                <li>
                  Click on any of the results to see the text from the document
                </li>
                {keyword_only_search &&
                  keyword?.indexOf('"') === -1 &&
                  keyword?.indexOf(" ") !== -1 && (
                    <li>
                      You're searching for multiple keywords - try and wrap that
                      in quotes
                    </li>
                  )}
              </ul>
            </AlertDescription>
          </Alert>

          <QandA
            onClosing={() => setShowQandA(false)}
            show={showQandA}
            data={qandAData}
          />
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Document Name</TableHead>
                <TableHead>Page Number</TableHead>
                <TableHead>Document Location</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {results?.map((result) => (
                <React.Fragment key={result.id}>
                  {/* Main Row */}
                  <TableRow
                    className="cursor-pointer"
                    onClick={() => toggleRow(result.result_id)}
                    key={result.result_id}
                  >
                    <TableCell className="font-semibold">
                      {result.filename}
                    </TableCell>
                    <TableCell>{result.page_number}</TableCell>
                    <TableCell className="text-gray-600">
                      {result.folder_path}
                    </TableCell>

                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            aria-haspopup="true"
                            size="icon"
                            variant="ghost"
                          >
                            <MoreHorizontal className="h-4 w-4" />
                            <span className="sr-only">Toggle menu</span>
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuLabel>Actions</DropdownMenuLabel>
                          <DropdownMenuItem
                            onClick={() => askAQuestion(result.doc_id)}
                          >
                            Ask questions
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={() => viewFile(result.doc_id)}
                          >
                            View
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => copyInfo(result)}>
                            Copy Info
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>

                  {/* Expanded Row - Document Content Preview */}
                  {expandedRow === result.result_id && (
                    <TableRow>
                      <TableCell colSpan={4} className="p-4">
                        <span className="text-2xl inline">&ldquo;</span>
                        {keyword_only_search &&
                          result.content
                            .split(
                              new RegExp(
                                `(${keyword.replaceAll('"', "")})`,
                                "gi"
                              )
                            )
                            .map((part, index) =>
                              part.toLowerCase() ===
                              keyword.replaceAll('"', "").toLowerCase() ? (
                                <span
                                  key={index}
                                  className="bg-yellow-300 px-1"
                                >
                                  {part}
                                </span>
                              ) : (
                                <span key={index}>{part}</span>
                              )
                            )}
                        {!keyword_only_search && <>{result.content}</>}
                        <span className="text-2xl inline">&rdquo;</span>
                      </TableCell>
                    </TableRow>
                  )}
                </React.Fragment>
              ))}
            </TableBody>
          </Table>
        </>
      )}
      {results?.length === 0 && (
        <div className="text-lg text-center pt-4">No results found</div>
      )}
    </div>
  );
}
