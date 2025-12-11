import React from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { MoreHorizontal } from "lucide-react";

// Sample document data with error statuses and explanations
// const errorDocuments = [
//   {
//     id: 1,
//     name: "Supplier Agreement - ABC Corp.tiff",
//     errorMessage: "Unable to read the file",
//   },
//   {
//     id: 2,
//     name: "Employee Contract - John Doe.docx",
//     errorMessage: "No content found",
//   },
//   {
//     id: 3,
//     name: "Employee Contract - John Doe.docx",
//     errorMessage: "Possible duplicate",
//   },
//   {
//     id: 4,
//     name: "Employment contract.docx",
//     errorMessage: "Language is French, only English supported",
//   },
// ];

export function DocumentErrors({ errors }) {
  return (
    <div className="p-6 mx-auto">
      <div className="bg-white shadow-md rounded-lg p-4">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-1/4">Document Name</TableHead>
              <TableHead className="w-1/4">Location</TableHead>
              <TableHead className="w-1/4 text-center">Error</TableHead>
              <TableHead className="w-1/4 text-center">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {errors.map((doc) => (
              <TableRow key={doc.id}>
                <TableCell>{doc.name}</TableCell>
                <TableCell>{doc.path}</TableCell>
                <TableCell className="text-center">
                  <Badge className="bg-red-500 text-white">
                    {doc.errorMessage}
                  </Badge>
                </TableCell>
                <TableCell className="text-center">
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button aria-haspopup="true" size="icon" variant="ghost">
                        <MoreHorizontal className="h-4 w-4" />
                        <span className="sr-only">Toggle menu</span>
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuLabel>Actions</DropdownMenuLabel>
                      <DropdownMenuItem>Delete</DropdownMenuItem>
                      <DropdownMenuItem>
                        Exclude from future interaction
                      </DropdownMenuItem>
                      <DropdownMenuItem>View</DropdownMenuItem>
                      <DropdownMenuItem>
                        Copy information into clipboard
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

export default DocumentErrors;
