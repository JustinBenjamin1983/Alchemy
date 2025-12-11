"use client";

import * as React from "react";
import { SquareTerminal, FilePlus2, BookOpen } from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
} from "@/components/ui/sidebar";
import { NavMain } from "../OpinionWriter/NavMain";
import { NavUser } from "../OpinionWriter/NavUser";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { useGetUser } from "@/hooks/useGetUser";
import { useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";

export function AgreementSideBar({
  onSelectView,
  onSelectAgreement,
}: {
  onSelectView: (view: "new_agreement" | "clause_library") => void;
  onSelectAgreement: (id: string) => void;
}) {
  const { data: user } = useGetUser();
  const navigate = useNavigate();
  const [agreements, setAgreements] = useState<any[]>([]);
  const API_BASE = import.meta.env.VITE_API_BASE_URL;

  useEffect(() => {
    fetch(`${API_BASE}/api/list_agreements`)
      .then((res) => res.json())
      .then((data) => setAgreements(data))
      .catch(console.error);
  }, []);

  const data = {
    user: {
      name: (user as any)?.name,
      email: (user as any)?.email,
      avatar: "/alchemy_logo.png",
    },
  };

  return (
    <Sidebar collapsible="icon" className="border-none">
      <SidebarHeader className="bg-alchemyPrimaryNavyBlue p-0">
        <div className="grid grid-cols-[50px_1fr] p-2">
          <div>
            <Avatar
              className="h-8 w-8 rounded-lg cursor-pointer"
              onClick={() => navigate("/activity")}
            >
              <AvatarImage src="/alchemy_logo.png" />
              <AvatarFallback className="rounded-lg"></AvatarFallback>
            </Avatar>
          </div>
          <div
            className="pt-[2px] text-lg text-left cursor-pointer text-white"
            onClick={() => navigate("/activity")}
          >
            Alchemy Law Africa
          </div>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <div className="p-2 text-sm font-semibold">Your History</div>
        {agreements.map((agreement) => (
          <div
            key={agreement.id}
            className="flex items-center gap-2 cursor-pointer p-2 hover:bg-gray-100"
            onClick={() => onSelectAgreement(agreement.id)}
          >
            <SquareTerminal className="h-5 w-5" />
            <span>{agreement.agreement_name || "Untitled Agreement"}</span>
          </div>
        ))}
        <div
          className="flex items-center gap-2 cursor-pointer p-2 hover:bg-gray-100"
          onClick={() => onSelectView("new_agreement")}
        >
          <FilePlus2 className="h-5 w-5" />
          <span>New Agreement</span>
        </div>
        <div
          className="flex items-center gap-2 cursor-pointer p-2 hover:bg-gray-100"
          onClick={() => onSelectView("clause_library")}
        >
          <BookOpen className="h-5 w-5" />
          <span>Clause Library</span>
        </div>
      </SidebarContent>
      <SidebarFooter>
        <NavUser user={data.user} />
      </SidebarFooter>
    </Sidebar>
  );
}
