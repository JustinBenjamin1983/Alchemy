import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { MoreHorizontal } from "lucide-react";
import { useState } from "react";

type RiskLevel = "Red" | "Amber";

type Finding = {
  documentName: string;
  documentLocation: string;
  riskClause: string;
  identifiedInfo: string;
  riskLevel: RiskLevel;
};

const initialFindings: Finding[] = [
  {
    documentName: "Share Purchase Agreement",
    documentLocation: "Data Room / Legal / SPA.pdf",
    riskClause:
      "Are the shares being sold subject to any encumbrances or security?",
    identifiedInfo:
      "Clause 6.4 indicates that 25% of shares are pledged as collateral to ABC Bank.",
    riskLevel: "Red",
  },
  {
    documentName: "Balance Sheet Report - 2023",
    documentLocation: "Data Room / Financials / BS_2023.pdf",
    riskClause: "Does the target company’s assets exceed its liabilities?",
    identifiedInfo:
      "As of Dec 2023, total liabilities exceeded assets by $1.2M.",
    riskLevel: "Red",
  },
  {
    documentName: "Corporate Guarantees Register",
    documentLocation: "Data Room / Finance / Guarantees.pdf",
    riskClause:
      "Has the target company or any other person provided security for the debts of the target company? If so, provide details of the security given and the person that gave the security.",
    identifiedInfo:
      "Director John Smith personally guaranteed a $500K loan from First Bank.",
    riskLevel: "Amber",
  },
  {
    documentName: "Lease Agreements Summary",
    documentLocation: "Data Room / Property / Leases.xlsx",
    riskClause:
      "Provide a summary of each lease agreement which includes the duration of each lease agreement, the lessor, the lessee and the premises being let.",
    identifiedInfo:
      "HQ lease: 5 years, Lessor: Main Property Ltd, Lessee: TargetCo, Premises: 45 Brick Ln, London.",
    riskLevel: "Amber",
  },
];

export default function Findings() {
  const [findings, setFindings] = useState<Finding[]>(initialFindings);

  const handleRemove = (index: number) => {
    const updated = [...findings];
    updated.splice(index, 1);
    setFindings(updated);
  };

  const handleChangeRisk = (index: number) => {
    const updated = [...findings];
    updated[index].riskLevel =
      updated[index].riskLevel === "Red" ? "Amber" : "Red";
    setFindings(updated);
  };

  const handleOpenDocument = (docPath: string) => {
    // Placeholder: implement file open logic
    alert(`Open document at: ${docPath}`);
  };

  return (
    <div className="p-6 space-y-4">
      {/* <h2 className="text-xl font-semibold">Due Diligence Findings</h2> */}
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Document Name</TableHead>
            <TableHead>Location</TableHead>
            <TableHead>Risk Clause</TableHead>
            <TableHead>Identified Information</TableHead>
            <TableHead>Risk Level</TableHead>
            <TableHead>Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {findings.map((finding, index) => (
            <TableRow key={index}>
              <TableCell>{finding.documentName}</TableCell>
              <TableCell className="text-sm text-muted-foreground">
                {finding.documentLocation}
              </TableCell>
              <TableCell>{finding.riskClause}</TableCell>
              <TableCell>{finding.identifiedInfo}</TableCell>
              <TableCell>
                <Badge
                  className={
                    finding.riskLevel === "Red"
                      ? "bg-red-600 text-white"
                      : "bg-yellow-500 text-white"
                  }
                >
                  {finding.riskLevel}
                </Badge>
              </TableCell>
              <TableCell>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon">
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={() => handleChangeRisk(index)}>
                      Change risk rating
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() =>
                        handleOpenDocument(finding.documentLocation)
                      }
                    >
                      Open Document
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => handleRemove(index)}>
                      Remove Finding
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
