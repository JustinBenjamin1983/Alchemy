import { useRef, useState } from "react";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { AgreementSideBar } from "./AgreementSideBar";
import { ClauseLibrary } from "./ClauseLibrary";
import { NewAgreement } from "./NewAgreement";

export function AgreementMain() {
  const [currentView, setCurrentView] = useState<
    "new_agreement" | "clause_library"
  >("new_agreement");
  const [selectedAgreementId, setSelectedAgreementId] = useState<string | null>(
    null
  );

  const newAgreementRef = useRef<any>(null);

  return (
    <SidebarProvider>
      <AgreementSideBar
        onSelectView={(view) => {
          if (view === "clause_library" && newAgreementRef.current) {
            newAgreementRef.current.resetAgreementState();
          }
          if (view === "new_agreement") {
            setSelectedAgreementId(null);
          }
          setCurrentView(view);
        }}
        onSelectAgreement={(id) => {
          setCurrentView("new_agreement");
          setSelectedAgreementId(id);
        }}
      />

      <SidebarInset>
        {currentView === "new_agreement" && (
          <NewAgreement
            ref={newAgreementRef}
            existingAgreementId={selectedAgreementId}
          />
        )}
        {currentView === "clause_library" && <ClauseLibrary />}
      </SidebarInset>
    </SidebarProvider>
  );
}
