// File: ui/src/pages/OpinionWriter/AppSideBar.tsx

"use client";

import * as React from "react";
import { SquareTerminal } from "lucide-react";

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

export function AppSidebar({
  isOpinion = true,
  ...props
}: {
  isOpinion?: boolean;
} & React.ComponentProps<typeof Sidebar>) {
  const { data: user } = useGetUser();
  const { data: opinions } = useGetOpinions();
  const { data: dds } = useGetDDListing("involves_me");
  console.log("dds", dds);
  const navigate = useNavigate();
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
          : dds?.due_diligences.map((dd) => {
              return {
                title: dd.name,
                id: dd.id,
                onClick: (evtData) => {
                  navigate(`/dd?id=${evtData}`);
                },
              };
            }),
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
