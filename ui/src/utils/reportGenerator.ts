// File: ui/src/utils/reportGenerator.ts
import {
  Document,
  Packer,
  Paragraph,
  TextRun,
  Table,
  TableRow,
  TableCell,
  AlignmentType,
  HeadingLevel,
  BorderStyle,
  WidthType,
  ShadingType,
  LevelFormat,
} from "docx";
import { saveAs } from "file-saver";

interface Finding {
  finding_id?: string;
  perspective_risk_id?: string;
  finding_type?: "positive" | "negative" | "gap" | "neutral" | "informational";
  finding_status?: "New" | "Red" | "Amber" | "Green" | "Info" | "Deleted";
  confidence_score?: number;
  direct_answer?: string;
  phrase?: string;
  evidence_quote?: string;
  requires_action?: boolean;
  action_items?: string;
  missing_documents?: string;
  document: {
    id: string;
    original_file_name: string;
    folder: { path: string };
  };
  page_number?: number;
  finding_is_reviewed?: boolean;
  detail?: string;
  category?: string;
}

export async function generateDDReport(
  ddName: string,
  findings: Finding[],
  categories: string[]
): Promise<void> {
  // Filter out deleted findings
  const activeFindings = findings.filter((f) => f.finding_status !== "Deleted");

  // Helper functions
  const getTypeLabel = (type?: string) => {
    const labels: Record<string, string> = {
      positive: "Positive Finding",
      negative: "Risk Identified",
      gap: "Information Gap",
      neutral: "Neutral",
      informational: "Informational",
    };
    return labels[type || ""] || "Finding";
  };

  // Calculate summary statistics
  const totalFindings = activeFindings.length;
  const positiveCount = activeFindings.filter(
    (f) => f.finding_type === "positive" || f.finding_status === "Green"
  ).length;
  const redCount = activeFindings.filter(
    (f) => f.finding_status === "Red"
  ).length;
  const amberCount = activeFindings.filter(
    (f) => f.finding_status === "Amber"
  ).length;
  const gapCount = activeFindings.filter(
    (f) => f.finding_type === "gap"
  ).length;
  const requiresActionCount = activeFindings.filter(
    (f) => f.requires_action
  ).length;

  // Group findings by category
  const findingsByCategory: Record<string, Finding[]> = {};
  activeFindings.forEach((finding) => {
    const category = finding.category || "Uncategorized";
    if (!findingsByCategory[category]) {
      findingsByCategory[category] = [];
    }
    findingsByCategory[category].push(finding);
  });

  // Define table borders
  const tableBorder = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
  const cellBorders = {
    top: tableBorder,
    bottom: tableBorder,
    left: tableBorder,
    right: tableBorder,
  };

  // Setup numbering for bullet lists
  const numberingConfig = {
    config: [
      {
        reference: "bullet-list",
        levels: [
          {
            level: 0,
            format: LevelFormat.BULLET,
            text: "•",
            alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 720, hanging: 360 } } },
          },
        ],
      },
      {
        reference: "risk-bullets",
        levels: [
          {
            level: 0,
            format: LevelFormat.BULLET,
            text: "•",
            alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 720, hanging: 360 } } },
          },
        ],
      },
    ],
  };

  // Document styles
  const styles = {
    default: {
      document: {
        run: { font: "Arial", size: 24 },
      },
    },
    paragraphStyles: [
      {
        id: "Title",
        name: "Title",
        basedOn: "Normal",
        run: { size: 56, bold: true, color: "000000", font: "Arial" },
        paragraph: {
          spacing: { before: 240, after: 120 },
          alignment: AlignmentType.CENTER,
        },
      },
      {
        id: "Heading1",
        name: "Heading 1",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: { size: 32, bold: true, color: "000000", font: "Arial" },
        paragraph: { spacing: { before: 480, after: 240 }, outlineLevel: 0 },
      },
      {
        id: "Heading2",
        name: "Heading 2",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: { size: 28, bold: true, color: "1F2937", font: "Arial" },
        paragraph: { spacing: { before: 360, after: 180 }, outlineLevel: 1 },
      },
      {
        id: "Heading3",
        name: "Heading 3",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: { size: 26, bold: true, color: "374151", font: "Arial" },
        paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 2 },
      },
    ],
  };

  // Build document sections
  const children: (Paragraph | Table)[] = [];

  // TITLE PAGE
  children.push(
    new Paragraph({
      heading: HeadingLevel.TITLE,
      children: [new TextRun("Due Diligence Report")],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 120, after: 120 },
      children: [new TextRun({ text: ddName, size: 32, bold: true })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 240 },
      children: [
        new TextRun({
          text: `Generated: ${new Date().toLocaleDateString()}`,
          size: 22,
          color: "6B7280",
        }),
      ],
    }),
    new Paragraph({ children: [new TextRun("")], pageBreakBefore: true })
  );

  // EXECUTIVE SUMMARY
  children.push(
    new Paragraph({
      heading: HeadingLevel.HEADING_1,
      children: [new TextRun("Executive Summary")],
    }),
    new Paragraph({
      spacing: { after: 120 },
      children: [
        new TextRun({
          text: `This report presents the findings from the due diligence review of ${ddName}. A total of ${totalFindings} findings were identified across ${categories.length} categories.`,
        }),
      ],
    })
  );

  // Summary Statistics Table
  children.push(
    new Paragraph({
      heading: HeadingLevel.HEADING_2,
      children: [new TextRun("Summary Statistics")],
    }),
    new Table({
      columnWidths: [4680, 4680],
      margins: { top: 100, bottom: 100, left: 180, right: 180 },
      rows: [
        new TableRow({
          tableHeader: true,
          children: [
            new TableCell({
              borders: cellBorders,
              width: { size: 4680, type: WidthType.DXA },
              shading: { fill: "F3F4F6", type: ShadingType.CLEAR },
              children: [
                new Paragraph({
                  alignment: AlignmentType.CENTER,
                  children: [new TextRun({ text: "Metric", bold: true })],
                }),
              ],
            }),
            new TableCell({
              borders: cellBorders,
              width: { size: 4680, type: WidthType.DXA },
              shading: { fill: "F3F4F6", type: ShadingType.CLEAR },
              children: [
                new Paragraph({
                  alignment: AlignmentType.CENTER,
                  children: [new TextRun({ text: "Count", bold: true })],
                }),
              ],
            }),
          ],
        }),
        new TableRow({
          children: [
            new TableCell({
              borders: cellBorders,
              width: { size: 4680, type: WidthType.DXA },
              children: [
                new Paragraph({ children: [new TextRun("Total Findings")] }),
              ],
            }),
            new TableCell({
              borders: cellBorders,
              width: { size: 4680, type: WidthType.DXA },
              children: [
                new Paragraph({
                  alignment: AlignmentType.CENTER,
                  children: [new TextRun(totalFindings.toString())],
                }),
              ],
            }),
          ],
        }),
        new TableRow({
          children: [
            new TableCell({
              borders: cellBorders,
              width: { size: 4680, type: WidthType.DXA },
              children: [
                new Paragraph({ children: [new TextRun("Positive Findings")] }),
              ],
            }),
            new TableCell({
              borders: cellBorders,
              width: { size: 4680, type: WidthType.DXA },
              shading: { fill: "D1FAE5", type: ShadingType.CLEAR },
              children: [
                new Paragraph({
                  alignment: AlignmentType.CENTER,
                  children: [
                    new TextRun({
                      text: positiveCount.toString(),
                      color: "059669",
                      bold: true,
                    }),
                  ],
                }),
              ],
            }),
          ],
        }),
        new TableRow({
          children: [
            new TableCell({
              borders: cellBorders,
              width: { size: 4680, type: WidthType.DXA },
              children: [
                new Paragraph({
                  children: [new TextRun("Critical Risks (Red)")],
                }),
              ],
            }),
            new TableCell({
              borders: cellBorders,
              width: { size: 4680, type: WidthType.DXA },
              shading: { fill: "FEE2E2", type: ShadingType.CLEAR },
              children: [
                new Paragraph({
                  alignment: AlignmentType.CENTER,
                  children: [
                    new TextRun({
                      text: redCount.toString(),
                      color: "DC2626",
                      bold: true,
                    }),
                  ],
                }),
              ],
            }),
          ],
        }),
        new TableRow({
          children: [
            new TableCell({
              borders: cellBorders,
              width: { size: 4680, type: WidthType.DXA },
              children: [
                new Paragraph({
                  children: [new TextRun("Medium Risks (Amber)")],
                }),
              ],
            }),
            new TableCell({
              borders: cellBorders,
              width: { size: 4680, type: WidthType.DXA },
              shading: { fill: "FEF3C7", type: ShadingType.CLEAR },
              children: [
                new Paragraph({
                  alignment: AlignmentType.CENTER,
                  children: [
                    new TextRun({
                      text: amberCount.toString(),
                      color: "F59E0B",
                      bold: true,
                    }),
                  ],
                }),
              ],
            }),
          ],
        }),
        new TableRow({
          children: [
            new TableCell({
              borders: cellBorders,
              width: { size: 4680, type: WidthType.DXA },
              children: [
                new Paragraph({ children: [new TextRun("Information Gaps")] }),
              ],
            }),
            new TableCell({
              borders: cellBorders,
              width: { size: 4680, type: WidthType.DXA },
              children: [
                new Paragraph({
                  alignment: AlignmentType.CENTER,
                  children: [new TextRun(gapCount.toString())],
                }),
              ],
            }),
          ],
        }),
        new TableRow({
          children: [
            new TableCell({
              borders: cellBorders,
              width: { size: 4680, type: WidthType.DXA },
              children: [
                new Paragraph({ children: [new TextRun("Requires Action")] }),
              ],
            }),
            new TableCell({
              borders: cellBorders,
              width: { size: 4680, type: WidthType.DXA },
              shading: { fill: "FEF3C7", type: ShadingType.CLEAR },
              children: [
                new Paragraph({
                  alignment: AlignmentType.CENTER,
                  children: [
                    new TextRun({
                      text: requiresActionCount.toString(),
                      bold: true,
                    }),
                  ],
                }),
              ],
            }),
          ],
        }),
      ],
    }),
    new Paragraph({ children: [new TextRun("")], spacing: { after: 240 } })
  );

  // KEY RISKS SECTION
  if (redCount > 0 || amberCount > 0) {
    children.push(
      new Paragraph({
        heading: HeadingLevel.HEADING_2,
        children: [new TextRun("Key Risks Identified")],
      })
    );

    if (redCount > 0) {
      children.push(
        new Paragraph({
          heading: HeadingLevel.HEADING_3,
          children: [new TextRun({ text: "Critical Risks", color: "DC2626" })],
        })
      );

      const redFindings = activeFindings.filter(
        (f) => f.finding_status === "Red"
      );
      redFindings.forEach((finding) => {
        children.push(
          new Paragraph({
            numbering: { reference: "risk-bullets", level: 0 },
            children: [
              new TextRun({
                text: `${finding.category}: ${
                  finding.detail || "Risk identified"
                }`,
                bold: true,
              }),
            ],
          }),
          new Paragraph({
            indent: { left: 720 },
            spacing: { after: 120 },
            children: [
              new TextRun({
                text:
                  finding.phrase ||
                  finding.direct_answer ||
                  "See detailed findings",
                size: 22,
              }),
            ],
          })
        );
      });
    }

    if (amberCount > 0) {
      children.push(
        new Paragraph({
          heading: HeadingLevel.HEADING_3,
          children: [new TextRun({ text: "Medium Risks", color: "F59E0B" })],
        })
      );

      const amberFindings = activeFindings.filter(
        (f) => f.finding_status === "Amber"
      );
      amberFindings.forEach((finding) => {
        children.push(
          new Paragraph({
            numbering: { reference: "risk-bullets", level: 0 },
            children: [
              new TextRun({
                text: `${finding.category}: ${
                  finding.detail || "Risk identified"
                }`,
                bold: true,
              }),
            ],
          }),
          new Paragraph({
            indent: { left: 720 },
            spacing: { after: 120 },
            children: [
              new TextRun({
                text:
                  finding.phrase ||
                  finding.direct_answer ||
                  "See detailed findings",
                size: 22,
              }),
            ],
          })
        );
      });
    }

    children.push(
      new Paragraph({ children: [new TextRun("")], pageBreakBefore: true })
    );
  }

  // DETAILED FINDINGS BY CATEGORY
  children.push(
    new Paragraph({
      heading: HeadingLevel.HEADING_1,
      children: [new TextRun("Detailed Findings")],
    })
  );

  Object.entries(findingsByCategory).forEach(([category, categoryFindings]) => {
    children.push(
      new Paragraph({
        heading: HeadingLevel.HEADING_2,
        children: [new TextRun(category)],
      }),
      new Paragraph({
        spacing: { after: 120 },
        children: [
          new TextRun({
            text: `${categoryFindings.length} finding${
              categoryFindings.length !== 1 ? "s" : ""
            } in this category`,
            size: 22,
            color: "6B7280",
          }),
        ],
      })
    );

    categoryFindings.forEach((finding, index) => {
      const confidence = finding.confidence_score || 0.5;
      const confidencePercent = Math.round(confidence * 100);

      children.push(
        new Paragraph({
          heading: HeadingLevel.HEADING_3,
          children: [
            new TextRun(
              `Finding ${index + 1}: ${finding.detail || "Assessment"}`
            ),
          ],
        })
      );

      // Finding metadata
      const metadataItems = [];
      metadataItems.push(`Type: ${getTypeLabel(finding.finding_type)}`);
      if (finding.finding_status && finding.finding_status !== "New") {
        metadataItems.push(`Status: ${finding.finding_status}`);
      }
      metadataItems.push(`Confidence: ${confidencePercent}%`);

      children.push(
        new Paragraph({
          spacing: { after: 120 },
          children: [
            new TextRun({
              text: metadataItems.join(" | "),
              size: 20,
              color: "6B7280",
              italics: true,
            }),
          ],
        })
      );

      // Main finding text
      if (finding.direct_answer) {
        children.push(
          new Paragraph({
            spacing: { after: 120 },
            children: [
              new TextRun({ text: "Answer: ", bold: true }),
              new TextRun(finding.direct_answer),
            ],
          })
        );
      }

      if (finding.phrase) {
        children.push(
          new Paragraph({
            spacing: { after: 120 },
            children: [
              new TextRun({ text: "Finding: ", bold: true }),
              new TextRun(finding.phrase),
            ],
          })
        );
      }

      // Evidence quote
      if (finding.evidence_quote) {
        children.push(
          new Paragraph({
            spacing: { after: 120 },
            indent: { left: 360 },
            border: {
              left: { color: "D1D5DB", size: 6, style: BorderStyle.SINGLE },
            },
            children: [
              new TextRun({
                text: finding.evidence_quote,
                italics: true,
                color: "4B5563",
              }),
            ],
          })
        );
      }

      // Action items
      if (finding.requires_action && finding.action_items) {
        try {
          const actions = JSON.parse(finding.action_items || "[]");
          if (actions.length > 0) {
            children.push(
              new Paragraph({
                spacing: { before: 120, after: 60 },
                children: [
                  new TextRun({
                    text: "Required Actions:",
                    bold: true,
                    color: "D97706",
                  }),
                ],
              })
            );
            actions.forEach((action: string) => {
              children.push(
                new Paragraph({
                  numbering: { reference: "bullet-list", level: 0 },
                  children: [new TextRun(action)],
                })
              );
            });
          }
        } catch (e) {
          console.error("Error parsing action items:", e);
        }
      }

      // Source information
      children.push(
        new Paragraph({
          spacing: { before: 120, after: 240 },
          children: [
            new TextRun({ text: "Source: ", bold: true, size: 20 }),
            new TextRun({
              text: finding.document.original_file_name,
              size: 20,
            }),
            ...(finding.page_number
              ? [
                  new TextRun({
                    text: `, Page ${finding.page_number}`,
                    size: 20,
                  }),
                ]
              : []),
          ],
        })
      );
    });

    children.push(
      new Paragraph({ children: [new TextRun("")], spacing: { after: 120 } })
    );
  });

  // Create the document
  const doc = new Document({
    styles,
    numbering: numberingConfig,
    sections: [
      {
        properties: {
          page: {
            margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
          },
        },
        children,
      },
    ],
  });

  // Generate and download the document
  const blob = await Packer.toBlob(doc);
  const fileName = `DD_Report_${ddName.replace(/[^a-z0-9]/gi, "_")}_${
    new Date().toISOString().split("T")[0]
  }.docx`;
  saveAs(blob, fileName);
}
