// File: ui/src/pages/OpinionWriter/AppSideBar.tsx

"use client";

import * as React from "react";
import { SquareTerminal, FileEdit } from "lucide-react";

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
} from "@/components/ui/sidebar";
import { NavMain } from "./NavMain";
import { NavUser } from "./NavUser";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { useGetUser } from "@/hooks/useGetUser";
import { useGetOpinions } from "@/hooks/useGetOpinions";
import { useNavigate } from "react-router-dom";
import { useGetDDListing } from "@/hooks/useGetDDListing";
import { useGetWizardDrafts } from "@/hooks/useWizardDraft";
import { TRANSACTION_TYPE_INFO, TransactionTypeCode } from "../DD/Wizard/types";

export function AppSidebar({
  isOpinion = true,
  onResumeWizardDraft,
  ...props
}: {
  isOpinion?: boolean;
  onResumeWizardDraft?: (draftId: string) => void;
} & React.ComponentProps<typeof Sidebar>) {
  const { data: user } = useGetUser();
  const { data: opinions } = useGetOpinions(isOpinion); // Only fetch when in Opinion mode
  const { data: dds } = useGetDDListing("involves_me");
  const { data: wizardDrafts } = useGetWizardDrafts();
  const navigate = useNavigate();

  // Build DD items - completed projects + incomplete wizard drafts
  const ddItems = React.useMemo(() => {
    const items: { title: string; id: string; isDraft?: boolean; onClick: (id: string) => void }[] = [];

    // Add completed DD projects
    if (dds?.due_diligences) {
      dds.due_diligences.forEach((dd: { id: string; name: string; transaction_type?: string }) => {
        // Get transaction type info if available
        const typeCode = dd.transaction_type as TransactionTypeCode | undefined;
        const typeInfo = typeCode ? TRANSACTION_TYPE_INFO[typeCode] : null;
        const displayTitle = typeInfo
          ? `${dd.name} – ${typeInfo.name}`
          : dd.name;

        items.push({
          title: displayTitle,
          id: dd.id,
          isDraft: false,
          onClick: (evtData) => {
            navigate(`/dd?id=${evtData}`);
          },
        });
      });
    }

    // Add incomplete wizard drafts (with visual indicator)
    if (wizardDrafts && wizardDrafts.length > 0) {
      wizardDrafts.forEach((draft) => {
        items.push({
          title: `📝 ${draft.transactionName || "Untitled Draft"} (Draft)`,
          id: draft.id!,
          isDraft: true,
          onClick: (evtData) => {
            // Navigate to DD page with draft parameter to trigger wizard
            if (onResumeWizardDraft) {
              onResumeWizardDraft(evtData);
            } else {
              navigate(`/dd?resumeDraft=${evtData}`);
            }
          },
        });
      });
    }

    return items;
  }, [dds, wizardDrafts, navigate, onResumeWizardDraft]);

  const data = {
    user: {
      name: (user as any)?.name,
      email: (user as any)?.email,
      avatar: "/alchemy_logo.png",
    },
    navMain: [
      {
        title: "Your history",
        url: "#",
        icon: SquareTerminal,
        isActive: true,
        items: isOpinion
          ? opinions?.map((opinion) => {
              return {
                title: opinion.title,
                id: opinion.id,
                onClick: (evtData) => {
                  navigate(`/opinion?id=${evtData}`);
                },
              };
            })
          : ddItems,
      },
    ],
  };

  return (
    <Sidebar collapsible="icon" {...props} className="border-none">
      <SidebarHeader className="bg-alchemyPrimaryNavyBlue p-0">
        {/* <TeamSwitcher teams={data.teams} /> */}
        <div className="grid grid-cols-[50px_1fr] p-2">
          <div>
            <Avatar
              className="h-8 w-8 rounded-lg cursor-pointer"
              onClick={() => {
                navigate("/activity");
              }}
            >
              <AvatarImage src="alchemy_logo.png" />
              <AvatarFallback className="rounded-lg"></AvatarFallback>
            </Avatar>
          </div>
          <div
            className="pt-[2px] text-lg text-left cursor-pointer text-white"
            onClick={() => {
              navigate("/activity");
            }}
          >
            Alchemy Law Africa
          </div>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <NavMain items={data.navMain} />
        {/* <NavProjects projects={data.projects} /> */}
      </SidebarContent>
      <SidebarFooter>
        <NavUser user={data.user} />
      </SidebarFooter>
      {/* <SidebarRail /> */}
    </Sidebar>
  );
}
